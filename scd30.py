from datetime import timedelta
import logging
import smbus2
import struct
import time


def interpret_as_float(integer: int):
    return struct.unpack('!f', struct.pack('!I', integer))[0]


def pretty_hex(data):
    if type(data) is int:
        data = [data]
    if len(data) == 0:
        return "<none>"

    if len(data) == 1:
        value = "{:02x}".format(data[0])
        if len(value) % 2:
            value = "0" + value
        return "0x" + value
    return "[" + ", ".join("0x{:02x}".format(byte) for byte in data) + "]"


def crc8(word: int):
    """Computes the CRC-8 checksum defined in the SCD30 interface description.
    Polynomial: x^8 + x^5 + x^4 + 1 (0x31, MSB)
    Initialization: 0xFF

    Algorithm adapted from:
    https://en.wikipedia.org/wiki/Computation_of_cyclic_redundancy_checks
    """
    polynomial = 0x31
    rem = 0xFF
    word_bytes = word.to_bytes(2, "big")
    for byte in word_bytes:
        rem ^= byte
        for bit in range(8):
            if rem & 0x80:
                rem = (rem << 1) ^ polynomial
            else:
                rem = rem << 1
            rem &= 0xFF

    return rem


def check_word(word: int, name: str = "value"):
    """Checks that a word is a valid two-byte value and throws otherwise"""

    if not 0 <= word <= 0xFFFF:
        raise ValueError(
            f"{name} outside valid two-byte word range: {word}")


