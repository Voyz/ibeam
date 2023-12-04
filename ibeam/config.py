from ibeam.src.var import UNDEFINED


class Config():
    def __init__(self, env_variables):
        self._all_variables = env_variables.copy()
        self.manual_input_variables = self._all_variables.get('IBEAM_MANUAL_INPUT_VARIABLES', [])

    def __getattr__(self, key):
        try:
            value = self._all_variables[key]
            if value is UNDEFINED:
                raise ValueError(f'Variable "IBEAM_{key}" is undefined. Fix by setting "IBEAM_{key}" environment variable.')
            return value
        except KeyError:
            # we allow the user to manually input some variables
            if key in self.manual_input_variables:
                return input(f'Enter value for {key}: ')

            raise AttributeError(f'{key} is not a valid config key. Existing keys: {list(self._all_variables.keys())}')

    @property
    def all_variables(self):
        return self._all_variables.copy()