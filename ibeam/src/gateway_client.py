import json
import logging
import os
import shutil
import socket
import ssl
import subprocess
import sys
import time
import urllib.request
from getpass import getpass

from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError

import psutil
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from cryptography.fernet import Fernet
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from pyvirtualdisplay import Display
from selenium.webdriver.support.wait import WebDriverWait

sys.path.insert(0, str(Path(__file__).parent.parent))

from ibeam import config

config.initialize()

_GATEWAY_STARTUP = int(os.environ.get('IBEAM_GATEWAY_STARTUP', 3))
"""How many seconds to wait before attempting to communicate with the gateway after its startup."""

_GATEWAY_BASE_URL = os.environ.get('IBEAM_GATEWAY_BASE_URL', "https://localhost:5000")
"""Base URL of the gateway."""

_GATEWAY_PROCESS_MATCH = os.environ.get('IBEAM_GATEWAY_PROCESS_MATCH',
                                        'ibgroup.web.core.clientportal.gw.GatewayStart')
"""The gateway process' name to match against."""

_ROUTE_AUTH = os.environ.get('IBEAM_ROUTE_AUTH', '/sso/Login?forwardTo=22&RL=1&ip2loc=on')
"""Gateway route with authentication page."""

_ROUTE_USER = os.environ.get('IBEAM_ROUTE_USER', '/v1/api/one/user')
"""Gateway route with user information."""

_ROUTE_VALIDATE = os.environ.get('IBEAM_ROUTE_VALIDATE', '/v1/portal/sso/validate')
"""Gateway route with validation call."""

_ROUTE_REAUTHENTICATE = os.environ.get('IBEAM_ROUTE_REAUTHENTICATE', '/v1/portal/iserver/reauthenticate?force=true')
"""Gateway route with reauthentication call."""

_ROUTE_AUTH_STATUS = os.environ.get('IBEAM_ROUTE_AUTH_STATUS', '/v1/api/iserver/auth/status')
"""Gateway route with authentication status call."""

_ROUTE_TICKLE = os.environ.get('IBEAM_ROUTE_TICKLE', '/v1/api/tickle')
"""Gateway route with tickle call."""

_USER_NAME_EL_ID = os.environ.get('IBEAM_USER_NAME_EL_ID', 'user_name')
"""HTML element id containing the username input field."""

_PASSWORD_EL_ID = os.environ.get('IBEAM_PASSWORD_EL_ID', 'password')
"""HTML element id containing the password input field."""

_SUBMIT_EL_ID = os.environ.get('IBEAM_SUBMIT_EL_ID', 'submitForm')
"""HTML element id containing the submit button."""

_SUCCESS_EL_TEXT = os.environ.get('IBEAM_SUCCESS_EL_TEXT', 'Client login succeeds')
"""HTML element text indicating successful authentication."""

_MAINTENANCE_INTERVAL = int(os.environ.get('IBEAM_MAINTENANCE_INTERVAL', 60))
"""How many seconds between each maintenance."""

_LOG_LEVEL = os.environ.get('IBEAM_LOG_LEVEL', 'INFO')
"""Verbosity level of the logger used."""

_REQUEST_RETRIES = int(os.environ.get('IBEAM_REQUEST_RETRIES', 1))
"""How many times to reattempt a request to the gateway."""

_REQUEST_TIMEOUT = int(os.environ.get('IBEAM_REQUEST_TIMEOUT', 15))
"""How many seconds to wait for a request to complete."""

logging.getLogger('ibeam').setLevel(getattr(logging, _LOG_LEVEL))

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)


# from https://stackoverflow.com/questions/550653/cross-platform-way-to-get-pids-by-process-name-in-python/2241047
def find_procs_by_name(name):
    "Return a list of processes matching 'name'."
    assert name, name
    ls = []
    for p in psutil.process_iter():
        name_, exe, cmdline = "", "", []
        try:
            # name_ = p.name()
            cmdline = p.cmdline()
            exe = p.exe()
        except (psutil.AccessDenied, psutil.ZombieProcess):
            pass
        except psutil.NoSuchProcess:
            continue
        if name in ' '.join(cmdline) or name in os.path.basename(exe):
            ls.append(p)
    return ls