class SCD30:
    """Python I2C driver for the Sensirion SCD30 CO2 sensor."""

    def __init__(self):
        self._i2c_addr = 0x61
        self._i2c = smbus2.SMBus(1)

    def _send_command(self, command: int, num_response_words: int = 1,
                      arguments: list = []):
        """Sends the provided I2C command and reads out the results.

        Parameters:
            command: the two-byte command code, e.g. 0x0010
            num_response_words: number of two-byte words in the result
            arguments (optional): list of two-byte arguments to the command

        Returns:
            list of num_response_words two-byte int values from the sensor
        """
        check_word(command, "command")
        logging.debug(f"Executing command {pretty_hex(command)} with args: "
                      f"{pretty_hex(arguments)}")

        raw_message = list(command.to_bytes(2, "big"))
        for argument in arguments:
            check_word(argument, "argument")
            raw_message.extend(argument.to_bytes(2, "big"))
            raw_message.append(crc8(argument))

        logging.debug(
            f"Sending raw I2C data block: {pretty_hex(raw_message)}")

        #self._i2c.write_i2c_block_data(self._i2c_addr, command, arguments)
        write_txn = smbus2.i2c_msg.write(self._i2c_addr, raw_message)
        self._i2c.i2c_rdwr(write_txn)

        # The interface description provided by Sensirion suggests a >3ms
        # delay between writes and reads for most commands.
        time.sleep(timedelta(milliseconds=5).total_seconds())

        if num_response_words == 0:
            return []

        read_txn = smbus2.i2c_msg.read(self._i2c_addr, num_response_words * 3)
        self._i2c.i2c_rdwr(read_txn)

        # raw_response = self._i2c.read_i2c_block_data(
        #    self._i2c_addr, command, 3 * num_response_words)
        raw_response = list(read_txn)
        logging.debug(f"Received raw I2C response: {pretty_hex(raw_response)}")

        # Data is returned as a sequence of num_response_words 2-byte words
        # (big-endian), each with a CRC-8 checksum:
        # [MSB0, LSB0, CRC0, MSB1, LSB1, CRC1, ...]
        response = []
        for i in range(num_response_words):
            # word_with_crc contains [MSB, LSB, CRC] for the i-th response word
            word_with_crc = raw_response[3 * i: 3 * i + 3]
            word = int.from_bytes(word_with_crc[:2], "big")
            response_crc = word_with_crc[2]
            computed_crc = crc8(word)
            if (response_crc != computed_crc):
                logging.error(
                    f"CRC verification for word {pretty_hex(word)} failed: "
                    f"received {pretty_hex(response_crc)}, computed "
                    f"{pretty_hex(computed_crc)}")
                return None
            response.append(word)

        logging.debug(f"CRC-verified response: {pretty_hex(response)}")
        return response

    def get_firmware_version(self):
        """Reads the firmware version from the sensor.

        Returns:
            two-byte integer version number
        """
        return next(iter(self._send_command(0xD100) or []), None)

    def get_data_ready(self):
        return next(iter(self._send_command(0x0202) or []), None)

    def start_periodic_measurement(self, ambient_pressure: int = 0):
        """Starts periodic measurement of CO2 concentration, humidity and temp.

        Parameters:
            ambient_pressure (optional): external pressure reading in millibars

        The enable status of periodic measurement is stored in non-volatile
        memory onboard the sensor module and will persist after shutdown.

        ambient_pressure may be set to either 0 to disable ambient pressure
        compensation, or between [700; 1400] mBar.
        """
        if ambient_pressure and not 700 <= ambient_pressure <= 1400:
            raise ValueError("Ambient pressure must be set to either 0 or in the "
                             "range [700; 1400] mBar")

        self._send_command(0x0010, num_response_words=0,
                           arguments=[ambient_pressure])

    def stop_periodic_measurement(self):
        """Stops periodic measurement of CO2 concentration, humidity and temp.

        The enable status of periodic measurement is stored in non-volatile
        memory onboard the sensor module and will persist after shutdown.
        """
        self._send_command(0x0104, num_response_words=0)

    def set_measurement_interval(self, interval=2):
        """Sets the interval used for periodic measurements.

        Parameters:
            interval: the interval in seconds within the range [2; 1800]

        The interval setting is stored in non-volatile memory and persists
        after power-off.
        """
        if not 2 <= interval <= 1800:
            raise ValueError("Interval must be in the range [2; 1800] (sec)")

        res = next(iter(self._send_command(0x4600, 1, [interval]) or []), None)
        if res is None or res != interval:
            logging.error("Failed to set measurement interval.")

    def read_measurement(self):
        """Reads out a CO2, temperature and humidity measurement

        Must only be called if a measurement is available for reading, i.e.
        get_data_ready() returned 1.

        Returns:
            tuple of measurement values (CO2 ppm, Temp Celsius, RH %) or None
        """
        data = self._send_command(0x0300, num_response_words=6)

        if data is None or len(data) != 6:
            logging.error("Failed to read measurement.")
            return None

        co2_ppm = interpret_as_float((data[0] << 16) | data[1])
        temp_celsius = interpret_as_float((data[2] << 16) | data[3])
        rh_percent = interpret_as_float((data[4] << 16) | data[5])

        return (co2_ppm, temp_celsius, rh_percent)


if __name__ == "__main__":
    scd30 = SCD30()

    logging.basicConfig(level=logging.INFO)

    logging.info("Probing sensor...")
    while scd30.get_data_ready() not in [0, 1]:
        time.sleep(1)

    logging.info("Link to sensor established.")
    logging.info("Getting firmware version...")

    logging.info(
        f"Sensor firmware version: {pretty_hex(scd30.get_firmware_version())}")

    logging.info("Starting periodic measurement...")
    scd30.start_periodic_measurement()
    logging.info("Setting measurement interval to 2s...")
    scd30.set_measurement_interval(2)

    try:
        while True:
            if scd30.get_data_ready():
                measurement = scd30.read_measurement()
                if measurement is not None:
                    co2, temp, rh = measurement
                    print(f"CO2: {co2}ppm, temp: {temp}'C, rh: {rh}%'")
            time.sleep(0.5)

    except KeyboardInterrupt:
        logging.info("Stopping periodic measurement...")
        scd30.stop_periodic_measurement()
