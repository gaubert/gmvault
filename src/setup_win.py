from distutils.core import setup
import py2exe

from glob import glob
#data_files = [("Microsoft.VC90.CRT", glob(r'C:\Program Files\Microsoft Visual Studio 9.0\VC\redist\x86\Microsoft.VC90.CRT\*.*'))]
data_files = [("Microsoft.VC90.CRT", glob(r'C:\WINDOWS\WinSxS\x86_Microsoft.VC90.CRT_1fc8b3b9a1e18e3b_9.0.21022.8_x-ww_d08d0375\*.*'))]
setup(data_files=data_files, console=['gmv_cmd.py'])
