import os
import sys
from pathlib import Path

from ibeam.src import logs

initialized = False


def initialize():
    global initialized
    if initialized: return
    initialized = True

    logs.initialize()

    _this_filedir = os.path.abspath(os.path.dirname(__file__))
    sys.path.insert(0, str(Path(_this_filedir).parent))
