import logging
import re
import sys
import time
import urllib.parse
from pathlib import Path
import tempfile

from cryptography.fernet import Fernet
from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from ibeam.src import var

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)


def new_chrome_driver(driver_path, headless: bool = True):
    """Creates a new chrome driver."""
    options = webdriver.ChromeOptions()
    if headless: options.add_argument('headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')
    # options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--useAutomationExtension=false")
    options.add_argument(f'--user-data-dir={tempfile.gettempdir()}/ibeam-chrome')
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


def authenticate_gateway(driver_path, account, password, key: str = None, base_url: str = None) -> bool:
    """
    Authenticates the currently running gateway.

    If both password and key are provided, cryptography.fernet decryption will be used.

    :return: Whether authentication was successful.
    """
    if base_url is None: base_url = var.GATEWAY_BASE_URL
    display = None
    try:
        if sys.platform == 'linux':
            display = Display(visible=0, size=(800, 600))
            display.start()

        _LOGGER.debug(f'Loading auth page at {base_url + var.ROUTE_AUTH}')
        try:
            driver = new_chrome_driver(driver_path)
            driver.get(base_url + var.ROUTE_AUTH)
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

        user_name_present = EC.presence_of_element_located((By.ID, var.USER_NAME_EL_ID))
        WebDriverWait(driver, 15).until(user_name_present)

        _LOGGER.debug('Gateway auth page loaded')

        user_name_el = driver.find_element_by_id(var.USER_NAME_EL_ID)
        password_el = driver.find_element_by_id(var.PASSWORD_EL_ID)
        user_name_el.send_keys(account)

        if key is None:
            password_el.send_keys(password)
        else:
            password_el.send_keys(Fernet(key).decrypt(password.encode('utf-8')).decode("utf-8"))

        _LOGGER.debug('Submitting the form')
        submit_form_el = driver.find_element_by_id(var.SUBMIT_EL_ID)
        submit_form_el.click()

        success_present = EC.text_to_be_present_in_element((By.TAG_NAME, 'pre'), var.SUCCESS_EL_TEXT)
        two_factor_input_present = EC.presence_of_element_located((By.ID, var.TWO_FAC_EL_ID))

        WebDriverWait(driver, var.OAUTH_TIMEOUT).until(AnyEc(success_present, two_factor_input_present))

        two_factor_el = driver.find_elements_by_id(var.TWO_FAC_EL_ID)

        # if two_factor_el:
        #
        #     _LOGGER.debug(f'2FA in use: Loading messages.google.com/web')
        #
        #     driver_2fa = new_chrome_driver(driver_path)
        #     driver_2fa.get('https://messages.google.com/web')
        #
        #     sms_auth_present = EC.presence_of_element_located((By.CLASS_NAME, var.SMS_QR_CODE_CLASS))
        #     sms_code_present = EC.text_to_be_present_in_element((By.CLASS_NAME, var.SMS_MESSAGES_LIST_CLASS),
        #                                                         var.SMS_2FA_HEADING)
        #
        #     WebDriverWait(driver_2fa, 240).until(AnyEc(sms_auth_present, sms_code_present))
        #
        #     sms_auth_el = driver_2fa.find_elements_by_class_name(var.SMS_QR_CODE_CLASS)
        #
        #     if sms_auth_el:
        #         driver_2fa.find_element_by_class_name(var.SMS_AUTH_REMEMBER_CLASS).click()
        #
        #         _LOGGER.info(
        #             f'Web messages is not authenticated. Open this URL to pair web messages with your android phone:')
        #         _LOGGER.info(
        #             f'http://api.qrserver.com/v1/create-qr-code/?color=000000&bgcolor=FFFFFF&qzone=1&margin=0&size=400x400&ecc=L&data='
        #             + urllib.parse.quote(sms_auth_el[0].get_attribute('data-' + var.SMS_QR_CODE_CLASS))
        #         )
        #
        #         WebDriverWait(driver_2fa, 120).until(sms_code_present)
        #
        #     sms_list_el = driver_2fa.find_elements_by_class_name(var.SMS_MESSAGES_LIST_CLASS)
        #
        #     if not sms_list_el:
        #         _LOGGER.info('Timeout or authentication error while loading sms messages.')
        #         return False
        #
        #     _LOGGER.info(sms_list_el[0].text)
        #
        #     code_2fa = re.search(r'(\d+)', sms_list_el[0].text).group(1)
        #     two_factor_el[0].send_keys(code_2fa)
        #
        #     submit_form_el = driver.find_element_by_id(var.SUBMIT_EL_ID)
        #     submit_form_el.click()
        # 
        #     WebDriverWait(driver, var.OAUTH_TIMEOUT).until(success_present)

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
