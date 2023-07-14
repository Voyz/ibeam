import logging
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC

from ibeam.config import Config
from ibeam.src.utils.selenium_utils import text_to_be_present_in_element

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)


class Target():
    def __init__(self,
                 variable:str,
                 ):
        type, identifier = variable.split("@@")
        self.type = type
        self.identifier = identifier
        self.variable = variable

        if type == 'ID':
            self.by = By.ID
            self._identify = self.identify_by_id
        elif type == 'CSS_SELECTOR':
            self.by = By.CSS_SELECTOR
            self._identify = self.identify_by_css_selector
        elif type == 'CLASS_NAME':
            self.by = By.CLASS_NAME
            self._identify = self.identify_by_class
        elif type == 'NAME':
            self.by = By.NAME
            self._identify = self.identify_by_name
        elif type == 'TAG_NAME':
            self.by = [(By.TAG_NAME, 'pre'), (By.TAG_NAME, 'body')]
            self._identify = self.identify_by_text
        else:
            raise RuntimeError(f'Unknown target type: {type}@@{identifier}')

    def identify(self, trigger: WebElement) -> bool:
        return self._identify(trigger)

    def identify_by_id (self, trigger: WebElement) -> bool:
        return self.identifier in trigger.get_attribute('id')

    def identify_by_css_selector(self, trigger: WebElement) -> bool:
        return self.identifier.replace('.', ' ').strip() in trigger.get_attribute('class')
    def identify_by_class(self, trigger: WebElement) -> bool:
        return self.identifier in trigger.get_attribute('class')

    def identify_by_name(self, trigger: WebElement) -> bool:
        return self.identifier in trigger.get_attribute('name')

    def identify_by_text(self, trigger: WebElement) -> bool:
        return self.identifier in trigger.text

    def __repr__(self):
        return f'Target({self.variable})'


Targets = dict[str, Target]

def targets_from_versions(targets: Targets, versions: dict) -> Targets:
    version_target_user_name = Target(versions['USER_NAME_EL'])
    version_target_error = Target(versions['ERROR_EL'])

    if 'USER_NAME' in targets and version_target_user_name != targets['USER_NAME'].variable:
        _LOGGER.warning(f'USER_NAME target is forced to "{targets["USER_NAME"].variable}", contrary to the element found on the website: "{version_target_user_name}"')
    else:
        targets['USER_NAME'] = version_target_user_name

    if "ERROR" in targets and version_target_error != targets['ERROR'].variable:
        _LOGGER.warning(f'ERROR target is forced to "{targets["ERROR"].variable}", contrary to the element found on the website: "{version_target_error}"')
    else:
        targets['ERROR'] = version_target_error

    return targets

def create_targets(cnf:Config) -> Targets:
    targets = {}

    targets['PASSWORD'] = Target(cnf.PASSWORD_EL)
    targets['SUBMIT'] = Target(cnf.SUBMIT_EL)
    targets['SUCCESS'] = Target(cnf.SUCCESS_EL_TEXT)
    targets['IBKEY_PROMO'] = Target(cnf.IBKEY_PROMO_EL_CLASS)
    targets['TWO_FA'] = Target(cnf.TWO_FA_EL_ID)
    targets['TWO_FA_NOTIFICATION'] = Target(cnf.TWO_FA_NOTIFICATION_EL)
    targets['TWO_FA_INPUT'] = Target(cnf.TWO_FA_INPUT_EL_ID)
    targets['TWO_FA_SELECT'] = Target(cnf.TWO_FA_SELECT_EL_ID)

    return targets


def identify_target(trigger:WebElement, targets:Targets) -> Optional[Target]:
    for target in targets.values():
        try:
            if target.identify(trigger):
                return target
        except TypeError as e:
            # this is raised if trigger doesn't have Target's attribute, we can ignore it
            if "argument of type 'NoneType' is not iterable" in str(e):
                continue
            raise

    raise RuntimeError(f'Trigger found but cannot be identified: {trigger} :: {trigger.get_attribute("outerHTML")}')


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
