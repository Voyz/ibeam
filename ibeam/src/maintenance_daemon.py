import os
import logging
import daemon
from pidlockfile import PIDLockFile
from getpass import getpass
from pathlib import Path
from ibeam.src import var
from ibeam.src.gateway_client import create_gateway_client

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)

def start_maintenance_daemon(account, password):
    rootpath = os.path.abspath(
               os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))
    # https://stackoverflow.com/questions/13180720/maintaining-logging-and-or-stdout-stderr-in-python-daemon
    def get_logging_handles(logger):
        handles = []
        for handler in logger.handlers:
            handles.append(handler.stream.fileno())
        if logger.parent:
            handles += get_logging_handles(logger.parent)
        return handles
    files_preserve = get_logging_handles(_LOGGER)
    with daemon.DaemonContext(
        working_directory=rootpath,
        umask=0o002,
        pidfile=PIDLockFile(var.MAINTENANCE_PIDFILE_PATH, timeout=2.0),
        files_preserve=files_preserve
        ) as context:
        _LOGGER.info("Gateway maintenance started.")
        client = create_gateway_client(account=account, password=password)
        client.maintain()

if __name__ == "__main__":
    account = input('Account: ')
    password = getpass('Password: ')
    start_maintenance_daemon(account, password)
