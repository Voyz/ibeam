import traceback


# from https://stackoverflow.com/a/37135014/3508719
def exception_to_string(excp):
    stack = traceback.extract_stack()[:-2] + traceback.extract_tb(excp.__traceback__)
    pretty = traceback.format_list(stack)
    return ''.join(pretty) + '\n  {} {}'.format(excp.__class__,excp)