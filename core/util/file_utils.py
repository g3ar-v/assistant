import os
import tempfile

def get_temp_path(*args):
    """Generate a valid path in the system temp directory.

    This method accepts one or more strings as arguments. The arguments are
    joined and returned as a complete path inside the systems temp directory.
    Importantly, this will not create any directories or files.

    Example usage: get_temp_path('core', 'audio', 'example.wav')
    Will return the equivalent of: '/tmp/core/audio/example.wav'

    Args:
        path_element (str): directories and/or filename

    Returns:
        (str) a valid path in the systems temp directory
    """
    try:
        path = os.path.join(tempfile.gettempdir(), *args)
    except TypeError:
        raise TypeError(
            "Could not create a temp path, get_temp_path() only " "accepts Strings"
        )
    return path