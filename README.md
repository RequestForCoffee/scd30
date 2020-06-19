# Sensirion SCD30 I²C driver in Python 3

**Status: Work In Progress**

The [SCD30](https://www.sensirion.com/en/environmental-sensors/carbon-dioxide-sensors/carbon-dioxide-sensors-co2/)
is a high-precision CO2 sensor based on [NDIR](https://en.wikipedia.org/wiki/Nondispersive_infrared_sensor) spectroscopy.
The sensor module also includes an
[SHT31](https://www.sensirion.com/en/environmental-sensors/humidity-sensors/digital-humidity-sensors-for-various-applications/)
temperature and humidity sensor onboard (see
[description of the PCB layout](https://www.sensirion.com/fileadmin/user_upload/customers/sensirion/Dokumente/9.5_CO2/Sensirion_SCD30_Design-In_Guidelines_D1.pdf)).

## Overview
This library provides a Python interface to the I²C-level commands supported by the SCD30 as listed in the
[interface description](https://www.sensirion.com/fileadmin/user_upload/customers/sensirion/Dokumente/9.5_CO2/Sensirion_CO2_Sensors_SCD30_Interface_Description.pdf).

The primary intended use case is driving the sensor directly from a Raspberry Pi using either hardware or software I²C.
However, the code may be adapted for use with other devices supporting the protocol.

## System setup
The library was developed using a Raspberry Pi 4B (8GB RAM) running Raspbian Buster. For more details about the chip, see the
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

### Software configuration
The SCD30 supports a maximal I²C speed of 100kHz. To configure the hardware I²C interface speed on the Raspberry Pi, add or modify
the following parameter to `/boot/config.txt`:
```
dtparam=i2c_baudrate=100000
```

### I²C clock stretching
Older versions of the Raspberry Pi based on the BCM2835 chip (and possibly the BCM2837) suffered from a hardware bug in its I²C
clock stretching implementation. The SCD30 is fairly sensitive in this regard, requiring the I²C master support for up to 150ms
clock stretching. Therefore, using it with hardware I²C may not work reliably (or at all) on Raspberry Pi boards prior to the
model 4B (software-based I²C [bit banging](https://en.wikipedia.org/wiki/Bit_banging) bus implementations may still work).
