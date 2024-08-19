import traceback


# from https://stackoverflow.com/a/37135014/3508719
def exception_to_string(excp):
    stack = traceback.extract_stack()[:-2] + traceback.extract_tb(excp.__traceback__)
    pretty = traceback.format_list(stack)
    return ''.join(pretty) + '\n  {} {}'.format(excp.__class__,excp)


# from: https://github.com/drgarcia1986/simple-settings/pull/281/files
_MAP = {
    'y': True,
    'yes': True,
    't': True,
    'true': True,
    'on': True,
    '1': True,
    'n': False,
    'no': False,
    'f': False,
    'false': False,
    'off': False,
    '0': False
}

def strtobool(value):
    try:
        return _MAP[str(value).lower()]
    except KeyError:
        raise ValueError('"{}" is not a valid bool value'.format(value))