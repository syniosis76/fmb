import threading
import time

from kivy.logger import Logger

from utilities import libmpv_loader

libmpv_loader.load_libmpv()

import mpv  # pylint: disable=wrong-import-position,import-error

# Position (seconds) to sample the thumbnail from. Matches the previous
# ffmpeg based generator which used 3 seconds in.
THUMBNAIL_POSITION = 3.0

_lock = threading.Lock()
_player = None


def _get_player():
    global _player
    if _player is None:
        _player = mpv.MPV(
            vo='null',
            ao='null',
            audio='no',
            terminal=False,
            osc=False,
            keep_open='yes',
            hwdec='no',
        )
    return _player


def _wait_for_position(player, position_seconds):
    deadline = time.time() + 5.0
    while time.time() < deadline:
        time_pos = player.time_pos
        if time_pos is not None and abs(time_pos - position_seconds) < 0.5:
            return
        time.sleep(0.02)


def grab_frame(source_file, position_seconds=None):
    """Decode a single frame from source_file and return it as a PIL image.

    Returns None if the file cannot be decoded. The frame is sampled at
    ``position_seconds`` (defaults to 3s in, or half the duration for short
    clips). Uses a single shared libmpv instance for all thumbnails.
    """
    with _lock:
        try:
            player = _get_player()
            player.play(source_file)
            player.wait_until_playing(timeout=15)

            if position_seconds is None:
                duration = player.duration or 0
                if duration >= THUMBNAIL_POSITION:
                    position_seconds = THUMBNAIL_POSITION
                else:
                    position_seconds = duration / 2

            player.command('seek', position_seconds, 'absolute', 'exact')
            _wait_for_position(player, position_seconds)

            player.pause = True
            try:
                return player.screenshot_raw()
            finally:
                player.pause = False
        except Exception:  # pylint: disable=broad-exception-caught
            Logger.exception(f'mpv_thumbnail: failed to grab frame from {source_file}')
            return None


def shutdown():
    global _player
    with _lock:
        if _player is not None:
            try:
                _player.terminate()
            except Exception:  # pylint: disable=broad-exception-caught
                Logger.exception('mpv_thumbnail: error terminating player')
            _player = None
