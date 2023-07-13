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
from ibeam.src.login.authenticate import log_in
from ibeam.src.handlers.http_handler import HttpHandler, Status
from ibeam.src.handlers.inputs_handler import InputsHandler
from ibeam.src.utils.process_utils import try_starting_gateway, kill_gateway
from ibeam.src.handlers.secrets_handler import SecretsHandler
from ibeam.src.handlers.strategy_handler import StrategyHandler
from ibeam.src.two_fa_handlers.two_fa_handler import TwoFaHandler

sys.path.insert(0, str(Path(__file__).parent.parent))

from ibeam import config

config.initialize()

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)

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


        self.strategy_handler = StrategyHandler(
            http_handler=self.http_handler,
            authentication_strategy=var.AUTHENTICATION_STRATEGY,
            reauthenticate_wait=var.REAUTHENTICATE_WAIT,
            restart_failed_sessions=var.RESTART_FAILED_SESSIONS,
            restart_wait=var.RESTART_WAIT,
            max_reauthenticate_retries=var.MAX_REAUTHENTICATE_RETRIES,
            max_status_check_retries=var.MAX_STATUS_CHECK_RETRIES,
            gateway_process_match=var.GATEWAY_PROCESS_MATCH,
            log_in_function=self._log_in,
        )


        self._concurrent_maintenance_attempts = 1
        self._health_server = new_health_server(var.HEALTH_SERVER_PORT, self.http_handler.get_status, self.get_shutdown_status)

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

    def get_shutdown_status(self) -> bool:
        return self._should_shutdown

    def user(self):
        try:
            response = self.http_handler.url_request(self.base_url + var.ROUTE_USER)
            _LOGGER.info(response.read())
        except Exception as e:
            _LOGGER.exception(e)

    def start_and_authenticate(self, request_retries=1) -> (bool, bool, Status):
        """Starts the gateway and authenticates using the credentials stored."""

        self.try_starting()

        success, shutdown, status = self.strategy_handler.try_authenticating(request_retries=request_retries)
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
