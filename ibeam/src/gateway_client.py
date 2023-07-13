import logging
import os
import sys
import time

from pathlib import Path
from typing import Optional, List
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ibeam.src import var
from ibeam.src.health_server import new_health_server
from ibeam.src.handlers.http_handler import HttpHandler, Status
from ibeam.src.utils.process_utils import try_starting_gateway, kill_gateway
from ibeam.src.handlers.strategy_handler import StrategyHandler

sys.path.insert(0, str(Path(__file__).parent.parent))

from ibeam import config

config.initialize()

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)

class GatewayClient():

    def __init__(self,
                 http_handler: HttpHandler,
                 strategy_handler: StrategyHandler,
                 gateway_dir: os.PathLike = None):

        self._should_shutdown = False

        self.gateway_dir = gateway_dir

        self.http_handler = http_handler
        self.strategy_handler = strategy_handler

        self._concurrent_maintenance_attempts = 1
        self._health_server = new_health_server(var.HEALTH_SERVER_PORT, self.http_handler.get_status, self.get_shutdown_status)

    def try_starting(self) -> Optional[List[int]]:
        return try_starting_gateway(
            gateway_process_match=var.GATEWAY_PROCESS_MATCH,
            gateway_dir=self.gateway_dir,
            gateway_startup=var.GATEWAY_STARTUP,
            verify_connection=self.http_handler.base_route,
        )

    def get_shutdown_status(self) -> bool:
        return self._should_shutdown


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
