import json
import logging
import os
import sys
import time
from getpass import getpass

from pathlib import Path
from typing import Optional, List
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ibeam.src import var
from ibeam.src.health_server import new_health_server
from ibeam.src.authenticate import log_in
from ibeam.src.http_handler import HttpHandler, Status
from ibeam.src.inputs_handler import InputsHandler
from ibeam.src.process_utils import try_starting_gateway, kill_gateway
from ibeam.src.secrets_handler import SecretsHandler
from ibeam.src.two_fa_handlers.two_fa_handler import TwoFaHandler

sys.path.insert(0, str(Path(__file__).parent.parent))

from ibeam import config

config.initialize()

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)


def condition_authenticated_true(status:Status) -> bool:
    # unhappy cases, we don't need to keep on retrying
    if not status.running or not status.session:
        return True

    # happy case, wa don't need to keep on retrying
    if status.authenticated:
        return True

    return False

def condition_logged_out(status:Status) -> bool:
    # unhappy cases, we don't need to keep on retrying
    if not status.running or not status.session or status.competing:
        return True

    # happy case, wa don't need to keep on retrying
    if not status.connected and not status.authenticated:
        return True

    return False

def condition_not_competing(status:Status) -> bool:
    # unhappy cases, we don't need to keep on retrying
    if not status.running or not status.session:
        return True

    # happy case, wa don't need to keep on retrying
    if not status.competing and status.connected and status.authenticated:
        return True

    return False
