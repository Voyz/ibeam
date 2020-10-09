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

from _queue import Empty
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
_BASE_URL = os.environ.get('IB_PROXY_URL', "https://localhost:5000")
_ROUTE_VALIDATE = os.environ.get('IB_VALIDATE_ROUTE', '/v1/portal/sso/validate')
_ROUTE_TICKLE = os.environ.get('IB_TICKLE_ROUTE', '/v1/api/tickle')
_USER_NAME_EL_ID = os.environ.get('USER_NAME_EL_ID', 'user_name')
_PASSWORD_EL_ID = os.environ.get('PASSWORD_EL_ID', 'password')
_SUBMIT_EL_ID = os.environ.get('SUBMIT_EL_ID', 'submitForm')
_SUCCESS_EL_TEXT = os.environ.get('SUCCESS_EL_TEXT', 'Client login succeeds')


_LOGGER = logging.getLogger('ibeam.'+Path(__file__).stem)


def new_chrome_driver(driver_path, headless:bool=True):
    options = webdriver.ChromeOptions()
    if headless: options.add_argument('headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--useAutomationExtension=false")
    return webdriver.Chrome(driver_path, options=options)


def authenticate_gateway(driver, account, password, key:str=None, base_url:str=None):
    if base_url is None: base_url = _BASE_URL
    display = None
    try:
        if sys.platform == 'linux':
            display = Display(visible=0, size=(800, 600))
            display.start()

        try:
            driver.get(base_url+'/sso/Login?forwardTo=22&RL=1&ip2loc=on')
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
                    base_url:str=None):

        self.base_url = base_url if base_url is not None else _BASE_URL

        self.account = account if account is not None else os.environ.get('IB_ACCOUNT')
        self.password = password if password is not None else os.environ.get('IB_PASSWORD')
        self.key = key if key is not None else os.environ.get('IB_KEY')
        self.gateway_path = gateway_path if gateway_path is not None else os.environ.get('IB_CLIENTPORTAL_GW')
        self.driver_path = driver_path if driver_path is not None else os.environ.get('CHROME_DRIVER_PATH')

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

            creationflags = None

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
                raise OSError(f'Unknown platform: {sys.platform}')

            self.server_process = subprocess.Popen(
                args=args,
                cwd=self.gateway_path,
                creationflags=creationflags,
                stdout=subprocess.PIPE,
            )

            # while True:
            #     line = self.server_process.stdout.readline()
            #     print(line)
            #     print(self.server_process.stderr.readline())
            #     if line and 'App demo is available after you login under' in line:
            #         break
            #     time.sleep(0.5)

            # self.server_process, q = run_subprocess(args=args, cwd=self.gateway_path)
            #
            # while True:
            #     try:
            #         line = q.get_nowait()  # or q.get(timeout=.1)
            #     except Empty:
            #         print('no output yet')
            #         time.sleep(1)
            #     else:  # got line
            #         print(line)
            #         if line and b'App demo is available after you login under' in line:
            #             break

            _LOGGER.debug(f'Gateway started with process id: {self.server_process.pid}')

            return self.server_process.pid
        else:
            _LOGGER.debug('Gateway is already running.')
            return None

    def authenticate(self):
        driver = new_chrome_driver(self.driver_path)
        return authenticate_gateway(driver, self.account, self.password, self.key, self.base_url)

    def _url_request(self, url):
        return urllib.request.urlopen(url, context=self._empty_context)

    def verify(self):
        try:
            self._url_request(self.base_url+_ROUTE_VALIDATE)
            return True
        except HTTPError as e:
            if e.code == 401:
                return False
            else: # todo: possibly other codes could appear when not authenticated
                return True
        except URLError as e:
            if 'No connection could be made because the target machine actively refused it' in str(e.reason):
                return False
            else:
                _LOGGER.exception(e)

    def tickle(self):
        try:
            self._url_request(self.base_url+_ROUTE_TICKLE)
            return True
        except HTTPError:
            return True
        except URLError as e:
            if 'No connection could be made because the target machine actively refused it' in str(e.reason):
                return False
            else:
                _LOGGER.exception(e)
        except Exception as e:
            _LOGGER.exception(e)

    def start_and_authenticate(self):
        self.start()

        if not self.verify():
            _LOGGER.info('Authenticating.')
            time.sleep(_GATEWAY_STARTUP_SECONDS)

            success = self.authenticate()
            _LOGGER.info(f'Authentication {"succeeded" if success else "failed"}')
            if not success:
                return False

        if self.verify():
            _LOGGER.info('Gateway running and authenticated.')
            return True
        else:
            if self.tickle():
                _LOGGER.error('Gateway running but not authenticated.')
            else:
                _LOGGER.error('Gateway not running and not authenticated.')
            return False

