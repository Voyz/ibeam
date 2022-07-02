import logging
import os
import sys
import time
from getpass import getpass

from pathlib import Path
from typing import Optional
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ibeam.src import var
from ibeam.src.health_server import new_health_server
from ibeam.src.authenticate import authenticate_gateway
from ibeam.src.http_handler import HttpHandler, Status
from ibeam.src.inputs_handler import InputsHandler
from ibeam.src.process_utils import find_procs_by_name, start_gateway
from ibeam.src.two_fa_handlers.two_fa_handler import TwoFaHandler

sys.path.insert(0, str(Path(__file__).parent.parent))

from ibeam import config

config.initialize()

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)

SECRETS_SOURCE_ENV = 'env'
SECRETS_SOURCE_FS = 'fs'


class GatewayClient():

    def __init__(self,
                 http_handler: HttpHandler,
                 inputs_handler: InputsHandler,
                 two_fa_handler: TwoFaHandler,
                 account: str = None,
                 password: str = None,
                 key: str = None,
                 gateway_dir: str = None,
                 driver_path: str = None,
                 base_url: str = None):

        self._should_shutdown = False

        self.secrets_source = os.environ.get(
            'IBEAM_SECRETS_SOURCE', default=SECRETS_SOURCE_ENV)
        """If IBEAM_SECRETS_SOURCE is set to
        SECRETS_SOURCE_ENV, or if it is not set, then
        environment values will be assumed to hold the
        secret values directly.

        If IBEAM_SECRETS_SOURCE is set to SECRETS_SOURCE_FS
        then the environment values are assumed to be file
        paths to read for the secret value."""

        _LOGGER.info(f'Secrets source: {self.secrets_source}')

        self.encoding = os.environ.get(
            'IBEAM_ENCODING', default='UTF-8')
        """Character encoding for secret files"""

        self.base_url = base_url if base_url is not None else var.GATEWAY_BASE_URL

        self.account = account if account is not None else self.secret_value('IBEAM_ACCOUNT')
        """IBKR account name."""

        self.password = password if password is not None else self.secret_value('IBEAM_PASSWORD')
        """IBKR password."""

        self.key = key if key is not None else self.secret_value('IBEAM_KEY')
        """Key to the IBKR password."""

        if self.account is None:
            self.account = input('Account: ')

        if self.password is None:
            self.password = getpass('Password: ')
            if self.key is None:
                self.key = getpass('Key: ') or None

        self.gateway_dir = gateway_dir
        self.driver_path = driver_path

        self.http_handler = http_handler
        self.inputs_handler = inputs_handler
        self.two_fa_handler = two_fa_handler

        self._concurrent_maintenance_attempts = 1
        self._health_server = new_health_server(var.IBEAM_HEALTH_SERVER_PORT, self.get_status, self.get_shutdown_status)

    def secret_value(self, name: str,
                     lstrip=None, rstrip='\r\n') -> str:
        """
        secret_value reads secrets from os.environ or from
        the filesystem.

        Given a name, such as 'IBEAM_ACCOUNT', it will
        examine os.environ for a value associated with that
        name.

        If no value has been set, None is returned.
        Otherwise the self.secrets_source will be evaluated
        to determine how to handle the value.

        If self.secrets_source has been set to
        SECRETS_SOURCE_ENV the os.environ value will be
        returned as the secret value.

        If self.secrets_source has been set to
        SECRETS_SOURCE_FS then the os.environ value is
        treated as a filesystem path.  The file will be read
        as text and its contents returned as the secret
        value.

        Parameters:
          name:
            The identifier for the value, e.g.,
            'IBEAM_ACCOUNT', 'IBEAM_PASSWORD', or
            'IBEAM_KEY'.
          lstrip:
            If not None, strip these characters from the
            left of the returned value (default: None).
          rstrip:
            If not None, strip these characters from the
            right of the returned value (default: '\r\n')
        Returns:
          If the name is not defined in os.environ then None
          is returned.

          If self.secrets_source is SECRETS_SOURCE_ENV then
          the os.environ value is returned as the secret
          value.

          If self.secrets_source is SECRETS_SOURCE_FS then
          the os.environ value is treated as file path.  The
          file is read as a text file and its contents
          returned as the secret value.

          If an error is encountered reading the file then
          an error is logged and None is returned.
        """
        # read the environment value for name
        value = os.environ.get(name)
        if value is None:
            # no key for this name, nothing to do
            return None

        if self.secrets_source == SECRETS_SOURCE_ENV:
            # treat environment values as the secrets themselves
            if lstrip is not None:
                value = value.lstrip(lstrip)

            if rstrip is not None:
                value = value.rstrip(rstrip)

            return value
        elif self.secrets_source == SECRETS_SOURCE_FS:
            # treat environment values as filesystem paths to the secrets
            if not os.path.isfile(value):
                _LOGGER.error(
                    f'Unable to read env value for {name}: value is not a file')
                return None

            try:
                with open(value, mode='rt', encoding=self.encoding) as fh:
                    secret = fh.read()

                    if lstrip is not None:
                        secret = secret.lstrip(lstrip)

                    if rstrip is not None:
                        secret = secret.rstrip(rstrip)

                    return secret
            except IOError:
                _LOGGER.error(
                    f'Unable to read env value for {name} as a file.')
                return None
        else:
            _LOGGER.error(
                f'Unknown Secrets Source: {self.secrets_source}')
            return None

    def try_starting(self) -> Optional[int]:
        processes = find_procs_by_name(var.GATEWAY_PROCESS_MATCH)
        if not processes:
            _LOGGER.info('Gateway not found, starting new one...')
            _LOGGER.info(
                'Note that the Gateway log below may display "Open https://localhost:5000 to login" - ignore this command.')

            start_gateway(self.gateway_dir)

            time.sleep(1)  # buffer to ensure process is running

            processes = find_procs_by_name(var.GATEWAY_PROCESS_MATCH)
            success = len(processes) != 0
            if not success:
                return None

            self.server_process = processes[0].pid
            _LOGGER.info(f'Gateway started with pid: {self.server_process}')

            # let's try to communicate with the Gateway
            t_end = time.time() + var.GATEWAY_STARTUP
            ping_success = False
            while time.time() < t_end:
                status = self.http_handler.try_request(self.base_url, False)
                if not status.running:
                    seconds_remaining = round(t_end - time.time())
                    if seconds_remaining > 0:
                        _LOGGER.debug(
                            f'Cannot ping Gateway. Retrying for another {seconds_remaining} seconds')
                        time.sleep(1)
                else:
                    _LOGGER.debug('Gateway connection established')
                    ping_success = True
                    break

            if not ping_success:
                _LOGGER.error('Gateway process found but cannot establish a connection with the Gateway')

        return processes[0].pid

    def _authenticate(self) -> (bool, bool):
        return authenticate_gateway(driver_path=self.driver_path,
                                    account=self.account,
                                    password=self.password,
                                    key=self.key,
                                    base_url=self.base_url,
                                    two_fa_handler=self.two_fa_handler)

    # def _reauthenticate(self):
    #     self._try_request(self.base_url + _ROUTE_REAUTHENTICATE, False)

    def try_authenticating(self, request_retries=1) -> (bool, bool):
        status = self.get_status(max_attempts=request_retries)
        if status.authenticated and not status.competing:  # running, authenticated and not competing
            return True, False
        elif not status.running:  # no gateway running
            _LOGGER.error('Cannot communicate with the Gateway. Consider increasing IBEAM_GATEWAY_STARTUP')
            return False, False
        else:
            if status.session:
                if status.competing:
                    _LOGGER.info('Competing Gateway session found, reauthenticating...')
                    self.restart()
                    # return False, False

                _LOGGER.info('Gateway session found but not authenticated, authenticating...')
            else:
                _LOGGER.info('No active sessions, logging in...')

            success, shutdown = self._authenticate()
            _LOGGER.info(f'Authentication process {"succeeded" if success else "failed"}')
            if shutdown:
                return False, True
            if not success:
                return False, False
            # self._try_request(self.base_url + _ROUTE_VALIDATE, False, max_attempts=REQUEST_RETRIES)

            time.sleep(3)  # buffer for session to be authenticated

            # double check if authenticated
            status = self.get_status(max_attempts=max(request_retries, 2))
            if not status.authenticated:
                if status.session:
                    _LOGGER.error('Gateway session active but not authenticated')
                    if var.RESTART_FAILED_SESSIONS:
                        _LOGGER.info('Logging out and restarting the Gateway')
                        self.restart()
                        return self.try_authenticating(request_retries=request_retries)
                elif status.running:
                    _LOGGER.error('Gateway running but has no active sessions')
                else:
                    _LOGGER.error('Cannot communicate with the Gateway')
                return False, False
            elif status.competing:
                _LOGGER.info('Authenticated but competing Gateway session found, reauthenticating...')
                self.reauthenticate()
                time.sleep(var.RESTART_WAIT)
                return False, False

        return True, False

    def get_shutdown_status(self) -> bool:
        return self._should_shutdown

    def get_status(self, max_attempts=1) -> Status:
        return self.http_handler.try_request(self.base_url + var.ROUTE_TICKLE, True, max_attempts=max_attempts)

    def validate(self) -> bool:
        return self.http_handler.try_request(self.base_url + var.ROUTE_VALIDATE, False).session

    def tickle(self) -> bool:
        return self.http_handler.try_request(self.base_url + var.ROUTE_TICKLE, True).running

    def logout(self):
        return self.http_handler.url_request(self.base_url + var.ROUTE_LOGOUT)

    def reauthenticate(self):
        return self.http_handler.url_request(self.base_url + var.ROUTE_REAUTHENTICATE)

    def restart(self):
        try:
            logout_response = self.logout()
            logout_success = logout_response.read().decode('utf8') == '{"status":true}'
            _LOGGER.info(f'Gateway logout {"successful" if logout_success else "unsuccessful"}')
        except Exception as e:
            _LOGGER.error(f'Exception during logout: {e}')

        # try:
        #     killed = self.kill()
        #     _LOGGER.info(f'Gateway shutdown {"successful" if killed else "unsuccessful"}')
        # except Exception as e:
        #     _LOGGER.error(f'Exception during shutdown: {e}')

    def user(self):
        try:
            response = self.http_handler.url_request(self.base_url + var.ROUTE_USER)
            _LOGGER.info(response.read())
        except Exception as e:
            _LOGGER.exception(e)

    def start_and_authenticate(self, request_retries=1) -> (bool, bool):
        """Starts the gateway and authenticates using the credentials stored."""

        self.try_starting()

        success, shutdown = self.try_authenticating(request_retries=request_retries)
        self._should_shutdown = shutdown
        return success, shutdown

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
        self._scheduler.shutdown(True)

    def _maintenance(self):
        _LOGGER.debug('Maintenance')

        success, shutdown = self.start_and_authenticate(request_retries=var.REQUEST_RETRIES)

        if shutdown:
            _LOGGER.warning('Shutting IBeam down due to critical error.')
            self._scheduler.remove_all_jobs()
            self._scheduler.shutdown(False)
            if self._health_server:
                self._health_server.shutdown()
        elif success:
            _LOGGER.info('Gateway running and authenticated')

    def kill(self) -> bool:
        processes = find_procs_by_name(var.GATEWAY_PROCESS_MATCH)
        if processes:
            processes[0].terminate()

            time.sleep(1)

            # double check we succeeded
            processes = find_procs_by_name(var.GATEWAY_PROCESS_MATCH)
            if processes:
                return False
        if self._health_server:
            self._health_server.shutdown()
        return True

    def __getstate__(self):
        state = self.__dict__.copy()

        # APS schedulers and health_server can't be pickled
        del state['_scheduler']
        del state['_health_server']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.build_scheduler()
