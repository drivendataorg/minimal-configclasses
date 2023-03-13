from contextlib import contextmanager
import os
from pathlib import Path
import platform

import pytest

requires_macos = pytest.mark.skipif(platform.system() != "Darwin", reason="requires macOS")
requires_not_macos = pytest.mark.skipif(platform.system() == "Darwin", reason="requires macOS")

requires_windows = pytest.mark.skipif(platform.system() != "Windows", reason="requires Windows")
requires_not_windows = pytest.mark.skipif(
    platform.system() == "Windows", reason="requires Windows"
)


@contextmanager
def working_directory(directory: Path):
    """Changes working directory and returns to previous on exit."""
    prev_cwd = Path.cwd()
    os.chdir(directory)
    try:
        yield directory
    finally:
        os.chdir(prev_cwd)
