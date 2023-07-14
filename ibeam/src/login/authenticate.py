import logging
import time
from functools import partial
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium import webdriver

from ibeam.src import var
from ibeam.src.login.driver import save_screenshot, DriverFactory, start_up_browser, shut_down_browser
from ibeam.src.login.targets import Target, Targets, create_targets, identify_target
from ibeam.src.utils.py_utils import exception_to_string
from ibeam.src.two_fa_handlers.two_fa_handler import TwoFaHandler
from ibeam.src.utils.selenium_utils import text_to_be_present_in_element, any_of

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)

_FAILED_ATTEMPTS = 0
_PRESUBMIT_BUFFER = var.MIN_PRESUBMIT_BUFFER


_VERSIONS = {
    1: {
        'USER_NAME_EL': 'NAME@@user_name',
        'ERROR_EL': 'CSS_SELECTOR@@.alert.alert-danger.margin-top-10'
    },
    2: {
        'USER_NAME_EL': 'NAME@@username',
        'ERROR_EL': 'CSS_SELECTOR@@.xyz-errormessage'
    }
}


def is_present(target: Target) -> callable:
    return EC.presence_of_element_located((target.by, target.identifier))

def is_visible(target: Target) -> callable:
    return EC.visibility_of_element_located((target.by, target.identifier))

def is_clickable(target: Target) -> callable:
    return EC.element_to_be_clickable((target.by, target.identifier))

def has_text(target: Target) -> callable:
    return text_to_be_present_in_element(target.by, target.identifier)

def find_element(target: Target, driver:webdriver.Chrome) -> WebElement:
    return driver.find_element(target.by, target.identifier)


def check_version(driver) -> int:
    """ Check for the IBRK website version. Currently, there are various versions shown to users and we want to know which one we are operating on.

    Versions:

    * 1 = available until March 2023
    * 2 = available from March 2023
    """
    try:
        user_name_present = EC.presence_of_element_located((By.NAME, 'user_name'))
        WebDriverWait(driver, 5).until(user_name_present)
        return 1
    except TimeoutException as e:
        pass

    try:
        user_name_present = EC.presence_of_element_located((By.NAME, 'username'))
        WebDriverWait(driver, 5).until(user_name_present)
        return 2
    except TimeoutException as e:
        pass

    _LOGGER.warning(f'Cannot determine the version of IBKR website, assuming version 1')

    return 1


def _wait_and_identify_trigger(targets: Targets,
                               driver: webdriver.Chrome,
                               timeout: int,
                               *expected_conditions,
                               skip_identify: bool = False,
                               ) -> (WebElement, Target):
    trigger = WebDriverWait(driver, timeout).until(any_of(*expected_conditions))

    if skip_identify:
        return trigger, None

    target = identify_target(trigger, targets)
    _LOGGER.debug(f'target: {target}')

    return trigger, target


def step_login(targets: Targets,
               wait_and_identify_trigger: callable,
               driver:webdriver.Chrome,
               account: str,
               password: str,
               key: str,
               presubmit_buffer: int,
               ):

    # input credentials
    user_name_el = find_element(targets['USER_NAME'], driver)
    password_el = find_element(targets['PASSWORD'], driver)

    user_name_el.clear()
    password_el.clear()

    user_name_el.send_keys(account)

    if key is None:
        password_el.send_keys(password)
    else:
        password_el.send_keys(Fernet(key).decrypt(password.encode('utf-8')).decode("utf-8"))

    password_el.send_keys(Keys.TAB)

    # small buffer to prevent race-condition on client side
    time.sleep(presubmit_buffer)
    # submit the form
    _LOGGER.info('Submitting the form')

    submit_form_el = find_element(targets['SUBMIT'], driver)
    submit_form_el.click()

    trigger, target = wait_and_identify_trigger(
        has_text(targets['SUCCESS']),
        is_visible(targets['TWO_FA']),
        is_visible(targets['TWO_FA_SELECT']),
        is_visible(targets['TWO_FA_NOTIFICATION']),
        is_visible(targets['ERROR']),
        is_clickable(targets['IBKEY_PROMO']),
    )

    return trigger, target

