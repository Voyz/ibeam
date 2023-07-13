import logging
import sys
import time
from pathlib import Path
from typing import Union, Optional

from cryptography.fernet import Fernet
from pyvirtualdisplay import Display
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.ui import Select

from ibeam.src import var
from ibeam.src.login.driver import release_chrome_driver, start_driver, save_screenshot
from ibeam.src.utils.py_utils import exception_to_string
from ibeam.src.two_fa_handlers.two_fa_handler import TwoFaHandler
from ibeam.src.utils.selenium_utils import text_to_be_present_in_element, any_of

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)

_FAILED_ATTEMPTS = 0
_PRESUBMIT_BUFFER = var.MIN_PRESUBMIT_BUFFER

_VERSIONS = {
    1: {
        'USER_NAME_EL': 'user_name',
        'ERROR_EL': 'alert alert-danger margin-top-10'
    },
    2: {
        'USER_NAME_EL': 'username',
        'ERROR_EL': 'xyz-errormessage'
    }
}


def identify_trigger(trigger, elements) -> Optional[str]:
    if trigger.get_attribute('id') == elements['TWO_FA_EL_ID']:
        return elements['TWO_FA_EL_ID']

    if trigger.get_attribute('id') == elements['TWO_FA_SELECT_EL_ID']:
        return elements['TWO_FA_SELECT_EL_ID']

    if elements['TWO_FA_EL_ID'].replace('.', '') in trigger.get_attribute('class'):
        return elements['TWO_FA_EL_ID']

    if elements['TWO_FA_SELECT_EL_ID'].replace('.', '') in trigger.get_attribute('class'):
        return elements['TWO_FA_EL_ID']

    if elements['ERROR_EL'] in trigger.get_attribute('class'):
        return elements['ERROR_EL']

    if elements['TWO_FA_NOTIFICATION_EL'] in trigger.get_attribute('class'):
        return elements['TWO_FA_NOTIFICATION_EL']

    if elements['IBKEY_PROMO_EL_CLASS'] in trigger.get_attribute('class'):
        return elements['IBKEY_PROMO_EL_CLASS']

    if trigger.text == elements['SUCCESS_EL_TEXT']:
        return elements['SUCCESS_EL_TEXT']

    raise RuntimeError(f'Trigger found but cannot be identified: {trigger} :: {trigger.get_attribute("outerHTML")}')


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


def create_elements(versions: dict):
    elements = {}
    elements['USER_NAME_EL'] = versions['USER_NAME_EL']
    elements['PASSWORD_EL'] = var.PASSWORD_EL
    elements['SUBMIT_EL'] = var.SUBMIT_EL
    elements['ERROR_EL'] = versions['ERROR_EL']
    elements['SUCCESS_EL_TEXT'] = var.SUCCESS_EL_TEXT
    elements['IBKEY_PROMO_EL_CLASS'] = var.IBKEY_PROMO_EL_CLASS
    elements['TWO_FA_EL_ID'] = var.TWO_FA_EL_ID
    elements['TWO_FA_NOTIFICATION_EL'] = var.TWO_FA_NOTIFICATION_EL
    elements['TWO_FA_INPUT_EL_ID'] = var.TWO_FA_INPUT_EL_ID
    elements['TWO_FA_SELECT_EL_ID'] = var.TWO_FA_SELECT_EL_ID


    if var.USER_NAME_EL is not None and var.USER_NAME_EL != elements['USER_NAME_EL']:
        _LOGGER.warning(f'USER_NAME_EL is forced to "{var.USER_NAME_EL}", contrary to the element found on the website: "{elements["USER_NAME_EL"]}"')
        elements['USER_NAME_EL'] = var.USER_NAME_EL

    if var.ERROR_EL is not None and var.ERROR_EL != elements['ERROR_EL']:
        _LOGGER.warning(f'ERROR_EL is forced to "{var.ERROR_EL}", contrary to the element found on the website: "{elements["ERROR_EL"]}"')
        elements['ERROR_EL'] = var.ERROR_EL

    return elements


