import logging
import os
import re
import time
import urllib.parse
from pathlib import Path
from typing import Union

from ibeam.src import var
from ibeam.src.authenticate import any_of, new_chrome_driver, release_chrome_driver, save_screenshot
from ibeam.src.two_fa_handlers.two_fa_handler import TwoFaHandler

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)

_GOOG_QR_CODE_CLASS = os.environ.get('IBEAM_GOOG_QR_CODE_CLASS', 'qr-code')
"""HTML element indicating web messages needs authorization."""

_GOOG_AUTH_REMEMBER_CLASS = os.environ.get('IBEAM_GOOG_AUTH_REMEMBER_CLASS', 'local-storage-checkbox')
"""HTML element to remember web messages device pairing."""

_GOOG_MESSAGES_LIST_CLASS = os.environ.get('IBEAM_GOOG_MESSAGES_LIST_CLASS', '.text-content.unread .snippet-text')
"""HTML element indicating web messages has loaded."""

_GOOG_2FA_HEADING = os.environ.get('IBEAM_GOOG_2FA_HEADING', 'Your requested authentication code')
"""HTML element text indicating 2fa message received."""


class GoogleMessagesTwoFaHandler(TwoFaHandler):

    def __init__(self, driver_path):
        self.driver_path = driver_path

    def get_two_fa_code(self) -> Union[str, None]:
        code_two_fa = None

        driver_2fa = new_chrome_driver(self.driver_path, name='google_msg')
        if driver_2fa is None:
            return None

        driver_2fa.get('https://messages.google.com/web')

        sms_auth_present = EC.presence_of_element_located((By.CLASS_NAME, _GOOG_QR_CODE_CLASS))
        sms_code_present = EC.text_to_be_present_in_element((By.CSS_SELECTOR, _GOOG_MESSAGES_LIST_CLASS),
                                                            _GOOG_2FA_HEADING)

        WebDriverWait(driver_2fa, 240).until(any_of(sms_auth_present, sms_code_present))

        sms_auth_el = driver_2fa.find_elements_by_class_name(_GOOG_QR_CODE_CLASS)

        if sms_auth_el:
            driver_2fa.find_element_by_class_name(_GOOG_AUTH_REMEMBER_CLASS).click()

            data = urllib.parse.quote(sms_auth_el[0].get_attribute('data-' + _GOOG_QR_CODE_CLASS))

            _LOGGER.info(
                'Web messages is not authenticated. Open this URL to pair web messages with your android phone:')
            _LOGGER.info(
                f'http://api.qrserver.com/v1/create-qr-code/?color=000000&bgcolor=FFFFFF&qzone=1&margin=0&size=400x400&ecc=L&data={data}')

            WebDriverWait(driver_2fa, 120).until(sms_code_present)

        sms_list_el = driver_2fa.find_elements_by_css_selector(_GOOG_MESSAGES_LIST_CLASS)

        if not sms_list_el:
            _LOGGER.error('Timeout or authentication error while loading sms messages.')
            save_screenshot(driver_2fa, postfix='__google_2fa')
        else:
            _LOGGER.info(sms_list_el[0].text)
            sms_list_el[0].click()  # mark message as read
            time.sleep(2)  # wait for click to mark message as read
            code_two_fa = re.search(r'(\d+)', sms_list_el[0].text).group(1)

        release_chrome_driver(driver_2fa)

        return code_two_fa

    def __str__(self):
        return f"GoogleMessagesTwoFaHandler(driver_path={self.driver_path})"
