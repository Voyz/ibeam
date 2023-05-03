import logging
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
import tempfile
from typing import Union, Optional

from cryptography.fernet import Fernet
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.common.exceptions import WebDriverException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.ui import Select

import ibeam
from ibeam.src import var
from ibeam.src.two_fa_handlers.two_fa_handler import TwoFaHandler

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)

_DRIVER_NAMES = {}
_FAILED_ATTEMPTS = 0


def new_chrome_driver(driver_path, name: str = 'default', headless: bool = True):
    """Creates a new chrome driver."""

    global _DRIVER_NAMES

    _DRIVER_NAMES[name] = True  # just to ensure the name is in the dict
    driver_index = list(_DRIVER_NAMES.keys()).index(name)  # order of insertion dictates the driver_index

    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument(f'--remote-debugging-port={9222 + driver_index}')
    options.add_argument('--useAutomationExtension=false')
    options.add_argument('--disable-extensions')
    options.add_argument('--dns-prefetch-disable')
    options.add_argument(f'--user-data-dir={tempfile.gettempdir()}/ibeam-chrome-{name}')
    driver = webdriver.Chrome(driver_path, options=options)
    if driver is None:
        _LOGGER.error('Unable to create a new chrome driver.')

    return driver


def release_chrome_driver(driver):
    driver.quit()


class text_to_be_present_in_element(object):
    """ An expectation for checking if the given text is present in the
    specified element.
    locator, text
    """

    def __init__(self, locators, text_):
        if not isinstance(locators, list):
            locators = locators
        self.locators = locators
        self.text = text_

    def __call__(self, driver):
        for locator in self.locators:
            try:
                element = EC._find_element(driver, locator)
                if self.text in element.text:
                    return element
            except StaleElementReferenceException:
                continue
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


def save_screenshot(driver, postfix=''):
    if not var.ERROR_SCREENSHOTS or driver is None:
        return

    now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    outputs_path = Path(var.OUTPUTS_DIR)
    screenshot_name = f'ibeam__{ibeam.__version__}__{now}{postfix}.png'

    try:
        required_width = driver.execute_script('return document.body.parentNode.scrollWidth')
        required_height = driver.execute_script('return document.body.parentNode.scrollHeight')
        driver.set_window_size(required_width, required_height)

        outputs_path.mkdir(exist_ok=True)
        screenshot_filepath = os.path.join(var.OUTPUTS_DIR, screenshot_name)

        # a little hack to prevent overwriting screenshots saved in the same second
        if os.path.exists(screenshot_filepath):
            save_screenshot(driver, postfix + '_')
            return

        _LOGGER.debug(
            f'Saving screenshot to {screenshot_filepath}. Make sure to cover your credentials if you share it with others.')
        driver.get_screenshot_as_file(screenshot_filepath)
    except Exception as e:
        _LOGGER.exception(f"Exception while saving screenshot: {str(e)} for screenshot: {screenshot_name}")


def identify_trigger(trigger) -> Optional[str]:
    if trigger.get_attribute('id') == var.TWO_FA_EL_ID:
        return var.TWO_FA_EL_ID

    if trigger.get_attribute('id') == var.TWO_FA_SELECT_EL_ID:
        return var.TWO_FA_SELECT_EL_ID

    if var.ERROR_EL in trigger.get_attribute('class'):
        return var.ERROR_EL

    if var.TWO_FA_NOTIFICATION_EL in trigger.get_attribute('class'):
        return var.TWO_FA_NOTIFICATION_EL

    if trigger.text == var.SUCCESS_EL_TEXT:
        return var.SUCCESS_EL_TEXT

    raise RuntimeError(f'Trigger found but cannot be identified: {trigger}')


