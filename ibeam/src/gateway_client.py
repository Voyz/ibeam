#!/opt/venv/bin python

import logging
import os
import ssl
import subprocess
import sys
import time
import urllib.request
from getpass import getpass

from pathlib import Path
from urllib.error import HTTPError, URLError

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

_GATEWAY_STARTUP_SECONDS = os.environ.get('GATEWAY_STARTUP_SECONDS', 3)
"""How many seconds to wait before attempting to communicate with the gateway after its startup."""

_GATEWAY_BASE_URL = os.environ.get('GATEWAY_BASE_URL', "https://localhost:5000")
"""Base URL of the gateway."""

_ROUTE_AUTH = os.environ.get('ROUTE_AUTH', '/sso/Login?forwardTo=22&RL=1&ip2loc=on')
"""Gateway route with authentication page."""

_ROUTE_USER = os.environ.get('ROUTE_USER', '/v1/api/one/user')
"""Gateway route with user information."""

_ROUTE_VALIDATE = os.environ.get('ROUTE_VALIDATE', '/v1/portal/sso/validate')
"""Gateway route with validation call."""

_ROUTE_TICKLE = os.environ.get('ROUTE_TICKLE', '/v1/api/tickle')
"""Gateway route with tickle call."""

_USER_NAME_EL_ID = os.environ.get('USER_NAME_EL_ID', 'user_name')
"""HTML element id containing the username input field."""

_PASSWORD_EL_ID = os.environ.get('PASSWORD_EL_ID', 'password')
"""HTML element id containing the password input field."""

_SUBMIT_EL_ID = os.environ.get('SUBMIT_EL_ID', 'submitForm')
"""HTML element id containing the submit button."""

_SUCCESS_EL_TEXT = os.environ.get('SUCCESS_EL_TEXT', 'Client login succeeds')
"""HTML element text indicating successful authentication."""

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)


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


def authenticate_gateway(driver, account, password, key: str = None, base_url: str = None):
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

        try:
            driver.get(base_url + _ROUTE_AUTH)
        except WebDriverException as e:
            if 'net::ERR_CONNECTION_REFUSED' in e.msg:
                _LOGGER.error('Connection to Gateway refused. This could indicate IB Gateway is not running.')
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
            raise RuntimeError('Error encountered during authentication.') from e
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

        self.account = account if account is not None else os.environ.get('IB_ACCOUNT')
        """IBKR account name."""

        self.password = password if password is not None else os.environ.get('IB_PASSWORD')
        """IBKR password."""

        self.key = key if key is not None else os.environ.get('IB_KEY')
        """Key to the IBKR password."""

        self.gateway_path = gateway_path if gateway_path is not None else os.environ.get('GATEWAY_PATH')
        """Path to the root of the IBKR Gateway."""

        self.driver_path = driver_path if driver_path is not None else os.environ.get('CHROME_DRIVER_PATH')
        """Path to the Chrome Driver executable file."""

        if self.account is None:
            self.account = input('Account: ')

        if self.password is None:
            self.password = getpass('Password: ')
            if self.key is None:
                self.key = getpass('Key: ') or None

        self._empty_context = ssl.SSLContext()

    def start(self):
        if not self.tickle():
            _LOGGER.info('Gateway not found, starting new one.')

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

            self.server_process = subprocess.Popen(
                args=args,
                cwd=self.gateway_path,
                creationflags=creationflags
            )

            _LOGGER.debug(f'Gateway started with process id: {self.server_process.pid}')

            return self.server_process.pid
        else:
            _LOGGER.debug('Gateway is already running.')
            return None

    def authenticate(self):
        driver = new_chrome_driver(self.driver_path)
        return authenticate_gateway(driver, self.account, self.password, self.key, self.base_url)

    def _url_request(self, url):
        _LOGGER.debug(f'URL request to: {url}')
        # Empty context allows us to ignore certificates, given we're on the same network. This may be a bad idea.
        return urllib.request.urlopen(url, context=self._empty_context)

    def _try_request(self, url, only_tickle: bool = True):
        """Attempts a HTTP request and returns a boolean flag indicating whether it was successful."""
        try:
            self._url_request(url)
            return True
        except HTTPError as e:
            if e.code == 401 and not only_tickle:
                return False
            else:  # todo: possibly other codes could appear when not authenticated, fix when necessary
                return True
        except URLError as e:
            # print(e.reason)
            reason = str(e.reason)

            """
                No connection... - happens when port isn't open
                Cannot assign... - happens when calling a port taken by Docker but not served, when called from within the container.
                Errno 0... - happens when calling a port taken by Docker but not served, when called from the host machine.
            """

            if 'No connection could be made because the target machine actively refused it' in reason \
                    or 'Cannot assign requested address' in reason \
                    or '[Errno 0] Error' in reason:
                return False
            else:
                _LOGGER.exception(e)
        except Exception as e:
            _LOGGER.exception(e)

    def validate(self) -> bool:
        return self._try_request(self.base_url + _ROUTE_VALIDATE, False)

    def tickle(self) -> bool:
        return self._try_request(self.base_url + _ROUTE_TICKLE, True)

    def user(self):
        try:
            response = self._url_request(self.base_url + _ROUTE_USER)
            _LOGGER.info(response.read())
        except Exception as e:
            _LOGGER.exception(e)

    def start_and_authenticate(self):
        """Starts the gateway and authenticates using the credentials stored."""

        self.start()

        if not self.validate():
            _LOGGER.info('Authenticating.')
            time.sleep(_GATEWAY_STARTUP_SECONDS)

            success = self.authenticate()
            _LOGGER.info(f'Authentication {"succeeded" if success else "failed"}')
            if not success:
                return False

        if self.validate():
            _LOGGER.info('Gateway running and authenticated.')
            return True
        else:
            if self.tickle():
                _LOGGER.error('Gateway running but not authenticated.')
            else:
                _LOGGER.error('Gateway not running and not authenticated.')
            return False
