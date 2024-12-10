import argparse
import logging
import os
import signal
import sys
from pathlib import Path

def add_to_path():
    _this_filedir = os.path.abspath(os.path.dirname(__file__))
    sys.path.insert(0, str(Path(_this_filedir).parent))

add_to_path()

from ibeam.config import Config
from ibeam.src.handlers.login_handler import LoginHandler
from ibeam.src.handlers.process_handler import ProcessHandler
from ibeam.src.handlers.secrets_handler import SecretsHandler
from ibeam.src.handlers.strategy_handler import StrategyHandler
from ibeam.src.login.driver import DriverFactory, shut_down_browser
from ibeam.src.login.targets import create_targets

import ibeam

from ibeam.src.gateway_client import GatewayClient
from ibeam.src.handlers.http_handler import HttpHandler
from ibeam.src import var, two_fa_selector
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
    cnf = Config(var.all_variables)

    from ibeam.src import logs
    logs.initialize(
        log_format=cnf.LOG_FORMAT,
        log_level=cnf.LOG_LEVEL,
        log_to_file=cnf.LOG_TO_FILE,
        outputs_dir=cnf.OUTPUTS_DIR,
    )


    _LOGGER.info(f'############ Starting IBeam version {ibeam.__version__} ############')
    args = parse_args()

    if args.verbose:
        logs.set_level_for_all(_LOGGER, logging.DEBUG)

    inputs_handler = InputsHandler(inputs_dir=cnf.INPUTS_DIR, gateway_dir=cnf.GATEWAY_DIR)

    http_handler = HttpHandler(
        inputs_handler=inputs_handler,
        base_url=cnf.GATEWAY_BASE_URL,
        route_validate=cnf.ROUTE_VALIDATE,
        route_tickle=cnf.ROUTE_TICKLE,
        route_logout=cnf.ROUTE_LOGOUT,
        route_reauthenticate=cnf.ROUTE_REAUTHENTICATE,
        route_initialise=cnf.ROUTE_INITIALISE,
        request_timeout=cnf.REQUEST_TIMEOUT,
    )

    driver_factory = DriverFactory(
        driver_path=cnf.CHROME_DRIVER_PATH,
        ui_scaling=cnf.UI_SCALING,
        page_load_timeout=cnf.PAGE_LOAD_TIMEOUT,
    )

    two_fa_handler = two_fa_selector.select(
        handler_name=cnf.TWO_FA_HANDLER,
        driver_factory=driver_factory,
        outputs_dir=cnf.OUTPUTS_DIR,
        custom_two_fa_handler=cnf.CUSTOM_TWO_FA_HANDLER,
        inputs_dir=cnf.INPUTS_DIR,
    )

    _LOGGER.info(f'Secrets source: {cnf.SECRETS_SOURCE}')
    secrets_handler = SecretsHandler(secrets_source=cnf.SECRETS_SOURCE, gcp_base_url=cnf.GCP_SECRETS_URL)

    targets = create_targets(cnf)

    login_handler = LoginHandler(
        secrets_handler=secrets_handler,
        two_fa_handler=two_fa_handler,
        driver_factory=driver_factory,
        targets=targets,
        base_url=cnf.GATEWAY_BASE_URL,
        route_auth=cnf.ROUTE_AUTH,
        two_fa_select_target=cnf.TWO_FA_SELECT_TARGET,
        strict_two_fa_code=cnf.STRICT_TWO_FA_CODE,
        max_immediate_attempts=cnf.MAX_IMMEDIATE_ATTEMPTS,
        oauth_timeout=cnf.OAUTH_TIMEOUT,
        max_presubmit_buffer=cnf.MAX_PRESUBMIT_BUFFER,
        min_presubmit_buffer=cnf.MIN_PRESUBMIT_BUFFER,
        max_failed_auth=cnf.MAX_FAILED_AUTH,
        outputs_dir=cnf.OUTPUTS_DIR,
    )

    process_handler = ProcessHandler(
        gateway_process_match=cnf.GATEWAY_PROCESS_MATCH,
        gateway_dir=cnf.GATEWAY_DIR,
        gateway_startup=cnf.GATEWAY_STARTUP,
        verify_connection=http_handler.base_route,
    )

    strategy_handler = StrategyHandler(
        http_handler=http_handler,
        login_handler=login_handler,
        process_handler=process_handler,
        authentication_strategy=cnf.AUTHENTICATION_STRATEGY,
        reauthenticate_wait=cnf.REAUTHENTICATE_WAIT,
        restart_failed_sessions=cnf.RESTART_FAILED_SESSIONS,
        restart_wait=cnf.RESTART_WAIT,
        max_reauthenticate_retries=cnf.MAX_REAUTHENTICATE_RETRIES,
        max_status_check_retries=cnf.MAX_STATUS_CHECK_RETRIES,
    )

    client = GatewayClient(
        http_handler=http_handler,
        strategy_handler=strategy_handler,
        process_handler=process_handler,
        health_server_port=cnf.HEALTH_SERVER_PORT,
        spawn_new_processes=cnf.SPAWN_NEW_PROCESSES,
        maintenance_interval=cnf.MAINTENANCE_INTERVAL,
        request_retries=cnf.REQUEST_RETRIES,
        active=cnf.START_ACTIVE,
    )

    def stop(_, _1):
        client.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    _LOGGER.info(f'Configuration:\n{cnf.all_variables}')

    if args.start:
        pids = process_handler.start_gateway()
        if pids is not None:
            _LOGGER.info(f'Gateway running with pids: {pids}')
        else:
            _LOGGER.info(f'Gateway not running.')
        while True:
            pass
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
        success = process_handler.kill_gateway()
        _LOGGER.info(f'Gateway {"" if success else "not "}killed.')
    else:
        # we have to do this here first because APS waits before running it the first time
        if client.active:
            success, shutdown, status = client.start_and_authenticate()
            if success:
                _LOGGER.info(f'Gateway running and authenticated, session id: {status.session_id}, server name: {status.server_name}')

            if shutdown:
                _LOGGER.warning('Shutting IBeam down due to critical error.')
            else:
                client.maintain()
        else:
            _LOGGER.info(f'IBeam initialised in an inactive state. Starting maintenance loop.')
            client.maintain()
