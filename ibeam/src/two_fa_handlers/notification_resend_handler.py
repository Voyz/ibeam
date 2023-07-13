import logging
import os
import time
from pathlib import Path
from typing import Optional

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from ibeam.src import var
from ibeam.src.login.authenticate import text_to_be_present_in_element
from ibeam.src.login.driver import save_screenshot
from ibeam.src.two_fa_handlers.two_fa_handler import TwoFaHandler
from selenium.webdriver.support import expected_conditions as EC

_NOTIFICATION_RESEND_RETRIES = int(os.environ.get('IBEAM_NOTIFICATION_RESEND_RETRIES', 10))
"""How many times to resend the notification."""

_NOTIFICATION_RESEND_INTERVAL = int(os.environ.get('IBEAM_NOTIFICATION_RESEND_INTERVAL', 10))
"""How many times to resend the notification."""

_NOTIFICATION_RESEND_EL = os.environ.get('IBEAM_NOTIFICATION_RESEND_EL', "a[onclick*='resendNotification()']")
"""Css selector for the resend notification button."""

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)


class NotificationResendTwoFaHandler(TwoFaHandler):
    """ This 2FA handler will repeatedly resend notifications to user's phone. """

    def check_and_resend(self, driver, depth=0):
        if depth >= _NOTIFICATION_RESEND_RETRIES:
            _LOGGER.error(f'Reached maximum number of notification resend retries: {_NOTIFICATION_RESEND_RETRIES}. Aborting.')
            return False

        try:
            WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.CSS_SELECTOR, _NOTIFICATION_RESEND_EL)))
        except TimeoutException:
            _LOGGER.error(f'Notification resend element not found: {_NOTIFICATION_RESEND_EL}. Aborting.')
            return False

        notification_resend_el = driver.find_element_by_css_selector(_NOTIFICATION_RESEND_EL)
        notification_resend_el.click()

        success_present = text_to_be_present_in_element([(By.TAG_NAME, 'pre'), (By.TAG_NAME, 'body')],
                                                        var.SUCCESS_EL_TEXT)

        try:
            WebDriverWait(driver, _NOTIFICATION_RESEND_INTERVAL).until(success_present)
        except TimeoutException:
            _LOGGER.info(f'Success condition was not found when resending 2FA notification. Reattempting {_NOTIFICATION_RESEND_RETRIES - depth - 1} more times.')
            return self.check_and_resend(driver, depth + 1)
        else:
            return True

    def get_two_fa_code(self, driver) -> Optional[bool]:
        time.sleep(2)  # give the first notification a short while to arrive first
        try:
            return self.check_and_resend(driver)
        except Exception as e:
            _LOGGER.exception(f'Exception while handling notification resend 2FA: {e}')
            save_screenshot(driver, self.outputs_dir, postfix='__notification_2fa')

    def __str__(self):
        return "NotificationResendTwoFaHandler()"
