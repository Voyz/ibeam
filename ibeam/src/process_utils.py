import logging
import os
import subprocess
import sys
from pathlib import Path

import psutil

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)


# from https://stackoverflow.com/questions/550653/cross-platform-way-to-get-pids-by-process-name-in-python/2241047
def find_procs_by_name(name):
    "Return a list of processes matching 'name'."
    assert name, name
    ls = []
    for p in psutil.process_iter():
        name_, exe, cmdline = "", "", []
        try:
            # name_ = p.name()
            cmdline = p.cmdline()
            exe = p.exe()
        except (psutil.AccessDenied, psutil.ZombieProcess):
            pass
        except psutil.NoSuchProcess:
            continue
        if name in ' '.join(cmdline) or name in os.path.basename(exe):
            ls.append(p)
    return ls


def start_gateway(gateway_dir):
    creationflags = 0  # when not on Windows, we send 0 to avoid errors.

    if sys.platform == 'win32':
        args = ["cmd", "/k", r"bin\run.bat", r"root\conf.yaml"]
        _LOGGER.debug(f'Starting Windows process with params: {args}')
        creationflags = subprocess.CREATE_NEW_CONSOLE

    elif sys.platform == 'darwin':
        args = ["open", "-F", "-a", "Terminal", r"bin/run.sh", r"root/conf.yaml"]
        _LOGGER.debug(f'Starting Mac process with params: {args}')

    elif sys.platform == 'linux':
        args = ["bash", r"bin/run.sh", r"root/conf.yaml"]
        _LOGGER.debug(f'Starting Linux process with params: {args}')

    else:
        raise EnvironmentError(f'Unknown platform: {sys.platform}')

    subprocess.Popen(
        args=args,
        cwd=gateway_dir,
        creationflags=creationflags
    )

# if __name__ == '__main__':
#     start_gateway(os.environ.get('IBEAM_GATEWAY_DIR'))
