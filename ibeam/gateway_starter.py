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
    parser.add_argument('-a', '--only-authenticate', action='store_true',
                        help='Only authenticates the existing gateway.')
    parser.add_argument('-s', '--only-start', action='store_true', help='Only start the gateway.')
    parser.add_argument('-v', '--verify', action='store_true', help='Verify authentication.')
    parser.add_argument('-t', '--tickle', action='store_true', help='Tickle the gateway.')
    parser.add_argument('-u', '--user', action='store_true', help='Get the user.')

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_args()
    # print(args)
    client = GatewayClient()

    if args.only_start:
        client.start()
    elif args.only_authenticate:
        success = client.authenticate()
        _LOGGER.info(f'Authentication {"succeeded" if success else "failed"}')
    elif args.verify:
        success = client.verify()
        _LOGGER.info(f'Gateway {"" if success else "not "}authenticated.')
    elif args.tickle:
        success = client.tickle()
        _LOGGER.info(f'Gateway {"" if success else "not "}running.')
    elif args.user:
        client.user()
    else:
        client.start_and_authenticate()
