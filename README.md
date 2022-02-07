# HDC1080 CircuitPython module

## Quickstart
From the [CircuitPyton libraries](https://learn.adafruit.com/welcome-to-circuitpython/circuitpython-libraries) get the 
`adafruit_bus_device` and `adafruit_register` and add it to your `/lib` folder on your board. Copy the 
[amu_hdc1080.py](amu_hdc1080.py) from this repository to the `/lib` folder as well.

It will return the temperature in **degrees Celsius** and the **Relative humidity**

```python
import board
import amu_hdc1080
import busio
import time

i2c = busio.I2C(board.SCL, board.SDA)
hdc1080 = amu_hdc1080.HDC1080(i2c)

while True:
    print("temp: {temp:.2f} degrees C".format(temp=hdc1080.temperature))
    print("humidity: {hum:.2f}%".format(hum=hdc1080.humidity))
    
    time.sleep(1)
```


## Modes

The default (example above) configures the sensor to read either temperature **or** humidity. It does however have a
more optimized mode where it performs a measurement for both in one go. This might be useful if you always
read them together:

```python
import board
import amu_hdc1080
import busio
import time

i2c = busio.I2C(board.SCL, board.SDA)
hdc1080 = amu_hdc1080.HDC1080(i2c, mode=amu_hdc1080.READ_BOTH_VALUES)

while True:
    temp, hum = hdc1080.temperature_and_humidity()
    print("temp: {temp:.2f} degrees C".format(temp=temp))
    print("humidity: {hum:.2f}%".format(hum=hum))
    
    time.sleep(1)
```

## I2C address

In case your device does not use the standard `0x40` address you can specify this in the constructor:

```python
hdc1080 = amu_hdc1080.HDC1080(i2c, address=0x11)
```


