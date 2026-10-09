import os
import sys
import shutil
import tempfile
import ctypes
from kivy.logger import Logger

_libmpv_loaded = False

_opengl32 = None
_sdl2 = None
_libgl = None

DLL_NAME = 'libmpv-2.dll'
ARCHIVE_NAME = 'libmpv-2.dll.xz'
# Same UUID as models/data.py so the extracted copy lives alongside the app's
# other machine-specific data.
SETTINGS_UUID = 'fmb-9220f09f-1c1b-4a65-b636-fe3996d18803'


def libmpv_directory():
    # <repository root>/libmpv
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, 'libmpv')


def fallback_directory():
    base = os.getenv('LOCALAPPDATA') or os.getenv('XDG_CACHE_HOME') or tempfile.gettempdir()
    return os.path.join(base, SETTINGS_UUID, 'libmpv')


def _extract_dll(directory):
    """Extract libmpv-2.dll from the bundled .xz archive when needed."""
    archive = os.path.join(directory, ARCHIVE_NAME)
    target = os.path.join(directory, DLL_NAME)

    if os.path.exists(target) and (not os.path.exists(archive)
                                   or os.path.getmtime(target) >= os.path.getmtime(archive)):
        return target

    if not os.path.exists(archive):
        return target if os.path.exists(target) else None

    import lzma  # pylint: disable=import-outside-toplevel

    Logger.info(f'libmpv: extracting {DLL_NAME} from {ARCHIVE_NAME} (first run)')
    temp_target = target + '.tmp'
    with lzma.open(archive, 'rb') as source, open(temp_target, 'wb') as destination:
        shutil.copyfileobj(source, destination, 1024 * 1024)
    os.replace(temp_target, target)
    Logger.info(f'libmpv: extracted {target} ({os.path.getsize(target)} bytes)')

    return target


def _ensure_dll(directory):
    """Return a directory that contains libmpv-2.dll, extracting if required."""
    try:
        if _extract_dll(directory) and os.path.exists(os.path.join(directory, DLL_NAME)):
            return directory
    except OSError as error:
        Logger.warning(f'libmpv: could not extract to {directory}: {error}')

    # The application directory may be read-only (e.g. installed under Program
    # Files), fall back to a writable per-user location.
    fallback = fallback_directory()
    try:
        os.makedirs(fallback, exist_ok=True)
        archive_src = os.path.join(directory, ARCHIVE_NAME)
        archive_dst = os.path.join(fallback, ARCHIVE_NAME)
        if os.path.exists(archive_src) and not os.path.exists(archive_dst):
            shutil.copyfile(archive_src, archive_dst)
        if _extract_dll(fallback) and os.path.exists(os.path.join(fallback, DLL_NAME)):
            return fallback
    except OSError as error:
        Logger.warning(f'libmpv: could not extract to {fallback}: {error}')

    return directory


def load_libmpv():
    """Make the bundled libmpv-2.dll discoverable before importing python-mpv."""
    global _libmpv_loaded
    if _libmpv_loaded:
        return

    directory = libmpv_directory()
    if os.path.isdir(directory):
        directory = _ensure_dll(directory)
        os.environ['PATH'] = directory + os.pathsep + os.environ.get('PATH', '')
        if hasattr(os, 'add_dll_directory'):
            try:
                os.add_dll_directory(directory)
            except OSError:
                Logger.warning(f'libmpv: could not add dll directory {directory}')
    else:
        Logger.warning(f'libmpv: directory not found {directory}')

    _libmpv_loaded = True


def _sdl2_get_proc_address(name):
    global _sdl2
    if _sdl2 is None:
        try:
            _sdl2 = ctypes.CDLL('SDL2.dll')
            _sdl2.SDL_GL_GetProcAddress.restype = ctypes.c_void_p
            _sdl2.SDL_GL_GetProcAddress.argtypes = [ctypes.c_char_p]
        except OSError:
            _sdl2 = False

    if _sdl2:
        return _sdl2.SDL_GL_GetProcAddress(name) or 0

    return 0


def _wgl_get_proc_address(name):
    global _opengl32
    if _opengl32 is None:
        try:
            _opengl32 = ctypes.WinDLL('opengl32')
            _opengl32.wglGetProcAddress.restype = ctypes.c_void_p
            _opengl32.wglGetProcAddress.argtypes = [ctypes.c_char_p]
        except OSError:
            _opengl32 = False

    if _opengl32:
        address = _opengl32.wglGetProcAddress(name)
        if not address or address in (1, 2, 3, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF):
            # wglGetProcAddress only returns functions newer than OpenGL 1.1.
            # Fall back to the exports of opengl32.dll for the rest.
            kernel32 = ctypes.WinDLL('kernel32')
            kernel32.GetProcAddress.restype = ctypes.c_void_p
            kernel32.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
            address = kernel32.GetProcAddress(_opengl32._handle, name)
        return address or 0

    return 0


def _glx_get_proc_address(name):
    global _libgl
    if _libgl is None:
        try:
            _libgl = ctypes.CDLL('libGL.so.1')
            _libgl.glXGetProcAddressARB.restype = ctypes.c_void_p
            _libgl.glXGetProcAddressARB.argtypes = [ctypes.c_char_p]
        except OSError:
            _libgl = False

    if _libgl:
        return _libgl.glXGetProcAddressARB(name) or 0

    return 0


def gl_get_proc_address(name):
    """Resolve an OpenGL function for the current context (libmpv render API)."""
    if isinstance(name, str):
        name = name.encode('utf-8')

    if sys.platform == 'win32':
        return _sdl2_get_proc_address(name) or _wgl_get_proc_address(name)

    return _glx_get_proc_address(name)
