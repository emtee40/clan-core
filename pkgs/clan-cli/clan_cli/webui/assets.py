import functools
from pathlib import Path

from ..nix import nix_build


@functools.cache
def asset_path() -> Path:
    return nix_build("ui-assets")
