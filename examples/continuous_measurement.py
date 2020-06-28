from scd30_i2c import SCD30
import logging
import time


def continuous_reading(scd30: SCD30):
    while True:
        if scd30.get_data_ready():
            measurement = scd30.read_measurement()
            if measurement is not None:
                co2, temp, rh = measurement
                print(f"CO2: {co2:.2f}ppm, temp: {temp:.2f}'C, rh: {rh:.2f}%")
            time.sleep(measurement_interval)
        else:
            time.sleep(0.2)


scd30 = SCD30()

logging.basicConfig(level=logging.INFO)

retries = 30
logging.info("Probing sensor...")
ready = None
while ready is None and retries:
    try:
        ready = scd30.get_data_ready()
    except OSError:
        # The sensor may need a couple of seconds to boot up after power-on
        # and may not be ready to respond, raising I2C errors during this time.
        pass
    time.sleep(1)
    retries -= 1
if not retries:
    logging.error("Timed out waiting for SCD30.")
    exit(1)

logging.info("Link to sensor established.")
logging.info("Getting firmware version...")

logging.info(f"Sensor firmware version: {scd30.get_firmware_version()}")

# 2 seconds is the minimum supported interval.
measurement_interval = 2

logging.info("Setting measurement interval to 2s...")
scd30.set_measurement_interval(measurement_interval)
logging.info("Enabling automatic self-calibration...")
scd30.set_auto_self_calibration(active=True)
logging.info("Starting periodic measurement...")
scd30.start_periodic_measurement()

time.sleep(measurement_interval)

logging.info(f"ASC status: {scd30.get_auto_self_calibration_active()}")
logging.info(f"Measurement interval: {scd30.get_measurement_interval()}s")
logging.info(f"Temperature offset: {scd30.get_temperature_offset()}'C")

try:
    continuous_reading(scd30)
except KeyboardInterrupt:
    logging.info("Stopping periodic measurement...")
    scd30.stop_periodic_measurement()
