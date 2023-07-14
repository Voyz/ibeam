from typing import Union

from selenium.common import StaleElementReferenceException, WebDriverException
from selenium.webdriver.remote.webelement import WebElement


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
                element = driver.find_element(*locator)
                if self.text in element.text:
                    return element
            except StaleElementReferenceException:
                continue
        return False


def any_of(*expected_conditions):
    """ An expectation that any of multiple expected conditions is true.
    Equivalent to a logical 'OR'.
    Returns results of the first matching condition, or False if none do. """

    def any_of_condition(driver) -> Union[WebElement, bool]:
        for expected_condition in expected_conditions:
            try:
                result = expected_condition(driver)
                if result:
                    return result
            except WebDriverException:
                pass
        return False

    return any_of_condition
