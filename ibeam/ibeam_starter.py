import argparse
import logging
import os
import sys
from pathlib import Path

from ibeam.config import Config
from ibeam.src.handlers.credentials_handler import CredentialsHandler
from ibeam.src.handlers.login_handler import LoginHandler
from ibeam.src.handlers.secrets_handler import SecretsHandler
from ibeam.src.handlers.strategy_handler import StrategyHandler

_this_filedir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, str(Path(_this_filedir).parent))

import ibeam

from ibeam.src.gateway_client import GatewayClient
from ibeam.src.handlers.http_handler import HttpHandler
from ibeam.src import var, two_fa_selector, logs
from ibeam.src.handlers.inputs_handler import InputsHandler

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
    from ibeam.src import logs
    logs.initialize()

    cnf = Config()

    _LOGGER.info(f'############ Starting IBeam version {ibeam.__version__} ############')
    args = parse_args()

    if args.verbose:
        logs.set_level_for_all(_LOGGER, logging.DEBUG)


    inputs_handler = InputsHandler(inputs_dir=cnf.INPUTS_DIR, gateway_dir=cnf.GATEWAY_DIR)
    http_handler = HttpHandler(inputs_handler=inputs_handler, base_url=cnf.GATEWAY_BASE_URL)

    two_fa_handler = two_fa_selector.select(cnf.TWO_FA_HANDLER, cnf.CHROME_DRIVER_PATH, cnf.CUSTOM_TWO_FA_HANDLER, inputs_handler)

    _LOGGER.info(f'Secrets source: {cnf.SECRETS_SOURCE}')
    secrets_handler = SecretsHandler(secrets_source=cnf.SECRETS_SOURCE)

    credentials_handler = CredentialsHandler(secrets_handler=secrets_handler)
    login_handler = LoginHandler(cnf, credentials_handler=credentials_handler, two_fa_handler=two_fa_handler)

    strategy_handler = StrategyHandler(
        http_handler=http_handler,
        login_handler=login_handler,
        authentication_strategy=cnf.AUTHENTICATION_STRATEGY,
        reauthenticate_wait=cnf.REAUTHENTICATE_WAIT,
        restart_failed_sessions=cnf.RESTART_FAILED_SESSIONS,
        restart_wait=cnf.RESTART_WAIT,
        max_reauthenticate_retries=cnf.MAX_REAUTHENTICATE_RETRIES,
        max_status_check_retries=cnf.MAX_STATUS_CHECK_RETRIES,
        gateway_process_match=cnf.GATEWAY_PROCESS_MATCH,
    )

    client = GatewayClient(
        http_handler=http_handler,
        strategy_handler=strategy_handler,
        gateway_dir=cnf.GATEWAY_DIR,
    )

    _LOGGER.info(f'Configuration:\n{cnf.all_variables}')

    if args.start:
        pids = client.try_starting()
        if pids is not None:
            _LOGGER.info(f'Gateway running with pids: {pids}')
        else:
            _LOGGER.info(f'Gateway not running.')
    elif args.authenticate:
        success, _ = strategy_handler.try_authenticating()
        _LOGGER.info(f'Gateway {"" if success else "not "}authenticated.')
    elif args.check:
        status = http_handler.get_status()
        if not status.session:
            _LOGGER.info(f'No active Gateway session.')
        else:
            _LOGGER.info(f'Gateway session {"" if status.authenticated else "not "}authenticated.')
    elif args.tickle:
        success = http_handler.tickle().running
        _LOGGER.info(f'Gateway {"" if success else "not "}running.')
    elif args.maintain:
        client.maintain()
    elif args.kill:
        success = client.kill()
        _LOGGER.info(f'Gateway {"" if success else "not "}killed.')
    else:
        # we have to do this here first because APS waits before running it the first time
        success, shutdown, status = client.start_and_authenticate()
        if success:
            _LOGGER.info(f'Gateway running and authenticated, session id: {status.session_id}, server name: {status.server_name}')

        if shutdown:
            _LOGGER.warning('Shutting IBeam down due to critical error.')
        else:
            client.maintain()
