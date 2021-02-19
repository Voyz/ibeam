import logging
import re
import sys
import time
import urllib.parse
from pathlib import Path
import tempfile
from typing import Union

from cryptography.fernet import Fernet
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.common.exceptions import WebDriverException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from ibeam.src import var
from ibeam.src.two_fa_handlers.two_fa_handler import TwoFaHandler

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)

driver_index = 0


def new_chrome_driver(driver_path, headless: bool = True):
    global driver_index
    """Creates a new chrome driver."""
    options = webdriver.ChromeOptions()
    if headless: options.add_argument('headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument(f"--remote-debugging-port={9222 + driver_index}")
    options.add_argument("--useAutomationExtension=false")
    options.add_argument(f'--user-data-dir={tempfile.gettempdir()}/ibeam-chrome-{driver_index}')
    driver_index += 1
    return webdriver.Chrome(driver_path, options=options)


class AnyEc:
    """ Use with WebDriverWait to combine expected_conditions
        in an OR.
    """

    def __init__(self, *args):
        self.ecs = args

    def __call__(self, driver):
        for fn in self.ecs:
            try:
                if fn(driver): return True
            except:
                pass


class text_to_be_present_in_element(object):
    """ An expectation for checking if the given text is present in the
    specified element.
    locator, text
    """

    def __init__(self, locator, text_):
        self.locator = locator
        self.text = text_

    def __call__(self, driver):
        try:
            element = EC._find_element(driver, self.locator)
            if self.text in element.text:
                return element
            else:
                return False
        except StaleElementReferenceException:
            return False


def any_of(*expected_conditions):
    """ An expectation that any of multiple expected conditions is true.
    Equivalent to a logical 'OR'.
    Returns results of the first matching condition, or False if none do. """

    def any_of_condition(driver):
        for expected_condition in expected_conditions:
            try:
                result = expected_condition(driver)
                if result:
                    return result
            except WebDriverException:
                pass
        return False

    return any_of_condition


def authenticate_gateway(driver_path,
                         account,
                         password,
                         key: str = None,
                         base_url: str = None,
                         two_fa_handler: TwoFaHandler = None) -> bool:
    """
    Authenticates the currently running gateway.

    If both password and key are provided, cryptography.fernet decryption will be used.

    :return: Whether authentication was successful.
    """
    base_url = base_url if base_url is not None else var.GATEWAY_BASE_URL
    display = None
    success = False
    driver = None
    try:
        _LOGGER.debug(f'Loading auth webpage at {base_url + var.ROUTE_AUTH}')
        if sys.platform == 'linux':
            display = Display(visible=0, size=(800, 600))
            display.start()

        driver = start_driver(base_url, driver_path)
        if driver is None:
            return False

        # wait for the page to load
        user_name_present = EC.presence_of_element_located((By.ID, var.USER_NAME_EL_ID))
        WebDriverWait(driver, 15).until(user_name_present)
        _LOGGER.debug('Gateway auth webpage loaded')

        # input credentials
        user_name_el = driver.find_element_by_id(var.USER_NAME_EL_ID)
        password_el = driver.find_element_by_id(var.PASSWORD_EL_ID)
        user_name_el.send_keys(account)

        if key is None:
            password_el.send_keys(password)
        else:
            password_el.send_keys(Fernet(key).decrypt(password.encode('utf-8')).decode("utf-8"))

        # submit the form
        _LOGGER.debug('Submitting the form')
        submit_form_el = driver.find_element_by_id(var.SUBMIT_EL_ID)
        submit_form_el.click()

        # observe results - either success or 2FA request
        success_present = text_to_be_present_in_element((By.TAG_NAME, 'pre'), var.SUCCESS_EL_TEXT)
        two_factor_input_present = EC.visibility_of_element_located((By.ID, var.TWO_FA_EL_ID))
        error_displayed = EC.visibility_of_element_located((By.ID, var.ERROR_EL_ID))

        trigger = WebDriverWait(driver, var.OAUTH_TIMEOUT).until(
            any_of(success_present, two_factor_input_present, error_displayed))

        trigger_id = trigger.get_attribute('id')

        # handle 2FA
        if trigger_id == var.TWO_FA_EL_ID:
            _LOGGER.info(f'Credentials correct, but Gateway requires two-factor authentication.')
            two_fa_code = handle_two_fa(two_fa_handler, driver_path)

            if two_fa_code is not None:
                two_fa_el = driver.find_elements_by_id(var.TWO_FA_INPUT_EL_ID)
                two_fa_el[0].send_keys(two_fa_code)
                submit_form_el = driver.find_element_by_id(var.SUBMIT_EL_ID)
                submit_form_el.click()

            trigger = WebDriverWait(driver, var.OAUTH_TIMEOUT).until(any_of(success_present, error_displayed))
            trigger_id = trigger.get_attribute('id')

        if trigger_id == var.ERROR_EL_ID:
            _LOGGER.error(f'Error displayed by the login webpage: {trigger.text}')
        else:
            _LOGGER.debug('Webpage displayed "Client login succeeds"')
            success = True

        time.sleep(2)
    except Exception as e:
        try:
            raise RuntimeError('Error encountered during authentication') from e
        except Exception as full_e:
            _LOGGER.exception(full_e)
            success = False
    finally:
        if sys.platform == 'linux' and display is not None:
            display.stop()

        if driver is not None:
            driver.quit()
            global driver_index
            driver_index = max(driver_index - 1, 0)

    return success


def start_driver(base_url, driver_path) -> Union[webdriver.Chrome, None]:
    try:
        driver = new_chrome_driver(driver_path)
        driver.get(base_url + var.ROUTE_AUTH)
    except WebDriverException as e:
        if 'net::ERR_CONNECTION_REFUSED' in e.msg:
            _LOGGER.error(
                'Connection to Gateway refused. This could indicate IB Gateway is not running. Consider increasing IBEAM_GATEWAY_STARTUP wait buffer')
            return None
        if 'net::ERR_CONNECTION_CLOSED' in e.msg:
            _LOGGER.error(
                f'Connection to Gateway failed. This could indicate IB Gateway is not running correctly or that its port {base_url.split(":")[2]} was already occupied')
            return None
        else:
            raise e

    return driver


def handle_two_fa(two_fa_handler, driver_path) -> Union[str, None]:
    if two_fa_handler is None:
        _LOGGER.info(
            f'Not 2FA handler found. You may define your own 2FA handler or use built-in handlers. See documentation for more.')
        return None
    else:
        _LOGGER.info(f'Attempting to acquire 2FA code from: {two_fa_handler}')

        try:
            two_fa_code = two_fa_handler.get_two_fa_code()
        except Exception as two_fa_exception:
            try:
                raise RuntimeError('Error encountered while acquiring 2FA code.') from two_fa_exception
            except Exception as full_e:
                _LOGGER.exception(full_e)
                return None
        else:
            if two_fa_code is None:
                _LOGGER.info(f'No 2FA code returned.')
                return None
            else:
                _LOGGER.debug(f'2FA code returned: {two_fa_code}')
                return two_fa_code