def step_select_two_fa(targets: Targets,
                       wait_and_identify_trigger: callable,
                       driver:webdriver.Chrome,
                       two_fa_select_target: str,
                       ):
    _LOGGER.info(f'Required to select a 2FA method.')
    select_el = find_element(targets['TWO_FA_SELECT'], driver)
    select = Select(select_el)
    select.select_by_visible_text(two_fa_select_target)

    trigger, target = wait_and_identify_trigger(
        has_text(targets['SUCCESS']),
        is_visible(targets['TWO_FA']),
        is_visible(targets['TWO_FA_NOTIFICATION']),
        is_visible(targets['ERROR']),
        is_clickable(targets['IBKEY_PROMO'])
    )

    _LOGGER.info(f'2FA method "{two_fa_select_target}" selected successfully.')
    return trigger, target


def step_two_fa_notification(targets: Targets,
                             wait_and_identify_trigger: callable,
                             driver: webdriver.Chrome,
                             two_fa_handler: TwoFaHandler,
                             ):
    _LOGGER.info(f'Credentials correct, but Gateway requires notification two-factor authentication.')

    if two_fa_handler is not None:
        two_fa_success = two_fa_handler.get_two_fa_code(driver)
        if not two_fa_success:
            driver.refresh()
            raise ContinueException

    trigger, target = wait_and_identify_trigger(
        has_text(targets['SUCCESS']),
        is_clickable(targets['IBKEY_PROMO']),
        is_visible(targets['ERROR'])
    )
    return trigger, target

def step_two_fa(targets: Targets,
                wait_and_identify_trigger: callable,
                driver: webdriver.Chrome,
                two_fa_handler: TwoFaHandler,
                strict_two_fa_code: bool,
                ):
    _LOGGER.info(f'Credentials correct, but Gateway requires two-factor authentication.')
    if two_fa_handler is None:
        _LOGGER.critical(
            f'######## ATTENTION! ######## No 2FA handler found. You may define your own 2FA handler or use built-in handlers. See documentation for more: https://github.com/Voyz/ibeam/wiki/Two-Factor-Authentication')
        raise ShutdownException

    two_fa_code = handle_two_fa(two_fa_handler, driver, strict_two_fa_code)

    if two_fa_code is None:
        _LOGGER.warning(f'No 2FA code returned. Aborting authentication.')
    else:
        two_fa_el, _ = wait_and_identify_trigger(is_clickable(targets['TWO_FA_INPUT']), skip_identify=True)

        two_fa_el[0].clear()
        two_fa_el[0].send_keys(two_fa_code)

        _LOGGER.info('Submitting the 2FA form')
        two_fa_el[0].send_keys(Keys.RETURN)

        trigger, target = wait_and_identify_trigger(
            has_text(targets['SUCCESS']),
            is_clickable(targets['IBKEY_PROMO']),
            is_visible(targets['ERROR'])
        )

        return trigger, target

def step_handle_ib_key_promo(targets: Targets,
                             wait_and_identify_trigger: callable,
                             ib_promo_key_trigger: WebElement,
                             ):
    _LOGGER.info('Handling IB-Key promo display...')
    ib_promo_key_trigger.click()
    trigger, target = wait_and_identify_trigger(
        has_text(targets['SUCCESS']),
        is_visible(targets['ERROR'])
    )

    return trigger, target

