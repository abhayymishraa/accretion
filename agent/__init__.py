"""The build agent: one editing conversation and everything it owns."""
from pathlib import Path

# Assets are read by modules in several subpackages, so anchor on the package
# root rather than on any one module's location.
PACKAGE_ROOT = Path(__file__).resolve().parent