def authenticate_gateway(driver_path,
                         account,
                         password,
                         key: str = None,
                         base_url: str = None,
                         two_fa_handler: TwoFaHandler = None) -> (bool, bool):
    """
    Authenticates the currently running gateway.

    If both password and key are provided, cryptography.fernet decryption will be used.

    First boolean - whether authentication was successful
    Second boolean - whether max failed attempts was reached and IBeam should shut down

    :return: Whether authentication was successful and whether IBeam should shut down
    :rtype: (bool, bool)
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
            return False, False

        driver.get(base_url + var.ROUTE_AUTH)

        # wait for the page to load
        user_name_present = EC.presence_of_element_located((By.NAME, var.USER_NAME_EL))
        WebDriverWait(driver, 15).until(user_name_present)
        _LOGGER.debug('Gateway auth webpage loaded')

        immediate_attempts = 0

        while immediate_attempts < max(var.MAX_IMMEDIATE_ATTEMPTS, 1):
            immediate_attempts += 1
            _LOGGER.debug(f'Login attempt number {immediate_attempts}')

            # time.sleep(300)

            # input credentials
            user_name_el = driver.find_element_by_name(var.USER_NAME_EL)
            password_el = driver.find_element_by_name(var.PASSWORD_EL)
            user_name_el.send_keys(account)

            if key is None:
                password_el.send_keys(password)
            else:
                password_el.send_keys(Fernet(key).decrypt(password.encode('utf-8')).decode("utf-8"))

            password_el.send_keys(Keys.TAB)

            # small buffer to prevent race-condition on client side
            time.sleep(5)
            # submit the form
            _LOGGER.debug('Submitting the form')
            submit_form_el = driver.find_element_by_css_selector(var.SUBMIT_EL)
            submit_form_el.click()

            # observe results - either success or 2FA request
            success_present = text_to_be_present_in_element([(By.TAG_NAME, 'pre'), (By.TAG_NAME, 'body')],
                                                            var.SUCCESS_EL_TEXT)
            two_factor_input_present = EC.visibility_of_element_located((By.ID, var.TWO_FA_EL_ID))

            two_factor_select_present = EC.visibility_of_element_located((By.ID, var.TWO_FA_SELECT_EL_ID))

            two_factor_notification = EC.visibility_of_element_located((By.CLASS_NAME, var.TWO_FA_NOTIFICATION_EL))

            error_displayed = EC.visibility_of_element_located((By.CSS_SELECTOR, '.' + var.ERROR_EL.replace(' ', '.')))
            ibkey_promo_skip_clickable = EC.element_to_be_clickable((By.CLASS_NAME, var.IBKEY_PROMO_EL_CLASS))

            trigger = WebDriverWait(driver, var.OAUTH_TIMEOUT).until(
                any_of(success_present,
                       two_factor_input_present,
                       two_factor_select_present,
                       two_factor_notification,
                       error_displayed,
                       ibkey_promo_skip_clickable))

            trigger_identifier = identify_trigger(trigger)
            _LOGGER.debug(f'trigger: {trigger_identifier}')

            if trigger_identifier == var.TWO_FA_SELECT_EL_ID:
                _LOGGER.info(f'Required to select a 2FA method.')
                select_el = driver.find_element_by_id(var.TWO_FA_SELECT_EL_ID)
                select = Select(select_el)
                select.select_by_visible_text(var.TWO_FA_SELECT_TARGET)

                trigger = WebDriverWait(driver, var.OAUTH_TIMEOUT).until(
                    any_of(success_present,
                           two_factor_input_present,
                           two_factor_notification,
                           error_displayed,
                           ibkey_promo_skip_clickable))

                _LOGGER.info(f'2FA method "{var.TWO_FA_SELECT_TARGET}" selected successfully.')

                trigger_identifier = identify_trigger(trigger)
                _LOGGER.debug(f'trigger: {trigger_identifier}')

            if trigger_identifier == var.TWO_FA_NOTIFICATION_EL:
                _LOGGER.info(f'Credentials correct, but Gateway requires notification two-factor authentication.')

                if two_fa_handler is not None:
                    two_fa_success = two_fa_handler.get_two_fa_code(driver)
                    if not two_fa_success:
                        driver.refresh()
                        continue  # attempt a direct retry

                trigger = WebDriverWait(driver, var.OAUTH_TIMEOUT).until(
                    any_of(success_present, ibkey_promo_skip_clickable, error_displayed))
                trigger_identifier = identify_trigger(trigger)

            # handle 2FA
            if trigger_identifier == var.TWO_FA_EL_ID:
                _LOGGER.info(f'Credentials correct, but Gateway requires two-factor authentication.')
                if two_fa_handler is None:
                    _LOGGER.critical(
                        f'######## ATTENTION! ######## No 2FA handler found. You may define your own 2FA handler or use built-in handlers. See documentation for more: https://github.com/Voyz/ibeam/wiki/Two-Factor-Authentication')
                    return False, True

                two_fa_code = handle_two_fa(two_fa_handler)

                if two_fa_code is None:
                    _LOGGER.warning(f'No 2FA code returned. Aborting authentication.')
                else:
                    two_fa_el = driver.find_elements_by_id(var.TWO_FA_INPUT_EL_ID)
                    WebDriverWait(driver, var.OAUTH_TIMEOUT).until(
                        EC.element_to_be_clickable((By.ID, var.TWO_FA_INPUT_EL_ID)))
                    two_fa_el[0].send_keys(two_fa_code)

                    _LOGGER.debug('Submitting the 2FA form')
                    submit_form_el = driver.find_element_by_css_selector(var.SUBMIT_EL)
                    WebDriverWait(driver, var.OAUTH_TIMEOUT).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, var.SUBMIT_EL)))
                    submit_form_el.click()

                    trigger = WebDriverWait(driver, var.OAUTH_TIMEOUT).until(
                        any_of(success_present, ibkey_promo_skip_clickable, error_displayed))
                    trigger_identifier = identify_trigger(trigger)

            trigger_class = trigger.get_attribute('class')

            if var.IBKEY_PROMO_EL_CLASS in trigger_class:
                _LOGGER.debug('Handling IB-Key promo display...')
                trigger.click()
                WebDriverWait(driver, 10).until(success_present)
                trigger_identifier = identify_trigger(trigger)

            if trigger_identifier == var.ERROR_EL:
                _LOGGER.error(f'Error displayed by the login webpage: {trigger.text}')
                save_screenshot(driver, '__failed_attempt')

                # try to prevent having the account locked-out
                if trigger.text == 'failed' or trigger.text == 'Invalid username password combination' and var.MAX_FAILED_AUTH > 0:
                    global _FAILED_ATTEMPTS
                    _FAILED_ATTEMPTS += 1
                    if _FAILED_ATTEMPTS >= var.MAX_FAILED_AUTH:
                        _LOGGER.critical(
                            f'######## ATTENTION! ######## Maximum number of failed authentication attempts (IBEAM_MAX_FAILED_AUTH={var.MAX_FAILED_AUTH}) reached. IBeam will shut down to prevent an account lock-out. It is recommended you attempt to authenticate manually in order to reset the counter. Read the execution logs and report issues at https://github.com/Voyz/ibeam/issues')
                        return False, True

                time.sleep(1)
                continue  # attempt a direct retry

            elif trigger_identifier == var.TWO_FA_EL_ID:
                time.sleep(1)
                driver.refresh()
                continue  # attempt a direct retry
                pass  # this means no two_fa_code was returned and trigger remained the same - ie. don't authenticate
                # todo: retry authentication or resend code
            elif trigger_identifier == var.SUCCESS_EL_TEXT:
                _LOGGER.debug('Webpage displayed "Client login succeeds"')
                _FAILED_ATTEMPTS = 0
                success = True
                break

        time.sleep(2)
    except TimeoutException as e:
        exception_line = traceback.format_tb(sys.exc_info()[2])[0].replace('\n', '')
        _LOGGER.error(
            f'Timeout reached when waiting for authentication. Consider increasing IBEAM_PAGE_LOAD_TIMEOUT. Error: "{e.msg}" at {exception_line}')
        save_screenshot(driver, '__timeout-exception')
        success = False
    except Exception as e:
        try:
            raise RuntimeError('Error encountered during authentication') from e
        except Exception as full_e:
            _LOGGER.exception(full_e)
            save_screenshot(driver, '__generic-exception')
            success = False
    finally:
        # if sys.platform == 'linux' and display is not None:
        _LOGGER.debug(f'Cleaning up the resources. Display: {display} | Driver: {driver}')

        if display is not None:
            display.stop()

        if driver is not None:
            release_chrome_driver(driver)

    return success, False


def start_driver(base_url, driver_path) -> Union[webdriver.Chrome, None]:
    try:
        driver = new_chrome_driver(driver_path)
        driver.set_page_load_timeout(var.PAGE_LOAD_TIMEOUT)
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


def handle_two_fa(two_fa_handler) -> Union[str, None]:
    _LOGGER.info(f'Attempting to acquire 2FA code from: {two_fa_handler}')

    try:
        two_fa_code = two_fa_handler.get_two_fa_code()
        if two_fa_code is not None:
            two_fa_code = str(two_fa_code)  # in case someone returns an integer
    except Exception as two_fa_exception:
        try:
            raise RuntimeError('Error encountered while acquiring 2FA code.') from two_fa_exception
        except Exception as full_e:
            _LOGGER.exception(full_e)
            return None
    else:
        _LOGGER.debug(f'2FA code returned: {two_fa_code}')

        if var.STRICT_TWO_FA_CODE and two_fa_code is not None and (
                not two_fa_code.isdigit() or len(two_fa_code) != 6):
            _LOGGER.error(
                f'Illegal 2FA code returned: {two_fa_code}. Ensure the 2FA code contains 6 digits or disable this check by setting IBEAM_STRICT_TWO_FA_CODE to False.')
            return None

        return two_fa_code
