import logging
from pathlib import Path
from typing import Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from ibeam.src import var

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


def create_targets(versions: dict) -> Targets:
    targets = {}

    targets['USER_NAME'] = Target(versions['USER_NAME_EL'])
    targets['PASSWORD'] = Target(var.PASSWORD_EL)
    targets['SUBMIT'] = Target(var.SUBMIT_EL)
    targets['ERROR'] = Target(versions['ERROR_EL'])
    targets['SUCCESS'] = Target(var.SUCCESS_EL_TEXT)
    targets['IBKEY_PROMO'] = Target(var.IBKEY_PROMO_EL_CLASS)
    targets['TWO_FA'] = Target(var.TWO_FA_EL_ID)
    targets['TWO_FA_NOTIFICATION'] = Target(var.TWO_FA_NOTIFICATION_EL)
    targets['TWO_FA_INPUT'] = Target(var.TWO_FA_INPUT_EL_ID)
    targets['TWO_FA_SELECT'] = Target(var.TWO_FA_SELECT_EL_ID)

    if var.USER_NAME_EL is not None and var.USER_NAME_EL != targets['USER_NAME'].variable:
        _LOGGER.warning(f'USER_NAME target is forced to "{var.USER_NAME_EL}", contrary to the element found on the website: "{targets["USER_NAME"]}"')
        targets['USER_NAME'] = Target(var.USER_NAME_EL)

    if var.ERROR_EL is not None and var.ERROR_EL != targets['ERROR'].variable:
        _LOGGER.warning(f'ERROR target is forced to "{var.ERROR_EL}", contrary to the element found on the website: "{targets["ERROR"]}"')
        targets['ERROR'] = Target(var.ERROR_EL)

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