class GatewayClient():

    def __init__(self,
                 http_handler: HttpHandler,
                 inputs_handler: InputsHandler,
                 two_fa_handler: TwoFaHandler,
                 secrets_handler: SecretsHandler,
                 account: str = None,
                 password: str = None,
                 key: str = None,
                 gateway_dir: os.PathLike = None,
                 driver_path: str = None,
                 base_url: str = None):

        self._should_shutdown = False

        self.gateway_dir = gateway_dir
        self.driver_path = driver_path

        self.http_handler = http_handler
        self.inputs_handler = inputs_handler
        self.two_fa_handler = two_fa_handler
        self.secrets_handler = secrets_handler


        self.encoding = os.environ.get(
            'IBEAM_ENCODING', default='UTF-8')
        """Character encoding for secret files"""

        self.base_url = base_url if base_url is not None else var.GATEWAY_BASE_URL

        self.account = account if account is not None else self.secrets_handler.secret_value(self.encoding, 'IBEAM_ACCOUNT')
        """IBKR account name."""

        self.password = password if password is not None else self.secrets_handler.secret_value(self.encoding, 'IBEAM_PASSWORD')
        """IBKR password."""

        self.key = key if key is not None else self.secrets_handler.secret_value(self.encoding, 'IBEAM_KEY')
        """Key to the IBKR password."""

        if self.account is None:
            self.account = input('Account: ')

        if self.password is None:
            self.password = getpass('Password: ')
            if self.key is None:
                self.key = getpass('Key: ') or None



        self._concurrent_maintenance_attempts = 1
        self._health_server = new_health_server(var.HEALTH_SERVER_PORT, self.get_status, self.get_shutdown_status)

    def try_starting(self) -> Optional[List[int]]:
        return try_starting_gateway(
            gateway_process_match=var.GATEWAY_PROCESS_MATCH,
            gateway_dir=self.gateway_dir,
            gateway_startup=var.GATEWAY_STARTUP,
            verify_connection=lambda: self.http_handler.try_request(self.base_url),
        )

    def _log_in(self) -> (bool, bool):
        return log_in(driver_path=self.driver_path,
                      account=self.account,
                      password=self.password,
                      key=self.key,
                      base_url=self.base_url,
                      two_fa_handler=self.two_fa_handler)

    def try_authenticating(self, request_retries=1) -> (bool, bool, Status):

        status = self.get_status(max_attempts=request_retries)
        if status.authenticated and not status.competing:  # running, authenticated and not competing
            return True, False, status

        _LOGGER.info(str(status))

        if not status.running:  # no gateway running
            _LOGGER.error('Cannot communicate with the Gateway. Consider increasing IBEAM_GATEWAY_STARTUP')
            return False, False, status
        else:
            authentication_strategy = var.AUTHENTICATION_STRATEGY
            _LOGGER.info(f'Authentication strategy: "{authentication_strategy}"')

            if authentication_strategy == 'A':
                return self._authentication_strategy_A(status=status, request_retries=request_retries)
            elif authentication_strategy == 'B':
                return self._authentication_strategy_B(status=status, request_retries=request_retries)
            else:
                _LOGGER.error(f'Unknown authentication strategy: "{authentication_strategy}". Defaulting to strategy A.')
                return self._authentication_strategy_A(status=status, request_retries=request_retries)



    def _authentication_strategy_A(self, status:Status, request_retries=1) -> (bool, bool, Status):
        if status.session:
            if not status.connected or status.competing:
                _LOGGER.info('Competing Gateway session found, restarting and logging in...')
                self._logout()

            _LOGGER.info('Gateway session found but not authenticated, logging in...')
        else:
            _LOGGER.info('No active sessions, logging in...')

        success, shutdown = self._log_in()
        _LOGGER.info(f'Logging in {"succeeded" if success else "failed"}')
        if shutdown:
            return False, True, status
        if not success:
            return False, False, status

        time.sleep(3)  # buffer for session to be authenticated

        # double check if authenticated
        status = self.get_status(max_attempts=max(request_retries, 2))
        if not status.authenticated:
            if status.session:
                _LOGGER.error('Logging in succeeded, but active session is still not authenticated')
                self.reauthenticate()

                if var.REAUTHENTICATE_WAIT > 0:
                    _LOGGER.info(f'Waiting {var.REAUTHENTICATE_WAIT} seconds to reauthenticate before restarting.')
                    time.sleep(var.REAUTHENTICATE_WAIT)

                if var.RESTART_FAILED_SESSIONS:
                    _LOGGER.info('Logging out and reattempting full authentication')
                    self._logout()
                    return self.try_authenticating(request_retries=request_retries)
            elif status.running:
                _LOGGER.error('Logging in succeeded but there are still no active sessions')
            else:
                _LOGGER.error('Logging in succeeded but now cannot communicate with the Gateway')
            return False, False, status
        elif status.competing:
            _LOGGER.info('Logging in succeeded, session is authenticated but competing, reauthenticating...')
            self.reauthenticate()
            time.sleep(var.RESTART_WAIT)
            return False, False, status

        return True, False, status


    def _authentication_strategy_B(self, status:Status, request_retries=1) -> (bool, bool, Status):
        original_status = status
        if not original_status.session:
            _LOGGER.info('No active sessions, logging in...')

            success, shutdown = self._log_in()
            _LOGGER.info(f'Logging in {"succeeded" if success else "failed"}')
            if shutdown:
                return False, True, original_status # critical, shut down
            if not success:
                return False, False, original_status # unsuccessful, reattempt on next maintenance
        elif not original_status.connected or original_status.competing:
            _LOGGER.info('Competing or disconnected Gateway session found, logging out and reauthenticating...')
            self._logout()
            self.reauthenticate()
        else:
            _LOGGER.info('Active session found but not authenticated, reauthenticating...')
            self.reauthenticate()

        # if we only just logged in and succeeded, this will not reauthenticate but only check status
        status = self._repeatedly_reauthenticate(var.MAX_REAUTHENTICATE_RETRIES, condition_authenticated_true)

        if not status.running or not status.session:
            return False, False, status

        if not status.connected or status.competing or not status.authenticated:
            _LOGGER.error(f'Repeatedly reauthenticating failed {var.MAX_REAUTHENTICATE_RETRIES} times. Killing the Gateway and restarting the authentication process.')

            success = self.kill()
            if not success:
                _LOGGER.error(f'Killing the Gateway process failed')

            return False, False, status

        return True, False, status

    def _repeatedly_check_status(self, max_attempts=1, condition:callable=condition_authenticated_true):
        if max_attempts <= 1:
            # no need to do recursion in this case
            return self.get_status()

        if not callable(condition):
            raise ValueError(f'Condition must be a callable, found: "{type(condition)}": {condition}')

        def _check(attempt=0):
            status = self.get_status()

            if condition(status):
                return status

            if attempt >= max_attempts - 1:
                _LOGGER.info(
                    f'Max status check retries reached after {max_attempts} attempts. Consider increasing the retries by setting IBEAM_MAX_STATUS_CHECK_ATTEMPTS environment variable')
                return status
            else:
                time.sleep(1)
                if attempt == 0:
                    _LOGGER.info(f'Repeating status check attempts another {max_attempts - attempt - 1} times')
                return _check(attempt + 1)

        return _check(0)

    def _repeatedly_reauthenticate(self, max_attempts=1, condition:callable=condition_authenticated_true):

        if max_attempts <= 1:
            # no need to do recursion in this case
            self.reauthenticate()
            return self._repeatedly_check_status(var.MAX_STATUS_CHECK_RETRIES, condition)

        if not callable(condition):
            raise ValueError(f'Condition must be a callable, found: "{type(condition)}": {condition}')

        def _reauthenticate(attempt=0):
            status = self._repeatedly_check_status(var.MAX_STATUS_CHECK_RETRIES, condition)
            _LOGGER.info(str(status))

            if attempt >= max_attempts - 1:
                _LOGGER.info(
                    f'Max reauthenticate retries reached after {max_attempts} attempts. Consider increasing the retries by setting IBEAM_MAX_REAUTHENTICATE_RETRIES environment variable')
                return status

            if condition(status):
                return status

            self.reauthenticate()
            _LOGGER.info(f'Repeated reauthentication attempt number {attempt + 2}')
            return _reauthenticate(attempt + 1)

        return _reauthenticate(0)


    def get_shutdown_status(self) -> bool:
        return self._should_shutdown

    def get_status(self, max_attempts=1) -> Status:
        status = self.tickle()
        if status.session:
            status.response = json.loads(status.response.read().decode('utf8'))
            # some fields are not present if unauthenticated
            status.authenticated = status.response['iserver']['authStatus']['authenticated']
            status.competing = status.response['iserver']['authStatus']['competing']
            status.connected = status.response['iserver']['authStatus']['connected']
            status.collision = status.response['collission']
            status.session_id = status.response['session']
            status.expires = int(status.response['ssoExpires'])
            status.server_name = status.response['iserver']['authStatus'].get('serverInfo', {}).get('serverName')
            status.server_version = status.response['iserver']['authStatus'].get('serverInfo', {}).get('serverVersion')
        return status

    def validate(self) -> bool:
        """Validate provides information on the current session. Works also after logout."""
        status = self.http_handler.try_request(self.base_url + var.ROUTE_VALIDATE, 'GET')
        if status.session:
            status.response = json.loads(status.response.read().decode('utf8'))
            return status.response['RESULT']
        return False

    def tickle(self) -> Status:
        return self.http_handler.try_request(self.base_url + var.ROUTE_TICKLE, 'POST')

    def logout(self):
        """Logout will log the user out, but maintain the session, allowing us to reauthenticate directly."""
        return self.http_handler.url_request(self.base_url + var.ROUTE_LOGOUT, 'POST')

    def reauthenticate(self):
        """Reauthenticate will work only if there is an existing session."""
        return self.http_handler.url_request(self.base_url + var.ROUTE_REAUTHENTICATE, 'POST')

    def _logout(self):
        try:
            logout_response = self.logout()
            logout_success = logout_response.read().decode('utf8') == '{"status":true}'
            _LOGGER.info(f'Gateway logout {"successful" if logout_success else "unsuccessful"}')
        except Exception as e:
            _LOGGER.error(f'Exception during logout: {e}')


    def user(self):
        try:
            response = self.http_handler.url_request(self.base_url + var.ROUTE_USER)
            _LOGGER.info(response.read())
        except Exception as e:
            _LOGGER.exception(e)

    def start_and_authenticate(self, request_retries=1) -> (bool, bool, Status):
        """Starts the gateway and authenticates using the credentials stored."""

        self.try_starting()

        success, shutdown, status = self.try_authenticating(request_retries=request_retries)
        self._should_shutdown = shutdown
        return success, shutdown, status

    def build_scheduler(self):
        if var.SPAWN_NEW_PROCESSES:
            executors = {'default': ProcessPoolExecutor(self._concurrent_maintenance_attempts)}
        else:
            executors = {'default': ThreadPoolExecutor(self._concurrent_maintenance_attempts)}
        job_defaults = {'coalesce': False, 'max_instances': self._concurrent_maintenance_attempts}
        self._scheduler = BackgroundScheduler(executors=executors, job_defaults=job_defaults, timezone='UTC')
        self._scheduler.add_job(self._maintenance, trigger=IntervalTrigger(seconds=var.MAINTENANCE_INTERVAL))

    def maintain(self):
        self.build_scheduler()
        _LOGGER.info(f'Starting maintenance with interval {var.MAINTENANCE_INTERVAL} seconds')
        self._scheduler.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt as e:
            _LOGGER.info('Keyboard interrupt, shutting down.')
            pass
        self._scheduler.remove_all_jobs()
        self._scheduler.shutdown(wait=False)
        if self._health_server:
            self._health_server.shutdown()

    def _maintenance(self):
        _LOGGER.info('Maintenance')

        success, shutdown, status = self.start_and_authenticate(request_retries=var.REQUEST_RETRIES)

        if shutdown:
            _LOGGER.warning('Shutting IBeam down due to critical error.')
            self._scheduler.remove_all_jobs()
            self._scheduler.shutdown(False)
            if self._health_server:
                self._health_server.shutdown()
        elif success:
            _LOGGER.info(f'Gateway running and authenticated, session id: {status.session_id}, server name: {status.server_name}')

    def kill(self) -> bool:
        return kill_gateway(var.GATEWAY_PROCESS_MATCH)

    def __getstate__(self):
        state = self.__dict__.copy()

        # APS schedulers and health_server can't be pickled
        del state['_scheduler']
        del state['_health_server']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.build_scheduler()
