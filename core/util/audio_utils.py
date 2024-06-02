import re
import pyaudio
from .log import LOG


def find_input_device(device_name):
    """Find audio input device by name.

    Args:
        device_name: device name or regex pattern to match

    Returns: device_index (int) or None if device wasn't found
    """
    LOG.info("Searching for input device: {}".format(device_name))
    LOG.info("Devices: ")
    pa = pyaudio.PyAudio()
    pattern = re.compile(device_name)
    for device_index in range(pa.get_device_count()):
        dev = pa.get_device_info_by_index(device_index)
        LOG.info("   {}".format(dev["name"]))
        if dev["maxInputChannels"] > 0 and pattern.match(dev["name"]):
            LOG.info("    ^-- matched")
            return device_index
    return None