def log_in(driver_path,
           account,
           password,
           key: str = None,
           base_url: str = None,
           two_fa_handler: TwoFaHandler = None) -> (bool, bool):
    """
    Logs into the currently running gateway.

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
    website_version = -1
    elements = {}

    global _PRESUBMIT_BUFFER
    presubmit_buffer = _PRESUBMIT_BUFFER

    try:
        _LOGGER.info(f'Loading auth webpage at {base_url + var.ROUTE_AUTH}')
        if sys.platform == 'linux':
            display = Display(visible=False, size=(800, 600))
            display.start()

        driver = start_driver(base_url, driver_path)
        if driver is None:
            return False, False

        driver.get(base_url + var.ROUTE_AUTH)

        website_version = check_version(driver)

        elements = create_elements(_VERSIONS[website_version])
        _LOGGER.debug(f'Elements: {elements}')

        # wait for the page to load
        user_name_present = EC.presence_of_element_located((By.NAME, elements['USER_NAME_EL']))
        WebDriverWait(driver, 15).until(user_name_present)
        _LOGGER.info('Gateway auth webpage loaded')

        immediate_attempts = 0

        while immediate_attempts < max(var.MAX_IMMEDIATE_ATTEMPTS, 1):
            immediate_attempts += 1
            _LOGGER.info(f'Login attempt number {immediate_attempts}')

            # time.sleep(300)

            # input credentials
            user_name_el = driver.find_element(By.NAME, elements['USER_NAME_EL'])
            password_el = driver.find_element(By.NAME, elements['PASSWORD_EL'])

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
            submit_form_el = driver.find_element(By.CSS_SELECTOR, elements['SUBMIT_EL'])
            submit_form_el.click()

            # observe results - either success or 2FA request
            success_present = text_to_be_present_in_element([(By.TAG_NAME, 'pre'), (By.TAG_NAME, 'body')],
                                                            elements['SUCCESS_EL_TEXT'])
            two_factor_input_present = EC.visibility_of_element_located((By.ID, elements['TWO_FA_EL_ID']))

            two_factor_select_present = EC.visibility_of_element_located((By.ID, elements['TWO_FA_SELECT_EL_ID']))

            two_factor_notification = EC.visibility_of_element_located((By.CLASS_NAME, elements['TWO_FA_NOTIFICATION_EL']))

            error_displayed = EC.visibility_of_element_located((By.CSS_SELECTOR, '.' + elements['ERROR_EL'].replace(' ', '.')))
            ibkey_promo_skip_clickable = EC.element_to_be_clickable((By.CLASS_NAME, elements['IBKEY_PROMO_EL_CLASS']))

            trigger = WebDriverWait(driver, var.OAUTH_TIMEOUT).until(
                any_of(success_present,
                       two_factor_input_present,
                       two_factor_select_present,
                       two_factor_notification,
                       error_displayed,
                       ibkey_promo_skip_clickable))

            trigger_identifier = identify_trigger(trigger, elements)
            _LOGGER.debug(f'trigger: {trigger_identifier}')

            if trigger_identifier == elements['TWO_FA_SELECT_EL_ID']:
                _LOGGER.info(f'Required to select a 2FA method.')
                select_el = driver.find_element(By.ID, elements['TWO_FA_SELECT_EL_ID'])
                select = Select(select_el)
                select.select_by_visible_text(var.TWO_FA_SELECT_TARGET)

                trigger = WebDriverWait(driver, var.OAUTH_TIMEOUT).until(
                    any_of(success_present,
                           two_factor_input_present,
                           two_factor_notification,
                           error_displayed,
                           ibkey_promo_skip_clickable))

                _LOGGER.info(f'2FA method "{var.TWO_FA_SELECT_TARGET}" selected successfully.')

                trigger_identifier = identify_trigger(trigger, elements)
                _LOGGER.debug(f'trigger: {trigger_identifier}')

            if trigger_identifier == elements['TWO_FA_NOTIFICATION_EL']:
                _LOGGER.info(f'Credentials correct, but Gateway requires notification two-factor authentication.')

                if two_fa_handler is not None:
                    two_fa_success = two_fa_handler.get_two_fa_code(driver)
                    if not two_fa_success:
                        driver.refresh()
                        continue  # attempt a direct retry

                trigger = WebDriverWait(driver, var.OAUTH_TIMEOUT).until(
                    any_of(success_present, ibkey_promo_skip_clickable, error_displayed))
                trigger_identifier = identify_trigger(trigger, elements)

            # handle 2FA
            if trigger_identifier == elements['TWO_FA_EL_ID']:
                _LOGGER.info(f'Credentials correct, but Gateway requires two-factor authentication.')
                if two_fa_handler is None:
                    _LOGGER.critical(
                        f'######## ATTENTION! ######## No 2FA handler found. You may define your own 2FA handler or use built-in handlers. See documentation for more: https://github.com/Voyz/ibeam/wiki/Two-Factor-Authentication')
                    return False, True

                two_fa_code = handle_two_fa(two_fa_handler, driver, var.STRICT_TWO_FA_CODE)

                if two_fa_code is None:
                    _LOGGER.warning(f'No 2FA code returned. Aborting authentication.')
                else:
                    two_fa_el = driver.find_elements(By.ID, elements['TWO_FA_INPUT_EL_ID'])
                    WebDriverWait(driver, var.OAUTH_TIMEOUT).until(
                        EC.element_to_be_clickable((By.ID, elements['TWO_FA_INPUT_EL_ID'])))

                    two_fa_el[0].clear()
                    two_fa_el[0].send_keys(two_fa_code)

                    _LOGGER.info('Submitting the 2FA form')
                    two_fa_el[0].send_keys(Keys.RETURN)
                    # submit_form_el = driver.find_element(By.CSS_SELECTOR, elements['SUBMIT_EL'])
                    # WebDriverWait(driver, var.OAUTH_TIMEOUT).until(
                    #     EC.element_to_be_clickable((By.CSS_SELECTOR, elements['SUBMIT_EL'])))
                    # submit_form_el.click()

                    trigger = WebDriverWait(driver, var.OAUTH_TIMEOUT).until(
                        any_of(success_present, ibkey_promo_skip_clickable, error_displayed))
                    trigger_identifier = identify_trigger(trigger, elements)

            trigger_class = trigger.get_attribute('class')

            if elements['IBKEY_PROMO_EL_CLASS'] in trigger_class:
                _LOGGER.info('Handling IB-Key promo display...')
                trigger.click()
                trigger = WebDriverWait(driver, 10).until(any_of(success_present, error_displayed))
                trigger_identifier = identify_trigger(trigger, elements)

            if trigger_identifier == elements['ERROR_EL']:
                _LOGGER.error(f'Error displayed by the login webpage: {trigger.text}')
                save_screenshot(driver, '__failed_attempt')

                if trigger.text == 'Invalid username password combination' and presubmit_buffer < var.MAX_PRESUBMIT_BUFFER:
                    _PRESUBMIT_BUFFER += 5
                    if _PRESUBMIT_BUFFER >= var.MAX_PRESUBMIT_BUFFER:
                        _PRESUBMIT_BUFFER = var.MAX_PRESUBMIT_BUFFER
                        _LOGGER.warning(f'The presubmit buffer set to maximum: {var.MAX_PRESUBMIT_BUFFER}')
                    else:
                        _LOGGER.warning(f'Increased presubmit buffer to {_PRESUBMIT_BUFFER}')

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

            elif trigger_identifier == elements['TWO_FA_EL_ID']:
                time.sleep(1)
                driver.refresh()
                continue  # attempt a direct retry
                pass  # this means no two_fa_code was returned and trigger remained the same - ie. don't authenticate
                # todo: retry authentication or resend code
            elif trigger_identifier == elements['SUCCESS_EL_TEXT']:
                _LOGGER.info('Webpage displayed "Client login succeeds"')
                _FAILED_ATTEMPTS = 0
                _PRESUBMIT_BUFFER = var.MIN_PRESUBMIT_BUFFER
                success = True
                break

        time.sleep(2)
    except TimeoutException as e:
        page_loaded_correctly = True
        try:
            website_loaded = EC.presence_of_element_located((By.CLASS_NAME, 'login'))
            WebDriverWait(driver, 5).until(website_loaded)
        except TimeoutException as _:
            page_loaded_correctly = False

        if not page_loaded_correctly or website_version == -1:
            _LOGGER.error(f'Timeout reached when waiting for authentication. The website seems to not be loaded correctly. Consider increasing IBEAM_PAGE_LOAD_TIMEOUT. \nWebsite URL: {base_url + var.ROUTE_AUTH} \nIBEAM_PAGE_LOAD_TIMEOUT: {var.PAGE_LOAD_TIMEOUT} \nException:\n{exception_to_string(e)}')
        else:
            _LOGGER.error(f'Timeout reached searching for website elements, but the website seems to be loaded correctly. It is possible the setup is incorrect. \nWebsite version: {website_version} \nDOM elements searched for: {elements}. \nException:\n{exception_to_string(e)}')

        save_screenshot(driver, '__timeout-exception')
        success = False
    except Exception as e:
        _LOGGER.error(f'Error encountered during authentication \nException:\n{exception_to_string(e)}')
        save_screenshot(driver, '__generic-exception')
        success = False
    finally:
        # if sys.platform == 'linux' and display is not None:
        _LOGGER.info(f'Cleaning up the resources. Display: {display} | Driver: {driver}')

        if display is not None:
            display.stop()

        if driver is not None:
            release_chrome_driver(driver)

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
