from pkg_resources import DistributionNotFound, get_distribution

try:
    __version__ = get_distribution("python-sensors").version
except DistributionNotFound:
    pass

from .classification import SSPOC
from .reconstruction import SSPOR

__all__ = [
    # Modules:
    "basis",
    "classification",
    "reconstruction",
    "optimizers",
    "utils",
    # Non-modules:
    "SSPOR",
    "SSPOC",
]
