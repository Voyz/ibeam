import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.common import WebDriverException

import ibeam
from ibeam.src import var

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)


_DRIVER_NAMES = {}


def _new_chrome_driver(driver_path, name: str = 'default', headless: bool = True, incognito: bool = True, ui_scaling: float = 1) -> webdriver.Chrome:
    """Creates a new chrome driver."""

    global _DRIVER_NAMES

    _DRIVER_NAMES[name] = True  # just to ensure the name is in the dict
    driver_index = list(_DRIVER_NAMES.keys()).index(name)  # order of insertion dictates the driver_index

    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    if incognito:
        options.add_argument("--incognito")  # this allows 2FA method to be selected every time
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument(f'--remote-debugging-port={9222 + driver_index}')
    options.add_argument('--useAutomationExtension=false')
    options.add_argument('--disable-extensions')
    options.add_argument('--dns-prefetch-disable')
    options.add_argument('--disable-features=VizDisplayCompositor')
    options.add_argument(f"--force-device-scale-factor={ui_scaling}")
    options.add_argument(f'--user-data-dir={tempfile.gettempdir()}/ibeam-chrome-{name}')
    driver = webdriver.Chrome(driver_path, options=options)
    if driver is None:
        _LOGGER.error('Unable to create a new chrome driver.')

    return driver


def release_chrome_driver(driver: webdriver.Chrome):
    driver.quit()


def start_driver(driver_path: str,
                 name: str = 'default',
                 headless: bool = True,
                 incognito: bool = True,
                 ui_scaling: float = 1,
                 page_load_timeout: int = 15
                 ) -> Optional[webdriver.Chrome]:
    try:
        driver = _new_chrome_driver(driver_path=driver_path, name=name, headless=headless, incognito=incognito, ui_scaling=ui_scaling)
        driver.set_page_load_timeout(page_load_timeout)
    except WebDriverException as e:
        if 'net::ERR_CONNECTION_REFUSED' in e.msg:
            _LOGGER.error(
                'Connection to Gateway refused. This could indicate IB Gateway is not running. Consider increasing IBEAM_GATEWAY_STARTUP wait buffer')
            return None
        if 'net::ERR_CONNECTION_CLOSED' in e.msg:
            _LOGGER.error(
                f'Connection to Gateway failed. This could indicate IB Gateway is not running correctly or that its port was already occupied')
            return None
        else:
            raise e

    return driver


def save_screenshot(driver, outputs_dir, postfix=''):
    if not var.ERROR_SCREENSHOTS or driver is None:
        return

    now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    outputs_path = Path(outputs_dir)
    screenshot_name = f'ibeam__{ibeam.__version__}__{now}{postfix}.png'

    try:
        required_width = driver.execute_script('return document.body.parentNode.scrollWidth')
        required_height = driver.execute_script('return document.body.parentNode.scrollHeight')
        driver.set_window_size(required_width, required_height)

        outputs_path.mkdir(exist_ok=True)
        screenshot_filepath = os.path.join(outputs_dir, screenshot_name)

        # a little hack to prevent overwriting screenshots saved in the same second
        if os.path.exists(screenshot_filepath):
            save_screenshot(driver, outputs_dir, postfix + '_')
            return

        _LOGGER.info(
            f'Saving screenshot to {screenshot_filepath}. Make sure to cover your credentials if you share it with others.')
        driver.get_screenshot_as_file(screenshot_filepath)
    except Exception as e:
        _LOGGER.exception(f"Exception while saving screenshot: {str(e)} for screenshot: {screenshot_name}")


class DriverFactory():
    def __init__(self,
                 driver_path: str,
                 name: str = 'default',
                 headless: bool = True,
                 incognito: bool = True,
                 ui_scaling: float = 1,
                 page_load_timeout: int = 15
                 ):
        self.driver_path = driver_path
        self.name = name
        self.headless = headless
        self.incognito = incognito
        self.ui_scaling = ui_scaling
        self.page_load_timeout = page_load_timeout

    def new_driver(self,
                   driver_path: str = None,
                   name: str = None,
                   headless: bool = None,
                   incognito: bool = None,
                   ui_scaling: float = None,
                   page_load_timeout: int = None
                   ) -> webdriver.Chrome:

        driver_path = driver_path if driver_path is not None else self.driver_path
        name = name if name is not None else self.name
        headless = headless if headless is not None else self.headless
        incognito = incognito if incognito is not None else self.incognito
        ui_scaling = ui_scaling if ui_scaling is not None else self.ui_scaling
        page_load_timeout = page_load_timeout if page_load_timeout is not None else self.page_load_timeout

        return start_driver(driver_path=driver_path, name=name, headless=headless, incognito=incognito, ui_scaling=ui_scaling, page_load_timeout=page_load_timeout)


def start_up_browser(driver_factory:DriverFactory, base_url: str, route_auth: str) -> (webdriver.Chrome, Optional[Display]):
    display = None
    if sys.platform == 'linux':
        display = Display(visible=False, size=(800, 600))
        display.start()

    driver = driver_factory.new_driver()
    if driver is None:
        return False, False

    return driver, display


def shut_down_browser(driver:webdriver.Chrome, display:Optional[Display]):
    _LOGGER.info(f'Cleaning up the resources. Display: {display} | Driver: {driver}')

    if display is not None:
        display.stop()

    if driver is not None:
        release_chrome_driver(driver)
