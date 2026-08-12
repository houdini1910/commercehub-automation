import os
import sys

# Workaround for Python 3.14 + Tcl/Tk 9.0 with PyInstaller
# In Python 3.14, Tcl/Tk data is embedded in tcl90.dll via zipfs instead of directory on disk.
# Create dummy _tcl_data and _tk_data directories in sys._MEIPASS so pyi_rth__tkinter does not throw FileNotFoundError.
if hasattr(sys, '_MEIPASS'):
    tcldir = os.path.join(sys._MEIPASS, '_tcl_data')
    tkdir = os.path.join(sys._MEIPASS, '_tk_data')
    os.makedirs(tcldir, exist_ok=True)
    os.makedirs(tkdir, exist_ok=True)
