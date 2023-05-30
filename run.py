import sys

if sys.platform=="win32":
    import ctypes
    ctypes.windll.user32.ShowWindow( ctypes.windll.kernel32.GetConsoleWindow(), 0 )

import main

if __name__ == '__main__':
    main.fmb_app().run()