"""Load optional Linux CUDA wheels without changing the process search path."""

import ctypes
from importlib import import_module
from pathlib import Path
import sys


def prepare_runtime():
    if sys.platform != 'linux':
        return
    try:
        package = import_module('nvidia.cublas')
    except ModuleNotFoundError as exc:
        if exc.name not in ('nvidia', 'nvidia.cublas'):
            raise
        return  # A system installation can supply CUDA instead.
    folder = Path(next(iter(package.__path__))) / 'lib'
    for name in ('libcublasLt.so.12', 'libcublas.so.12'):
        ctypes.CDLL(str(folder / name), mode=ctypes.RTLD_GLOBAL)
