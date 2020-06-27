# SCD30 CO₂	sensor I²C driver in Python 3

**Status: initial release**

The [SCD30](https://www.sensirion.com/en/environmental-sensors/carbon-dioxide-sensors/carbon-dioxide-sensors-co2/)
is a high-precision CO2 sensor based on [NDIR](https://en.wikipedia.org/wiki/Nondispersive_infrared_sensor) spectroscopy.
The sensor module also includes an
[SHT31](https://www.sensirion.com/en/environmental-sensors/humidity-sensors/digital-humidity-sensors-for-various-applications/)
temperature and humidity sensor onboard (see
[description of the PCB layout](https://www.sensirion.com/fileadmin/user_upload/customers/sensirion/Dokumente/9.5_CO2/Sensirion_SCD30_Design-In_Guidelines_D1.pdf)).

## Overview
This library provides a Python interface to the main I²C-level commands supported by the SCD30 as listed in the
[interface description](https://www.sensirion.com/fileadmin/user_upload/customers/sensirion/Dokumente/9.5_CO2/Sensirion_CO2_Sensors_SCD30_Interface_Description.pdf).

The primary intended use case is driving the sensor directly from a Raspberry Pi using hardware I²C.
However, the code may be adapted for use with other devices supporting the protocol and/or software I²C.

## System setup
The library was developed using a Raspberry Pi 4B (8GB RAM) running Raspberry Pi OS Buster. For more details about the chip, see the
[BCM2711 datasheet](https://www.raspberrypi.org/documentation/hardware/raspberrypi/bcm2711/rpi_DATA_2711_1p0.pdf).

### Wiring
The Raspberry Pi can drive the SCD30 module via its hardware I²C interface directly without any additional components:

SCD30  | Raspberry Pi
------ | ------------
VDD    | 3V3 Power
GND    | Ground
TX/SCL | BCM 3 (SCL)
RX/SDA | BCM 2 (SDA)
SEL    | Ground¹

¹ To select I²C mode, the SEL pin should be left floating or connected to ground.
[This forum post](https://forum.arduino.cc/index.php?topic=561246.msg3828228#msg3828228) suggests grounding the pin may be the
more reliable option.

**Note the sequential order of the power, ground, and I²C pins on the SCD30 may be different from other popular sensor breakouts.**
For instance, the [Pimoroni breakouts](https://shop.pimoroni.com/collections/pimoroni-breakouts) use (3V3, SDA, SCL, INT, GND).

For more details, see the [Raspberry Pi I2C pinout](https://pinout.xyz/pinout/i2c).

### Software configuration and I²C clock stretching
The SCD30 supports a maximal I²C speed of 100kHz (the default of the Pi 4B).

It also requires the I²C bus to support clock stretching of up to 150ms. By default, the `bcm2835-i2c` driver which is still
used by the 4B (BCM2711) hard-codes the timeout to 35ms regardless of the speed. This does not seem to matter for one-off
readings, however may interfere with the long-term stability and particularly the automatic self-calibration feature.

As a workaround, the [rpi-i2c](https://github.com/RequestForCoffee/rpi-i2c-timings) binary utility provides means to
manipulate the relevant I2C controller registers directly.

### Usage
Contrary to other sensors that provide one-off readings, the SCD30 is designed to run continuously. Upon activation, periodic
measurements are stored in a buffer. A "data ready status" command is provided to check whether a reading is available.

The following example code will begin periodic measurements at a two-second interval and print the readings:

```py
from scd30_i2c import SCD30

scd30 = SCD30()

scd30.set_measurement_interval(2)
scd30.start_periodic_measurement()

time.sleep(2)

while True:
    if scd30.get_data_ready():
        m = scd30.read_measurement()
        if m is not None:
            print(f"CO2: {m[0]:.2f}ppm, temp: {m[1]:.2f}'C, rh: {m[2]:.2f}%")
        time.sleep(2)
    else:
        time.sleep(0.2)
```

Note that this minimal example script will NOT issue a stop command upon termination and the sensor will continue taking
periodic measurements unless powered off. This may or may not be appropriate depending on the use case.

For a more complete example, see [here](examples/continuous_measurement.py).
