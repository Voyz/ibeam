import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, List

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
        _LOGGER.info(f'Starting Gateway as Windows process with params: {args}')
        creationflags = subprocess.CREATE_NEW_CONSOLE

    elif sys.platform == 'darwin':
        args = ["open", "-F", "-a", "Terminal", r"bin/run.sh", r"root/conf.yaml"]
        _LOGGER.info(f'Starting Gateway as Mac process with params: {args}')

    elif sys.platform == 'linux':
        args = ["bash", r"bin/run.sh", r"root/conf.yaml"]
        _LOGGER.info(f'Starting Gateway as Linux process with params: {args}')

    else:
        raise EnvironmentError(f'Unknown platform: {sys.platform}')

    subprocess.Popen(
        args=args,
        cwd=gateway_dir,
        creationflags=creationflags
    )

def try_starting_gateway(
        gateway_process_match:str,
        gateway_dir:os.PathLike,
        gateway_startup:int,
        verify_connection:callable,
)  -> Optional[List[int]]:
    processes = find_procs_by_name(gateway_process_match)
    if processes:
        server_process_pids = [process.pid for process in processes]
    else:
        _LOGGER.info('Gateway not found, starting new one...')
        _LOGGER.info(
            'Note that the Gateway log below may display "Open https://localhost:[PORT] to login" - ignore this command.')

        start_gateway(gateway_dir)

        server_process_pids = None

        # let's try to communicate with the Gateway
        t_end = time.time() + gateway_startup

        while time.time() < t_end:
            processes = find_procs_by_name(gateway_process_match)
            if len(processes) == 0:
                continue

            server_process_pids = [process.pid for process in processes]
            _LOGGER.info(f'Gateway started with pids: {server_process_pids}')
            break

        if server_process_pids is None:
            _LOGGER.error(f'Cannot find gateway process by name: "{gateway_process_match}"')
            return None

        ping_success = False
        while time.time() < t_end:
            status = verify_connection()
            if not status.running:
                seconds_remaining = round(t_end - time.time())
                if seconds_remaining > 0:
                    _LOGGER.info(
                        f'Cannot ping Gateway. Retrying for another {seconds_remaining} seconds')
                    time.sleep(1)
            else:
                _LOGGER.info('Gateway connection established')
                ping_success = True
                break

        if not ping_success:
            _LOGGER.error('Gateway process found but cannot establish a connection with the Gateway')

    return server_process_pids

def kill_gateway(gateway_process_match:str):
    processes = find_procs_by_name(gateway_process_match)
    if not processes:
        _LOGGER.warning(f'Attempting to kill but could not find process named "{gateway_process_match}"')
        return False

    for process in processes:
        process.terminate()

    time.sleep(1)

    # double check we succeeded
    processes = find_procs_by_name(gateway_process_match)
    if processes:
        return False
    return True