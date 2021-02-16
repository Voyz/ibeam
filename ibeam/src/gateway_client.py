import json
import logging
import os
import shutil
import socket
import ssl
import sys
import time
import urllib.request
import urllib.parse
from getpass import getpass

from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ibeam.src import var
from ibeam.src.authenticate import authenticate_gateway
from ibeam.src.http_handler import HttpHandler
from ibeam.src.inputs_handler import InputsHandler
from ibeam.src.process_utils import find_procs_by_name, start_gateway

sys.path.insert(0, str(Path(__file__).parent.parent))

from ibeam import config

config.initialize()

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)


class GatewayClient():

    def __init__(self,
                 http_handler: HttpHandler,
                 inputs_handler: InputsHandler,
                 account: str = None,
                 password: str = None,
                 key: str = None,
                 gateway_dir: str = None,
                 driver_path: str = None,
                 base_url: str = None):

        self.base_url = base_url if base_url is not None else var.GATEWAY_BASE_URL

        self.account = account if account is not None else os.environ.get('IBEAM_ACCOUNT')
        """IBKR account name."""

        self.password = password if password is not None else os.environ.get('IBEAM_PASSWORD')
        """IBKR password."""

        self.key = key if key is not None else os.environ.get('IBEAM_KEY')
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

        # gateway_root_dir = os.path.join(self.gateway_dir, 'root')
        #
        # config_source = os.path.join(self.inputs_dir, 'conf.yaml')
        # if os.path.isfile(config_source):
        #     config_target = os.path.join(gateway_root_dir, 'conf.yaml')
        #     shutil.copy2(config_source, config_target)
        #
        # if self.http_handler.do_tls:
        #     cacert_target = os.path.join(gateway_root_dir, os.path.basename(self.http_handler.cecert_jks_path))
        #     shutil.copy2(self.http_handler.cecert_jks_path, cacert_target)

        self._threads = 4

    def try_starting(self) -> Optional[int]:
        processes = find_procs_by_name(var.GATEWAY_PROCESS_MATCH)
        if not processes:
            _LOGGER.info('Gateway not found, starting new one...')

            start_gateway(self.gateway_dir)

            time.sleep(var.GATEWAY_STARTUP)

            processes = find_procs_by_name(var.GATEWAY_PROCESS_MATCH)
            success = len(processes) != 0
            if not success:
                return None

            self.server_process = processes[0].pid
            _LOGGER.info(f'Gateway started with pid: {self.server_process}')

        return processes[0].pid

    def _authenticate(self) -> bool:
        return authenticate_gateway(self.driver_path, self.account, self.password, self.key, self.base_url)

    # def _reauthenticate(self):
    #     self._try_request(self.base_url + _ROUTE_REAUTHENTICATE, False)

    def try_authenticating(self, request_retries=1) -> bool:
        status = self.get_status(max_attempts=request_retries)
        if status[2]:  # running and authenticated
            return True
        elif not status[0]:  # no gateway running
            return False
        else:
            if status[1]:
                _LOGGER.info('Gateway session found but not authenticated, authenticating...')

                """
                Annoyingly this is an async request that takes arbitrary amount of time and returns no
                meaningful response. For now we stick with full login instead of calling reauthenticate. 
                """
                # self._reauthenticate()
            else:
                _LOGGER.info('No active sessions, logging in...')

            success = self._authenticate()
            _LOGGER.info(f'Login {"succeeded" if success else "failed"}')
            if not success:
                return False
            # self._try_request(self.base_url + _ROUTE_VALIDATE, False, max_attempts=REQUEST_RETRIES)

            time.sleep(1)  # a small buffer for session to be authenticated

            # double check if authenticated
            status = self.get_status(max_attempts=request_retries)
            if not status[2]:
                if status[1]:
                    _LOGGER.error('Gateway session active but not authenticated')
                elif status[0]:
                    _LOGGER.error('Gateway running but has no active sessions')
                else:
                    _LOGGER.error('Gateway not running and not authenticated')
                return False

        return True

    def get_status(self, max_attempts=1) -> (bool, bool, bool):
        return self.http_handler.try_request(self.base_url + var.ROUTE_TICKLE, True, max_attempts=max_attempts)

    def validate(self) -> bool:
        return self.http_handler.try_request(self.base_url + var.ROUTE_VALIDATE, False)[1]

    def tickle(self) -> bool:
        return self.http_handler.try_request(self.base_url + var.ROUTE_TICKLE, True)[0]

    def user(self):
        try:
            response = self.http_handler.url_request(self.base_url + var.ROUTE_USER)
            _LOGGER.info(response.read())
        except Exception as e:
            _LOGGER.exception(e)

    def start_and_authenticate(self, request_retries=1) -> bool:
        """Starts the gateway and authenticates using the credentials stored."""

        self.try_starting()

        success = self.try_authenticating(request_retries=request_retries)

        return success

    def maintain(self):
        executors = {'default': ThreadPoolExecutor(self._threads)}
        job_defaults = {'coalesce': False, 'max_instances': self._threads}
        self._scheduler = BlockingScheduler(executors=executors, job_defaults=job_defaults, timezone='UTC')
        self._scheduler.add_job(self._maintenance, trigger=IntervalTrigger(seconds=var.MAINTENANCE_INTERVAL))
        _LOGGER.info(f'Starting maintenance with interval {var.MAINTENANCE_INTERVAL} seconds')
        self._scheduler.start()

    def _maintenance(self):
        _LOGGER.debug('Maintenance')

        success = self.start_and_authenticate(request_retries=var.REQUEST_RETRIES)

        if success:
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

        return True
