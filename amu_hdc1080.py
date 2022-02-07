"""
`HDC1080 driver`
====================================================
CircuitPython module for the HDC1080 temperature/humidity sensor.
* Author: a-mueller
* Datasheet: https://www.ti.com/lit/ds/symlink/hdc1080.pdf

Implementation Notes
--------------------
**Software and Dependencies:**
*  Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
* Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

# Imports, make sure adafruit_bus_device and adafruit_register are in your lib folder!
from micropython import const
import struct
import adafruit_bus_device.i2c_device as i2cdevice
from adafruit_register.i2c_struct import ROUnaryStruct
from adafruit_register.i2c_bit import RWBit
from adafruit_register.i2c_bits import RWBits
import time

# Constants
_HDC1080_I2CADDR_DEFAULT = const(0x40)  # Default i2c address
_HDC1080_DEVICE_ID = const(0x1050)  # Device ID, (static) see 8.6.6 Device Register ID in Datasheet

# Register addresses, see Datasheet
_REG_TEMP = const(0x00)  # temperature register
_REG_HUMI = const(0x01)  # humidity register
_REG_CONF = const(0x02)  # configuration register
_REG_DEID = const(0xFF)  # device ID register

# External Constants
READ_BOTH_VALUES = const(0x01)
READ_SINGLE_VALUE = const(0x00)


def _convert_to_celsius(raw_value):
    # Convert to Celsius per datasheet
    return (raw_value / (2 ** 16)) * 165 - 40


def _convert_to_relative_humidity(raw_value):
    # Conversion per datasheet
    return (raw_value / (2 ** 16)) * 100


class HDC1080:
    """HDC1080 Temperature sensor.
    :param ~busio.I2C i2c: The I2C bus the HDC1080 is connected to
    :param int address: (optional) The I2C address of the device. Defaults to :const:`0x40`
    :param int mode: (optional) The mode we configure the sensor with. Defaults to `READ_SINGLE_VALUE`
    **Quickstart: Importing and using the HDC1080**
        Here is an example of using the :class:`HDC1080` class.
        First you will need to import the libraries to use the sensor
        .. code-block:: python
            import board
            from amu_hdc1080 import HDC1080
        Once this is done you can define your `board.I2C` object and define your sensor object
        .. code-block:: python
            i2c = board.I2C()   # uses board.SCL and board.SDA
            sensor = HDC1080(i2c)
        Now you have access to the :attr:`sensor.temperature and sensor.humidity`
        .. code-block:: python
            temperature_in_celcius = sensor.temperature
            relative_humidity = sensor.humidity
    """

    # Big endian unsigned short (>H)
    _device_id = ROUnaryStruct(_REG_DEID, ">H")

    # Software reset bit (see 8.6.3 Configuration Register), will clear itself
    # 0: Normal operation
    # 1: Software reset
    _software_reset = RWBit(_REG_CONF, bit=15, register_width=2, lsb_first=False)

    # Temperature resolution bit (see 8.6.3 Configuration Register)
    # 0: 14 bit resolution
    # 1: 11 bit resolution
    _temp_resolution = RWBit(_REG_CONF, bit=10, register_width=2, lsb_first=False)

    # Humidity resolution bits (see 8.6.3 Configuration Register)
    # 00: 14 bit resolution
    # 01: 11 bit resolution
    # 10: 8 bit resolution
    _humidity_resolution = RWBits(2, _REG_CONF, lowest_bit=8, register_width=2, lsb_first=False)

    # Operation Mode (see 8.6.3 Configuration Register)
    # 0: Read either temperature OR humidity
    # 1: Read both at the same time (default)
    _operation_mode = RWBit(_REG_CONF, bit=12, register_width=2, lsb_first=False)

    # Class-level buffer for reading and writing data with the sensor.
    # Unfortunately we can't use the adafruit i2c_struct library for this as the sensor wants us to wait
    # after having written to the register before reading which the library doesn't support.
    # This reduces memory allocations but means the code is not thread safe!
    _BUFFER = bytearray(5)

    def __init__(self, i2c, address=_HDC1080_I2CADDR_DEFAULT, mode=READ_SINGLE_VALUE):
        self.i2c_device = i2cdevice.I2CDevice(i2c, address)
        self.mode = mode

        # Make sure the sensor is connected to the I2C bus
        if self._device_id != _HDC1080_DEVICE_ID:
            raise RuntimeError("Failed to find a HDC1080 on I2C bus!")

        # Reset the chip
        self._software_reset = 0x1

        # Sleep for 15 ms to allow the temperature and humidity temperatures to start recording
        time.sleep(0.015)
        # set up for 14 bit resolution (in config register) for both temperature and humidity readings
        self._temp_resolution = 0x00
        self._humidity_resolution = 0x00
        self._operation_mode = mode
        # self._debug_config_register()

    # Prints the bits of the two bytes from the config register, for debugging
    def _debug_config_register(self):
        with self.i2c_device as i2c:
            self._BUFFER[0] = _REG_CONF & 0xFF
            i2c.write(self._BUFFER, end=1)
            time.sleep(0.0635)
            i2c.readinto(self._BUFFER, start=1, end=3)

        print("{0:08b}".format(self._BUFFER[1]))
        print("{0:08b}".format(self._BUFFER[2]))

    # Unfortunately we have to do this manually instead of using the i2c_struct as we have to wait for 6.35 ms between
    # writing and reading from the register,
    # struct format as in https://docs.python.org/3.4/library/struct.html#module-struct
    def _read_from_register(self, register, struct_format):
        with self.i2c_device as i2c:
            self._BUFFER[0] = register & 0xFF
            i2c.write(self._BUFFER, end=1)
            time.sleep(0.0635)
            i2c.readinto(self._BUFFER, start=1, end=3)

        return struct.unpack_from(struct_format, self._BUFFER, 1)[0]

    # Reads from multiple registers in a single transaction. This is useful if mode == READ_BOTH_VALUES as both
    # measurements are done at the same time, returns a tuple with the values
    def _read_from_registers(self, register, struct_format):
        with self.i2c_device as i2c:
            self._BUFFER[0] = register & 0xFF
            i2c.write(self._BUFFER, end=1)
            time.sleep(0.0635)
            i2c.readinto(self._BUFFER, start=1)

        return struct.unpack_from(struct_format, self._BUFFER, 1)[0], struct.unpack_from(struct_format, self._BUFFER, 3)[0]

    @property
    def temperature(self):
        if self.mode == READ_BOTH_VALUES:
            raise RuntimeError("Wrong mode, use temperature_and_humidity if mode == READ_BOTH_VALUES")
        # Read the temperature register (big endian signed short)
        value = self._read_from_register(_REG_TEMP, '>h')
        return _convert_to_celsius(value)

    @property
    def humidity(self):
        if self.mode == READ_BOTH_VALUES:
            raise RuntimeError("Wrong mode, use temperature_and_humidity if mode == READ_BOTH_VALUES")
        # Read the humidity register (big endian signed short)
        value = self._read_from_register(_REG_HUMI, '>h')
        return _convert_to_relative_humidity(value)

    def temperature_and_humidity(self):
        if self.mode == READ_SINGLE_VALUE:
            raise RuntimeError("Wrong mode, use temperature or humidity if mode == READ_SINGLE_VALUE")
        # Read the humidity register (big endian signed short)
        values = self._read_from_registers(_REG_TEMP, struct_format='>h')
        return _convert_to_celsius(values[0]), _convert_to_relative_humidity(values[1])