def step_error(driver:webdriver.Chrome,
               error_trigger: WebElement,
               presubmit_buffer: int,
               max_presubmit_buffer: int,
               max_failed_auth: int,
               outputs_dir: str
               ):
    _LOGGER.error(f'Error displayed by the login webpage: {error_trigger.text}')
    save_screenshot(driver, outputs_dir, '__failed_attempt')
    if error_trigger.text == 'Invalid username password combination' and presubmit_buffer < max_presubmit_buffer:
        global _PRESUBMIT_BUFFER
        _PRESUBMIT_BUFFER += 5
        if _PRESUBMIT_BUFFER >= max_presubmit_buffer:
            _PRESUBMIT_BUFFER = max_presubmit_buffer
            _LOGGER.warning(f'The presubmit buffer set to maximum: {max_presubmit_buffer}')
        else:
            _LOGGER.warning(f'Increased presubmit buffer to {_PRESUBMIT_BUFFER}')

    # try to prevent having the account locked-out
    if error_trigger.text == 'failed' or error_trigger.text == 'Invalid username password combination' and max_failed_auth > 0:
        global _FAILED_ATTEMPTS
        _FAILED_ATTEMPTS += 1
        if _FAILED_ATTEMPTS >= max_failed_auth:
            _LOGGER.critical(
                f'######## ATTENTION! ######## Maximum number of failed authentication attempts (IBEAM_MAX_FAILED_AUTH={max_failed_auth}) reached. IBeam will shut down to prevent an account lock-out. It is recommended you attempt to authenticate manually in order to reset the counter. Read the execution logs and report issues at https://github.com/Voyz/ibeam/issues')
            raise ShutdownException

    time.sleep(1)
    raise ContinueException


def handle_timeout_exception(e:Exception,
                             targets: Targets,
                             driver:webdriver.Chrome,
                             website_version: int,
                             route_auth: str,
                             base_url: str,
                             outputs_dir: str):
    page_loaded_correctly = True
    try:
        website_loaded = EC.presence_of_element_located((By.CLASS_NAME, 'login'))
        WebDriverWait(driver, 5).until(website_loaded)
    except TimeoutException as _:
        page_loaded_correctly = False

    if not page_loaded_correctly or website_version == -1:
        _LOGGER.error(f'Timeout reached when waiting for authentication. The website seems to not be loaded correctly. Consider increasing IBEAM_PAGE_LOAD_TIMEOUT. \nWebsite URL: {base_url + route_auth} \n \nException:\n{exception_to_string(e)}')
    else:
        _LOGGER.error(f'Timeout reached searching for website elements, but the website seems to be loaded correctly. It is possible the setup is incorrect. \nWebsite version: {website_version} \nDOM elements searched for: {targets}. \nException:\n{exception_to_string(e)}')

    save_screenshot(driver, outputs_dir, '__timeout-exception')

def step_failed_two_fa(driver:webdriver.Chrome):
    # this means no two_fa_code was returned and trigger remained the same - ie. don't authenticate
    time.sleep(1)
    driver.refresh()
    raise ContinueException
    # todo: retry authentication or resend code

def step_success(min_presubmit_buffer:int):
    _LOGGER.info('Webpage displayed "Client login succeeds"')
    _FAILED_ATTEMPTS = 0
    _PRESUBMIT_BUFFER = min_presubmit_buffer
    raise SuccessException

def attempt(
        targets: Targets,
        wait_and_identify_trigger: callable,
        driver: webdriver.Chrome,
        account: str,
        password: str,
        key: str,
        presubmit_buffer: int,
        min_presubmit_buffer: int,
        max_presubmit_buffer: int,
        max_failed_auth: int,
        two_fa_handler: TwoFaHandler,
        two_fa_select_target: str,
        strict_two_fa_code: bool,
        outputs_dir: str,
):
    trigger, target = step_login(targets, wait_and_identify_trigger, driver, account, password, key, presubmit_buffer)

    if target == targets['TWO_FA_SELECT']:
        trigger, target = step_select_two_fa(targets, wait_and_identify_trigger, driver, two_fa_select_target)

    if target == targets['TWO_FA_NOTIFICATION']:
        trigger, target = step_two_fa_notification(targets, wait_and_identify_trigger, driver, two_fa_handler)

    if target == targets['TWO_FA']:
        trigger, target = step_two_fa(targets, wait_and_identify_trigger, driver, two_fa_handler, strict_two_fa_code)

    if target == targets['IBKEY_PROMO']:
        trigger, target = step_handle_ib_key_promo(targets, wait_and_identify_trigger, trigger)

    if target == targets['ERROR']:
        step_error(driver, trigger, presubmit_buffer, max_presubmit_buffer, max_failed_auth, outputs_dir)

    elif target == targets['TWO_FA']:
        step_failed_two_fa(driver)

    elif target == targets['SUCCESS']:
        step_success(min_presubmit_buffer)


