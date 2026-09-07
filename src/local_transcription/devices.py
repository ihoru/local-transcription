"""Device selection shared by setup, diagnostics, and inference."""

import platform


DEVICES = ('cpu', 'cuda', 'metal')


def apple_silicon():
    return platform.system() == 'Darwin' and platform.machine() == 'arm64'


def default_device():
    return 'metal' if apple_silicon() else 'cpu'


def validate_device(device):
    if device not in DEVICES:
        raise ValueError(f'Unknown device: {device}')
    if device == 'metal' and not apple_silicon():
        raise ValueError('Metal recognition requires native Apple Silicon Python on macOS.')
    if device == 'cuda' and platform.system() == 'Darwin':
        raise ValueError('CUDA requires NVIDIA hardware. Use --device metal on Apple Silicon '
                         'or --device cpu on Intel Macs.')
    return device
