import ctypes
import sys

from kivy.logger import Logger

# Windows 11 (build 22000+) DWM window attributes.
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36


def _colour_ref(hex_colour):
    # COLORREF is 0x00BBGGRR
    red = (hex_colour >> 16) & 0xFF
    green = (hex_colour >> 8) & 0xFF
    blue = hex_colour & 0xFF
    return red | (green << 8) | (blue << 16)


def set_title_bar_colour(caption_hex, text_hex=0xFFFFFF):
    """Colour the Windows title bar (Windows 11 only). Returns True on success."""
    if sys.platform != 'win32':
        return False

    if sys.getwindowsversion().build < 22000:
        Logger.info('window_chrome: custom title bar colour requires Windows 11')
        return False

    try:
        from kivy.core.window import Window  # pylint: disable=import-outside-toplevel
        hwnd = Window.get_window_info().window
    except Exception:  # pylint: disable=broad-exception-caught
        hwnd = None

    if not hwnd:
        Logger.warning('window_chrome: could not get the window handle')
        return False

    dwm = ctypes.windll.dwmapi
    dwm.DwmSetWindowAttribute.restype = ctypes.c_long
    dwm.DwmSetWindowAttribute.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                                          ctypes.c_void_p, ctypes.c_uint]

    dark_mode = ctypes.c_int(1)
    caption = ctypes.c_uint(_colour_ref(caption_hex))
    text = ctypes.c_uint(_colour_ref(text_hex))

    results = []
    for attribute, value in ((DWMWA_USE_IMMERSIVE_DARK_MODE, dark_mode),
                             (DWMWA_CAPTION_COLOR, caption),
                             (DWMWA_TEXT_COLOR, text)):
        result = dwm.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), ctypes.c_uint(attribute),
                                           ctypes.byref(value), ctypes.sizeof(value))
        results.append((attribute, result))

    Logger.info(f'window_chrome: DwmSetWindowAttribute results {results}')
    return all(result == 0 for _, result in results)