def new_chrome_driver(driver_path, headless: bool = True):
    """Creates a new chrome driver."""
    options = webdriver.ChromeOptions()
    if headless: options.add_argument('headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--useAutomationExtension=false")
    return webdriver.Chrome(driver_path, options=options)


def authenticate_gateway(driver, account, password, key: str = None, base_url: str = None) -> bool:
    """
    Authenticates the currently running gateway.

    If both password and key are provided, cryptography.fernet decryption will be used.

    :return: Whether authentication was successful.
    """
    if base_url is None: base_url = _GATEWAY_BASE_URL
    display = None
    try:
        if sys.platform == 'linux':
            display = Display(visible=0, size=(800, 600))
            display.start()

        _LOGGER.debug(f'Loading auth page at {base_url + _ROUTE_AUTH}')
        try:
            driver.get(base_url + _ROUTE_AUTH)
        except WebDriverException as e:
            if 'net::ERR_CONNECTION_REFUSED' in e.msg:
                _LOGGER.error(
                    'Connection to Gateway refused. This could indicate IB Gateway is not running. Consider increasing IBEAM_GATEWAY_STARTUP wait buffer')
                return False
            if 'net::ERR_CONNECTION_CLOSED' in e.msg:
                _LOGGER.error(
                    f'Connection to Gateway failed. This could indicate IB Gateway is not running correctly or that its port {base_url.split(":")[2]} was already occupied')
                return False
            else:
                raise e

        user_name_present = EC.presence_of_element_located((By.ID, _USER_NAME_EL_ID))
        WebDriverWait(driver, 15).until(user_name_present)

        _LOGGER.debug('Gateway auth page loaded')

        user_name_el = driver.find_element_by_id(_USER_NAME_EL_ID)
        password_el = driver.find_element_by_id(_PASSWORD_EL_ID)
        user_name_el.send_keys(account)

        if key is None:
            password_el.send_keys(password)
        else:
            password_el.send_keys(Fernet(key).decrypt(password.encode('utf-8')).decode("utf-8"))

        _LOGGER.debug('Submitting the form')
        submit_form_el = driver.find_element_by_id(_SUBMIT_EL_ID)
        submit_form_el.click()

        success_present = EC.text_to_be_present_in_element((By.TAG_NAME, 'pre'), _SUCCESS_EL_TEXT)
        WebDriverWait(driver, 15).until(success_present)
        _LOGGER.debug('Client login succeeds')
        time.sleep(2)
        driver.quit()
        success = True
    except Exception as e:
        try:
            raise RuntimeError('Error encountered during authentication') from e
        except Exception as full_e:
            _LOGGER.exception(full_e)
            success = False
    finally:
        if sys.platform == 'linux' and display is not None:
            display.stop()

    return success


class GatewayClient():

    def __init__(self,
                 account: str = None,
                 password: str = None,
                 key: str = None,
                 gateway_path: str = None,
                 driver_path: str = None,
                 base_url: str = None):

        self.base_url = base_url if base_url is not None else _GATEWAY_BASE_URL

        self.account = account if account is not None else os.environ.get('IBEAM_ACCOUNT')
        """IBKR account name."""

        self.password = password if password is not None else os.environ.get('IBEAM_PASSWORD')
        """IBKR password."""

        self.key = key if key is not None else os.environ.get('IBEAM_KEY')
        """Key to the IBKR password."""

        self.gateway_dir = gateway_path if gateway_path is not None else os.environ.get('IBEAM_GATEWAY_DIR')
        """Path to the root of the IBKR Gateway."""

        self.driver_path = driver_path if driver_path is not None else os.environ.get('IBEAM_CHROME_DRIVER_PATH')
        """Path to the Chrome Driver executable file."""

        if self.account is None:
            self.account = input('Account: ')

        if self.password is None:
            self.password = getpass('Password: ')
            if self.key is None:
                self.key = getpass('Key: ') or None

        if self.gateway_dir is None:
            self.gateway_dir = input('Gateway root path: ')

        if self.driver_path is None:
            self.driver_path = input('Chrome Driver executable path: ')

        self.inputs_dir = os.environ.get('IBEAM_INPUTS_DIR', '/srv/inputs/')

        self.config_path = os.path.join(self.gateway_dir, 'root/conf.yaml')
        config_source = os.path.join(self.inputs_dir, 'conf.yaml')
        if os.path.isfile(config_source):
            shutil.copy2(config_source, self.config_path)

        self.cecert_jks_path = os.path.join(self.inputs_dir, 'cacert.jks')
        self.cecert_pem_path = os.path.join(self.inputs_dir, 'cacert.pem')

        self._ssl_context = ssl.SSLContext()
        self.do_tls = os.path.isfile(self.cecert_jks_path) and os.path.isfile(self.cecert_pem_path)
        if self.do_tls:
            _LOGGER.debug('Certificates found and will be used for TLS verification')
            shutil.copy2(self.cecert_jks_path,
                         os.path.join(self.gateway_dir, 'root', os.path.basename(self.cecert_jks_path)))

            self._ssl_context.verify_mode = ssl.CERT_REQUIRED
            self._ssl_context.check_hostname = True
            self._ssl_context.load_verify_locations(self.cecert_pem_path)

        self._threads = 4

    def _start(self):
        creationflags = 0  # when not on Windows, we send 0 to avoid errors.

        if sys.platform == 'win32':
            args = ["cmd", "/k", r"bin\run.bat", r"root\conf.yaml"]
            _LOGGER.debug(f'Starting Windows process with params: {args}')
            creationflags = subprocess.CREATE_NEW_CONSOLE

        elif sys.platform == 'darwin':
            args = ["open", "-F", "-a", "Terminal", r"bin/run.sh", r"root/conf.yaml"]
            _LOGGER.debug(f'Starting Mac process with params: {args}')

        elif sys.platform == 'linux':
            args = ["bash", r"bin/run.sh", r"root/conf.yaml"]
            _LOGGER.debug(f'Starting Linux process with params: {args}')

        else:
            raise EnvironmentError(f'Unknown platform: {sys.platform}')

        subprocess.Popen(
            args=args,
            cwd=self.gateway_dir,
            creationflags=creationflags
        )

    def try_starting(self) -> Optional[int]:
        processes = find_procs_by_name(_GATEWAY_PROCESS_MATCH)
        if not processes:
            _LOGGER.info('Gateway not found, starting new one...')

            self._start()

            time.sleep(_GATEWAY_STARTUP)

            processes = find_procs_by_name(_GATEWAY_PROCESS_MATCH)
            success = len(processes) != 0
            if not success:
                return None

            self.server_process = processes[0].pid
            _LOGGER.info(f'Gateway started with pid: {self.server_process}')

        return processes[0].pid

    def _authenticate(self) -> bool:
        driver = new_chrome_driver(self.driver_path)
        return authenticate_gateway(driver, self.account, self.password, self.key, self.base_url)

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

    def _url_request(self, url):
        _LOGGER.debug(f'HTTPS{"" if self.do_tls else " (unverified)"} request to: {url}')
        return urllib.request.urlopen(url, context=self._ssl_context, timeout=_REQUEST_TIMEOUT)

    def _try_request(self, url, check_auth=False, max_attempts=1) -> (bool, bool, bool):
        """Attempts a HTTP request and returns a tuple of three boolean flag indicating whether the gateway can be reached, whether there is an active session and whether it is authenticated. Attempts to repeat the request up to max_attempts times.

        status[0] -> gateway running
        status[1] -> active session present
        status[2] -> session authenticated (equivalent to 'all good')
        """

        def _request(attempt=0) -> (bool, bool, bool):
            status = [False, False, False]
            try:
                response = self._url_request(url)
                if check_auth:
                    data = json.loads(response.read().decode('utf8'))
                    return True, True, data['iserver']['authStatus']['authenticated']
                else:
                    return True, True, True
            except HTTPError as e:
                if e.code == 401:
                    return True, False, False  # we expect this error, no need to log
                else:  # todo: possibly other codes could appear when not authenticated, fix when necessary
                    _LOGGER.exception(e)
                    return True, False, False
            except (URLError, socket.timeout) as e:
                reason = str(e)

                """
                    No connection... - happens when port isn't open
                    Cannot assign... - happens when calling a port taken by Docker but not served, when called from within the container.
                    Errno 0... - happens when calling a port taken by Docker but not served, when called from the host machine.
                """

                if 'No connection could be made because the target machine actively refused it' in reason \
                        or 'Cannot assign requested address' in reason \
                        or '[Errno 0] Error' in reason:
                    status = [False, False, False]
                    pass  # we expect these errors and don't need to log them

                elif "timed out" in reason \
                        or "The read operation timed out" in reason:
                    _LOGGER.error(
                        f'Connection timeout after {_REQUEST_TIMEOUT} seconds. Consider increasing timeout by setting IBEAM_REQUEST_TIMEOUT environment variable. Error: {reason}')
                    status = [True, False, False]
                else:
                    _LOGGER.exception(e)
                    status = [True, False, False]

            if max_attempts <= 1:
                return status
            else:
                if attempt >= max_attempts - 1:
                    _LOGGER.debug(
                        f'Max validate request retries reached after {max_attempts} attempts. Consider increasing the retries by setting IBEAM_REQUEST_RETRIES environment variable')
                    return status
                else:
                    _LOGGER.debug(f'Attempt number {attempt + 2}')
                    return _request(attempt + 1)

        return _request(0)

    def get_status(self, max_attempts=1) -> (bool, bool, bool):
        return self._try_request(self.base_url + _ROUTE_TICKLE, True, max_attempts=max_attempts)

    def validate(self) -> bool:
        return self._try_request(self.base_url + _ROUTE_VALIDATE, False)[1]

    def tickle(self) -> bool:
        return self._try_request(self.base_url + _ROUTE_TICKLE, True)[0]

    def user(self):
        try:
            response = self._url_request(self.base_url + _ROUTE_USER)
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
        self._scheduler.add_job(self._maintenance, trigger=IntervalTrigger(seconds=_MAINTENANCE_INTERVAL))
        _LOGGER.info(f'Starting maintenance with interval {_MAINTENANCE_INTERVAL} seconds')
        self._scheduler.start()

    def _maintenance(self):
        _LOGGER.debug('Maintenance')

        success = self.start_and_authenticate(request_retries=_REQUEST_RETRIES)

        if success:
            _LOGGER.info('Gateway running and authenticated')

    def kill(self) -> bool:
        processes = find_procs_by_name(_GATEWAY_PROCESS_MATCH)
        if processes:
            processes[0].terminate()

            time.sleep(1)

            # double check we succeeded
            processes = find_procs_by_name(_GATEWAY_PROCESS_MATCH)
            if processes:
                return False

        return True
