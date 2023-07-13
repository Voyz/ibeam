import os
import sys
from pathlib import Path

from ibeam.src import logs, var

initialized = False


def initialize():
    global initialized
    if initialized: return
    initialized = True

    logs.initialize()

    _this_filedir = os.path.abspath(os.path.dirname(__file__))
    sys.path.insert(0, str(Path(_this_filedir).parent))


class Config():
    def __init__(self):
        self._all_variables = var.all_variables
        self.manual_input_variables = self._all_variables.get('IBEAM_MANUAL_INPUT_VARIABLES', [])

    def __getattr__(self, key):
        try:
            return self._all_variables[key]
        except KeyError:
            # we allow the user to manually input some variables
            if key in self.manual_input_variables:
                return input(f'Enter value for {key}: ')

            raise AttributeError(f'{key} is not a valid config key. Existing keys: {list(self._all_variables.keys())}')

    @property
    def all_variables(self):
        return self._all_variables.copy()