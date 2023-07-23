
import ctypes
import os
import platform
from typing import Union
from pathlib import Path


def get_free_space(path: Union[Path,str]) -> int:
    """Return folder/drive free space (in bytes)."""
    if not isinstance(path, Path):
        path = Path(path)
    if not os.path.exists(path):
        raise FileNotFoundError(f'{path} File Not Found')
    if platform.system() == 'Windows':
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(path), None, None, ctypes.pointer(free_bytes)) # type: ignore
        return free_bytes.value
    else:
        st = os.statvfs(path)
        return st.f_bavail * st.f_frsize