class BreakException(Exception):
    pass
class ContinueException(Exception):
    pass
class ShutdownException(Exception):
    pass
class SuccessException(Exception):
    pass
def log_in(
           driver_factory:DriverFactory,
           account,
           password,
           key: str = None,
           base_url: str = None,
           two_fa_handler: TwoFaHandler = None,
           route_auth: str = None,
           two_fa_select_target: str = None,
           strict_two_fa_code: bool = None,
           max_immediate_attempts: int = None,
           oauth_timeout: int = None,
           max_presubmit_buffer: int = None,
           min_presubmit_buffer: int = None,
           max_failed_auth: int = None,
           outputs_dir: str = None,
           ) -> (bool, bool):
    """
    Logs into the currently running gateway.

    If both password and key are provided, cryptography.fernet decryption will be used.

    First boolean - whether authentication was successful
    Second boolean - whether max failed attempts was reached and IBeam should shut down

    :return: Whether authentication was successful and whether IBeam should shut down
    :rtype: (bool, bool)
    """
    display = None
    success = False
    driver = None
    website_version = -1
    targets = {}

    global _PRESUBMIT_BUFFER
    presubmit_buffer = _PRESUBMIT_BUFFER

    try:
        _LOGGER.info(f'Loading auth webpage at {base_url + route_auth}')
        driver, display = start_up_browser(driver_factory, base_url, route_auth)

        website_version = check_version(driver)

        targets = create_targets(_VERSIONS[website_version])
        _LOGGER.debug(f'Targets: {targets}')

        wait_and_identify_trigger = partial(_wait_and_identify_trigger, targets, driver, oauth_timeout)


        # wait for the page to load
        wait_and_identify_trigger(is_present(targets['USER_NAME']), skip_identify=True)
        _LOGGER.info('Gateway auth webpage loaded')

        immediate_attempts = 0

        while immediate_attempts < max(max_immediate_attempts, 1):
            immediate_attempts += 1
            _LOGGER.info(f'Login attempt number {immediate_attempts}')

            try:
                attempt(targets, wait_and_identify_trigger, driver, account, password, key, presubmit_buffer, min_presubmit_buffer, max_presubmit_buffer, max_failed_auth, two_fa_handler, two_fa_select_target, strict_two_fa_code, outputs_dir)
            except BreakException:
                """ Not very proud of using exceptions for flow of control, but doing so simplifies the logic of breaking this while loop into functions and being able to break, continue, shutdown, etc. from within these functions."""
                break
            except ContinueException:
                continue
            except SuccessException:
                success = True
                break
            except ShutdownException:
                return False, True

        time.sleep(1)
    except TimeoutException as e:
        handle_timeout_exception(e, targets, driver, website_version, route_auth, base_url, outputs_dir)
        success = False
    except Exception as e:
        _LOGGER.error(f'Error encountered during authentication \nException:\n{exception_to_string(e)}')
        save_screenshot(driver, outputs_dir, '__generic-exception')
        success = False
    finally:
        shut_down_browser(driver, display)

    return success, False

def handle_two_fa(two_fa_handler:TwoFaHandler, driver:WebDriver, strict_two_fa_code:bool) -> Optional[str]:
    _LOGGER.info(f'Attempting to acquire 2FA code from: {two_fa_handler}')

    try:
        two_fa_code = two_fa_handler.get_two_fa_code(driver)
        if two_fa_code is not None:
            two_fa_code = str(two_fa_code)  # in case someone returns an integer
    except Exception as e:
        _LOGGER.error(f'Error encountered while acquiring 2FA code. \nException:\n{exception_to_string(e)}')
        return None

    _LOGGER.debug(f'2FA code returned: {two_fa_code}')

    if strict_two_fa_code and two_fa_code is not None and \
            (not two_fa_code.isdigit() or len(two_fa_code) != 6):
        _LOGGER.error(f'Illegal 2FA code returned: {two_fa_code}. Ensure the 2FA code contains 6 digits or disable this check by setting IBEAM_STRICT_TWO_FA_CODE to False.')
        return None

    return two_fa_code
