import argparse
import logging
import os
import sys
from pathlib import Path

_this_filedir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, str(Path(_this_filedir).parent))

from ibeam import config

config.initialize()

from ibeam.src.gateway_client import GatewayClient

_LOGGER = logging.getLogger('ibeam')


def parse_args():
    parser = argparse.ArgumentParser(description='Start, authenticate and verify the IB Gateway.')
    parser.add_argument('-a', '--authenticate', action='store_true', help='Authenticates the existing gateway.')
    parser.add_argument('-k', '--kill', action='store_true', help='Kill the gateway.')
    parser.add_argument('-m', '--maintain', action='store_true', help='Maintain the gateway.')
    parser.add_argument('-s', '--start', action='store_true', help='Start the gateway.')
    parser.add_argument('-t', '--tickle', action='store_true', help='Tickle the gateway.')
    parser.add_argument('-u', '--user', action='store_true', help='Get the user.')
    parser.add_argument('-c', '--check', action='store_true', help='Check if session is authenticated.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output.')

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_args()
    # print(args)
    client = GatewayClient()

    if args.verbose:
        _LOGGER.setLevel(logging.DEBUG)

    if args.start:
        pid = client.try_starting()
        success = pid is not None
        if success:
            _LOGGER.info(f'Gateway running with pid: {pid}')
        else:
            _LOGGER.info(f'Gateway not running.')
    elif args.authenticate:
        success = client.try_authenticating()
        _LOGGER.info(f'Gateway {"" if success else "not "}authenticated.')
    elif args.check:
        status = client.get_status()
        if status[1]:
            _LOGGER.info(f'Gateway session {"" if status[2] else "not "}authenticated.')
        else:
            _LOGGER.info(f'No active Gateway session.')
    elif args.tickle:
        success = client.tickle()
        _LOGGER.info(f'Gateway {"" if success else "not "}running.')
    elif args.user:
        client.user()
    elif args.maintain:
        client.maintain()
    elif args.kill:
        success = client.kill()
        _LOGGER.info(f'Gateway {"" if success else "not "}killed.')
    else:
        success = client.start_and_authenticate()
        if success:
            _LOGGER.info('Gateway running and authenticated.')
