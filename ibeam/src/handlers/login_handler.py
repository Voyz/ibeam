import logging
import time
from functools import partial
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.ui import Select

from ibeam.src.handlers.secrets_handler import SecretsHandler
from ibeam.src.login.driver import DriverFactory, start_up_browser, save_screenshot, shut_down_browser
from ibeam.src.login.targets import Targets, targets_from_versions, is_present, Target, identify_target, find_element, has_text, is_visible, is_clickable
from ibeam.src.two_fa_handlers.two_fa_handler import TwoFaHandler
from ibeam.src.utils.py_utils import exception_to_string
from ibeam.src.utils.selenium_utils import any_of

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)



class AttemptException(Exception):
    def __init__(self, *args, cause:str, **kwargs):
        self.cause = cause
        super().__init__(*args, **kwargs)

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

def handle_two_fa(two_fa_handler:TwoFaHandler, driver:webdriver.Chrome, strict_two_fa_code:bool) -> Optional[str]:
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

class LoginHandler():
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

    def __init__(self,
                 secrets_handler:SecretsHandler,
                 two_fa_handler:TwoFaHandler,
                 driver_factory:DriverFactory,
                 targets: Targets,
                 base_url: str,
                 route_auth: str,
                 two_fa_select_target: str,
                 strict_two_fa_code: bool,
                 max_immediate_attempts: int,
                 oauth_timeout: int,
                 max_presubmit_buffer: int,
                 min_presubmit_buffer: int,
                 max_failed_auth: int,
                 outputs_dir: str,
                 ):

        self.secrets_handler = secrets_handler
        self.two_fa_handler = two_fa_handler
        self.driver_factory = driver_factory
        self.targets = targets

        self.base_url = base_url
        self.route_auth = route_auth
        self.two_fa_select_target = two_fa_select_target
        self.strict_two_fa_code = strict_two_fa_code
        self.max_immediate_attempts = max_immediate_attempts
        self.oauth_timeout = oauth_timeout
        self.max_presubmit_buffer = max_presubmit_buffer
        self.min_presubmit_buffer = min_presubmit_buffer
        self.max_failed_auth = max_failed_auth
        self.outputs_dir = outputs_dir

        self.failed_attempts = 0
        self.presubmit_buffer = self.min_presubmit_buffer



    # def login(self):
    #     return log_in(
    #         targets=self.targets,
    #         driver_factory=self.driver_factory,
    #         account=self.secrets_handler.account,
    #         password=self.secrets_handler.password,
    #         key=self.secrets_handler.key,
    #         base_url=self.cnf.GATEWAY_BASE_URL,
    #         two_fa_handler=self.two_fa_handler,
    #         route_auth=self.cnf.ROUTE_AUTH,
    #         two_fa_select_target=self.cnf.TWO_FA_SELECT_TARGET,
    #         strict_two_fa_code=self.cnf.STRICT_TWO_FA_CODE,
    #         max_immediate_attempts=self.cnf.MAX_IMMEDIATE_ATTEMPTS,
    #         oauth_timeout=self.cnf.OAUTH_TIMEOUT,
    #         max_presubmit_buffer=self.cnf.MAX_PRESUBMIT_BUFFER,
    #         min_presubmit_buffer=self.cnf.MIN_PRESUBMIT_BUFFER,
    #         max_failed_auth=self.cnf.MAX_FAILED_AUTH,
    #         outputs_dir=self.cnf.OUTPUTS_DIR,
    #     )

    def step_login(self,
                   targets: Targets,
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

    def step_select_two_fa(self,
                           targets: Targets,
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


    def step_two_fa_notification(self,
                                 targets: Targets,
                                 wait_and_identify_trigger: callable,
                                 driver: webdriver.Chrome,
                                 two_fa_handler: TwoFaHandler,
                                 ):
        _LOGGER.info(f'Credentials correct, but Gateway requires notification two-factor authentication.')

        if two_fa_handler is not None:
            two_fa_success = two_fa_handler.get_two_fa_code(driver)
            if not two_fa_success:
                driver.refresh()
                raise AttemptException(cause='continue')

        trigger, target = wait_and_identify_trigger(
            has_text(targets['SUCCESS']),
            is_clickable(targets['IBKEY_PROMO']),
            is_visible(targets['ERROR'])
        )
        return trigger, target

    def step_two_fa(self,
                    targets: Targets,
                    wait_and_identify_trigger: callable,
                    driver: webdriver.Chrome,
                    two_fa_handler: TwoFaHandler,
                    strict_two_fa_code: bool,
                    ):
        _LOGGER.info(f'Credentials correct, but Gateway requires two-factor authentication.')
        if two_fa_handler is None:
            _LOGGER.critical(
                f'######## ATTENTION! ######## No 2FA handler found. You may define your own 2FA handler or use built-in handlers. See documentation for more: https://github.com/Voyz/ibeam/wiki/Two-Factor-Authentication')
            raise AttemptException(cause='shutdown')

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

    def step_handle_ib_key_promo(self,
                                 targets: Targets,
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

    def step_error(self,
                   driver:webdriver.Chrome,
                   error_trigger: WebElement,
                   max_presubmit_buffer: int,
                   max_failed_auth: int,
                   outputs_dir: str
                   ):
        _LOGGER.error(f'Error displayed by the login webpage: {error_trigger.text}')
        save_screenshot(driver, outputs_dir, '__failed_attempt')
        if error_trigger.text == 'Invalid username password combination' and self.presubmit_buffer < max_presubmit_buffer:
            # global _PRESUBMIT_BUFFER
            # _PRESUBMIT_BUFFER += 5
            self.presubmit_buffer += 5
            if self.presubmit_buffer >= self.max_presubmit_buffer:
                self.presubmit_buffer = self.max_presubmit_buffer
                _LOGGER.warning(f'The presubmit buffer set to maximum: {self.max_presubmit_buffer}')
            else:
                _LOGGER.warning(f'Increased presubmit buffer to {self.presubmit_buffer}')

        # try to prevent having the account locked-out
        if error_trigger.text == 'failed' or error_trigger.text == 'Invalid username password combination' and max_failed_auth > 0:
            self.failed_attempts += 1
            if self.failed_attempts >= self.max_failed_auth:
                _LOGGER.critical(
                    f'######## ATTENTION! ######## Maximum number of failed authentication attempts (IBEAM_MAX_FAILED_AUTH={self.max_failed_auth}) reached. IBeam will shut down to prevent an account lock-out. It is recommended you attempt to authenticate manually in order to reset the counter. Read the execution logs and report issues at https://github.com/Voyz/ibeam/issues')
                raise AttemptException(cause='shutdown')

        time.sleep(1)
        raise AttemptException(cause='continue')


    def handle_timeout_exception(self,
                                 e:Exception,
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

    def step_failed_two_fa(self, driver:webdriver.Chrome):
        # this means no two_fa_code was returned and trigger remained the same - ie. don't authenticate
        time.sleep(1)
        driver.refresh()
        raise AttemptException(cause='continue')
        # todo: retry authentication or resend code

    def step_success(self):
        _LOGGER.info('Webpage displayed "Client login succeeds"')
        self.failed_attempts = 0
        self.presubmit_buffer = self.min_presubmit_buffer
        raise AttemptException(cause='success')


    def attempt(
            self,
            targets: Targets,
            wait_and_identify_trigger: callable,
            driver: webdriver.Chrome
    ):
        trigger, target = self.step_login(targets, wait_and_identify_trigger, driver, self.secrets_handler.account, self.secrets_handler.password, self.secrets_handler.key, self.presubmit_buffer)

        if target == targets['TWO_FA_SELECT']:
            trigger, target = self.step_select_two_fa(targets, wait_and_identify_trigger, driver, self.two_fa_select_target)

        if target == targets['TWO_FA_NOTIFICATION']:
            trigger, target = self.step_two_fa_notification(targets, wait_and_identify_trigger, driver, self.two_fa_handler)

        if target == targets['TWO_FA']:
            trigger, target = self.step_two_fa(targets, wait_and_identify_trigger, driver, self.two_fa_handler, self.strict_two_fa_code)

        if target == targets['IBKEY_PROMO']:
            trigger, target = self.step_handle_ib_key_promo(targets, wait_and_identify_trigger, trigger)

        if target == targets['ERROR']:
            self.step_error(driver, trigger, self.max_presubmit_buffer, self.max_failed_auth, self.outputs_dir)

        elif target == targets['TWO_FA']:
            self.step_failed_two_fa(driver)

        elif target == targets['SUCCESS']:
            self.step_success()

    def login(self) -> (bool, bool):
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
        targets = self.targets

        try:
            _LOGGER.info(f'Loading auth webpage at {self.base_url + self.route_auth}')
            driver, display = start_up_browser(self.driver_factory, self.base_url, self.route_auth)

            website_version = check_version(driver)

            targets = targets_from_versions(targets, self._VERSIONS[website_version])
            _LOGGER.debug(f'Targets: {targets}')

            wait_and_identify_trigger = partial(_wait_and_identify_trigger, targets, driver, self.oauth_timeout)

            # wait for the page to load
            wait_and_identify_trigger(is_present(targets['USER_NAME']), skip_identify=True)
            _LOGGER.info('Gateway auth webpage loaded')

            immediate_attempts = 0

            while immediate_attempts < max(self.max_immediate_attempts, 1):
                immediate_attempts += 1
                _LOGGER.info(f'Login attempt number {immediate_attempts}')

                try:
                    self.attempt(targets, wait_and_identify_trigger, driver)
                except AttemptException as e:
                    """ Not very proud of using exceptions for flow of control, but doing so simplifies the logic of splitting this while loop into functions and being able to break, continue, shutdown, etc. from within these functions."""

                    if e.cause == 'continue':
                        continue
                    elif e.cause =='success':
                        success = True
                        break
                    elif e.cause =='shutdown':
                        return False, True
                    elif e.cause == 'break':
                        break
                    else:
                        raise RuntimeError(f'Invalid AttemptException: {e}')


            time.sleep(1)
        except TimeoutException as e:
            self.handle_timeout_exception(e, targets, driver, website_version, self.route_auth, self.base_url, self.outputs_dir)
            success = False
        except Exception as e:
            _LOGGER.error(f'Error encountered during authentication \nException:\n{exception_to_string(e)}')
            save_screenshot(driver, self.outputs_dir, '__generic-exception')
            success = False
        finally:
            shut_down_browser(driver, display)

        return success, False
