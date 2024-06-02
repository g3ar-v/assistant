import subprocess
from .log import LOG


def reduce_playback_volume():
    LOG.info("REDUCING SPOTIFY VOLUME")
    subprocess.run(
        [
            "osascript",
            "-e",
            (
                'tell application "Spotify" to set sound volume to'
                '(sound volume of application "Spotify") - 20'
            ),
        ]
    )


def restore_playback_volume():
    LOG.info("INCREASING SPOTIFY VOLUME")
    subprocess.run(
        [
            "osascript",
            "-e",
            (
                'tell application "Spotify" to set sound volume to'
                '(sound volume of application "Spotify") + 10'
            ),
        ]
    )
