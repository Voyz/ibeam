from types import SimpleNamespace

from ibeam.config import Config
from ibeam.src.login.targets import Target, create_targets
from ibeam.src.var import strip_quotes


def test_target_identify_by_tag():
    target = Target('TAG@@select')
    trigger = SimpleNamespace(tag_name='select')

    assert target.identify(trigger) is True


def test_target_identify_by_placeholder():
    target = Target('PLACEHOLDER@@Code')
    trigger = SimpleNamespace()
    trigger.get_attribute = lambda attr: 'Mobile Authenticator App Code' if attr == 'placeholder' else None

    assert target.identify(trigger) is True


def test_create_targets_uses_select_tag_for_two_fa_select_by_default():
    config = Config({
        'PASSWORD_EL': 'NAME@@password',
        'SUBMIT_EL': 'CSS_SELECTOR@@.btn.btn-lg.btn-primary',
        'SUCCESS_EL_TEXT': 'TAG_NAME@@Client login succeeds',
        'IBKEY_PROMO_EL_CLASS': 'CLASS_NAME@@ibkey-promo-skip',
        'TWO_FA_EL_ID': 'ID@@twofactbase',
        'TWO_FA_NOTIFICATION_EL': 'CLASS_NAME@@login-step-notification',
        'TWO_FA_INPUT_EL_ID': 'ID@@xyz-field-bronze-response',
        'TWO_FA_SELECT': True,
        'TWO_FA_SELECT_EL_ID': 'TAG@@select',
        'LIVE_PAPER_TOGGLE_EL': 'FOR@@label[for=toggle1]',
    })

    targets = create_targets(config)

    assert targets['TWO_FA_SELECT'].by == 'tag name'
    assert targets['TWO_FA_SELECT'].identifier == 'select'


def test_create_targets_skips_two_fa_select_when_disabled():
    config = Config({
        'PASSWORD_EL': 'NAME@@password',
        'SUBMIT_EL': 'CSS_SELECTOR@@.btn.btn-lg.btn-primary',
        'SUCCESS_EL_TEXT': 'TAG_NAME@@Client login succeeds',
        'IBKEY_PROMO_EL_CLASS': 'CLASS_NAME@@ibkey-promo-skip',
        'TWO_FA_EL_ID': 'ID@@twofactbase',
        'TWO_FA_NOTIFICATION_EL': 'CLASS_NAME@@login-step-notification',
        'TWO_FA_INPUT_EL_ID': 'ID@@xyz-field-bronze-response',
        'TWO_FA_SELECT': False,
        'TWO_FA_SELECT_EL_ID': 'TAG@@select',
        'LIVE_PAPER_TOGGLE_EL': 'FOR@@label[for=toggle1]',
    })

    targets = create_targets(config)

    assert 'TWO_FA_SELECT' not in targets


def test_strip_quotes_removes_matching_wrappers():
    assert strip_quotes("'TAG@@select'") == 'TAG@@select'
    assert strip_quotes('"Mobile Authenticator App"') == 'Mobile Authenticator App'
    assert strip_quotes('IB Key') == 'IB Key'


def test_create_targets_includes_two_fa_input_target():
    config = Config({
        'PASSWORD_EL': 'NAME@@password',
        'SUBMIT_EL': 'CSS_SELECTOR@@.btn.btn-lg.btn-primary',
        'SUCCESS_EL_TEXT': 'TAG_NAME@@Client login succeeds',
        'IBKEY_PROMO_EL_CLASS': 'CLASS_NAME@@ibkey-promo-skip',
        'TWO_FA_EL_ID': 'ID@@twofactbase',
        'TWO_FA_NOTIFICATION_EL': 'CLASS_NAME@@login-step-notification',
        'TWO_FA_INPUT_EL_ID': 'ID@@xyz-field-bronze-response',
        'TWO_FA_SELECT': True,
        'TWO_FA_SELECT_EL_ID': 'TAG@@select',
        'LIVE_PAPER_TOGGLE_EL': 'FOR@@label[for=toggle1]',
    })

    targets = create_targets(config)

    assert targets['TWO_FA_INPUT'].identifier == 'xyz-field-bronze-response'
    assert targets['TWO_FA_INPUT_GENERIC'].locator_identifier == 'input[placeholder*="Code"]'
