import os

from ibeam.src.utils.py_utils import strtobool

UNDEFINED = object()


def to_bool(value):
    return bool(strtobool(str(value)))


INPUTS_DIR = os.environ.get('IBEAM_INPUTS_DIR', '/srv/inputs/')
"""Directory path of Inputs Directory."""

OUTPUTS_DIR = os.environ.get('IBEAM_OUTPUTS_DIR',
                             os.path.abspath(
                                 os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', 'outputs')))
"""Directory path of Outputs Directory."""

GATEWAY_DIR = os.environ.get('IBEAM_GATEWAY_DIR', UNDEFINED)
"""Path to the root of the IBKR Gateway."""

CHROME_DRIVER_PATH = os.environ.get('IBEAM_CHROME_DRIVER_PATH', UNDEFINED)
"""Path to the Chrome Driver executable file."""

GATEWAY_STARTUP = int(os.environ.get('IBEAM_GATEWAY_STARTUP', 20))
"""How many seconds to wait for the Gateway to respond after its startup."""

GATEWAY_PROCESS_MATCH = os.environ.get('IBEAM_GATEWAY_PROCESS_MATCH', 'ibgroup.web.core.clientportal.gw.GatewayStart')
"""The gateway process' name to match against."""

MAINTENANCE_INTERVAL = int(os.environ.get('IBEAM_MAINTENANCE_INTERVAL', 60))
"""How many seconds between each maintenance."""

SPAWN_NEW_PROCESSES = to_bool(os.environ.get('IBEAM_SPAWN_NEW_PROCESSES', False))
"""Whether new processes should be spawned for each maintenance."""

LOG_LEVEL = os.environ.get('IBEAM_LOG_LEVEL', 'INFO')
"""Verbosity level of the logger used."""

LOG_TO_FILE = to_bool(os.environ.get('IBEAM_LOG_TO_FILE', True))
"""Whether logs should also be saved to a file."""

LOG_FORMAT = os.environ.get('IBEAM_LOG_FORMAT', '%(asctime)s|%(levelname)-.1s| %(message)s')
"""Log format that is used by IBeam. """

REQUEST_RETRIES = int(os.environ.get('IBEAM_REQUEST_RETRIES', 2))
"""How many times to reattempt a request to the gateway."""

REQUEST_TIMEOUT = int(os.environ.get('IBEAM_REQUEST_TIMEOUT', 15))
"""How many seconds to wait for a request to complete."""

RESTART_FAILED_SESSIONS = to_bool(os.environ.get('IBEAM_RESTART_FAILED_SESSIONS', True))
"""Whether Gateway should be restarted on failed sessions."""

RESTART_WAIT = int(os.environ.get('IBEAM_RESTART_WAIT', 15))
"""How many seconds to wait for a restart to complete."""

REAUTHENTICATE_WAIT = int(os.environ.get('IBEAM_REAUTHENTICATE_WAIT', 15))
"""How many seconds to wait for a reauthentication to complete."""

HEALTH_SERVER_PORT = int(os.environ.get("IBEAM_HEALTH_SERVER_PORT", 5001))
"""Port to start health server on."""

SECRETS_SOURCE = os.environ.get("IBEAM_SECRETS_SOURCE", 'env')
"""Source of secrets."""

GCP_SECRETS_URL = os.environ.get("IBEAM_GCP_SECRETS_URL", None)
"""Base URL for GCP secrets manager."""

START_ACTIVE = to_bool(os.environ.get('IBEAM_START_ACTIVE', True))
"""Whether IBeam should start activated or dormant."""

########### GATEWAY ROUTES ###########

GATEWAY_BASE_URL = os.environ.get('IBEAM_GATEWAY_BASE_URL', "https://localhost:5000")
"""Base URL of the gateway."""

ROUTE_AUTH = os.environ.get('IBEAM_ROUTE_AUTH', '/sso/Login?forwardTo=22&RL=1&ip2loc=on')
"""Gateway route with authentication page."""

ROUTE_VALIDATE = os.environ.get('IBEAM_ROUTE_VALIDATE', '/v1/portal/sso/validate')
"""Gateway route with validation call."""

ROUTE_REAUTHENTICATE = os.environ.get('IBEAM_ROUTE_REAUTHENTICATE', '/v1/portal/iserver/reauthenticate?force=true')
"""Gateway route with reauthentication call."""

ROUTE_INITIALISE = os.environ.get('IBEAM_ROUTE_INITIALISE', '/v1/api/iserver/auth/ssodh/init')
"""Gateway route with session initialisation call."""

ROUTE_AUTH_STATUS = os.environ.get('IBEAM_ROUTE_AUTH_STATUS', '/v1/api/iserver/auth/status')
"""Gateway route with authentication status call."""

ROUTE_TICKLE = os.environ.get('IBEAM_ROUTE_TICKLE', '/v1/api/tickle')
"""Gateway route with tickle call."""

ROUTE_LOGOUT = os.environ.get('IBEAM_ROUTE_LOGOUT', '/v1/api/logout')
"""Gateway route with logout call."""

########### AUTHENTICATION ###########

USER_NAME_EL = os.environ.get('IBEAM_USER_NAME_EL', None)
"""HTML element name attribute containing the username input field."""

PASSWORD_EL = os.environ.get('IBEAM_PASSWORD_EL', 'NAME@@password')
"""HTML element name attribute containing the password input field."""

SUBMIT_EL = os.environ.get('IBEAM_SUBMIT_EL', 'CSS_SELECTOR@@.btn.btn-lg.btn-primary')
"""HTML element name attribute containing the submit button."""

ERROR_EL = os.environ.get('IBEAM_ERROR_EL', None)
"""HTML element class name attribute containing the submit button."""

SUCCESS_EL_TEXT = os.environ.get('IBEAM_SUCCESS_EL_TEXT', 'TAG_NAME@@Client login succeeds')
"""HTML element text indicating successful authentication."""

LIVE_PAPER_TOGGLE_EL = os.environ.get('IBEAM_LIVE_PAPER_TOGGLE_EL', 'FOR@@label[for=toggle1]')
"""HTML element name attribute containing the live paper toggle button."""

USE_PAPER_ACCOUNT = to_bool(os.environ.get('IBEAM_USE_PAPER_ACCOUNT', False))
"""Whether to attempt switching to paper mode before attempting logging in."""

OAUTH_TIMEOUT = int(os.environ.get('IBEAM_OAUTH_TIMEOUT', 15))
"""How many seconds to wait for the OAuth login request to complete."""

PAGE_LOAD_TIMEOUT = int(os.environ.get('IBEAM_PAGE_LOAD_TIMEOUT', 15))
"""How many seconds to wait for the login page to load."""

ERROR_SCREENSHOTS = to_bool(os.environ.get('IBEAM_ERROR_SCREENSHOTS', False))
"""Whether to save login page screenshots on error."""

MAX_FAILED_AUTH = int(os.environ.get('IBEAM_MAX_FAILED_AUTH', 5))
"""Maximum number of failed authentication attempts."""

MIN_PRESUBMIT_BUFFER = int(os.environ.get('IBEAM_MIN_PRESUBMIT_BUFFER', 5))
"""Minimum number of seconds to wait before hitting the submit button"""

MAX_PRESUBMIT_BUFFER = int(os.environ.get('IBEAM_MAX_PRESUBMIT_BUFFER', 30))
"""Maximum number of seconds to wait before hitting the submit button"""

MAX_IMMEDIATE_ATTEMPTS = int(os.environ.get('IBEAM_MAX_IMMEDIATE_ATTEMPTS', 10))
"""Maximum number of immediate retries upon detecting an error message."""

IBKEY_PROMO_EL_CLASS = os.environ.get('IBEAM_IBKEY_PROMO_EL_CLASS', 'CLASS_NAME@@ibkey-promo-skip')
"""HTML element class containing the ibkey promo skip button."""

AUTHENTICATION_STRATEGY = os.environ.get('IBEAM_AUTHENTICATION_STRATEGY', 'B')
"""The authentication strategy used by IBeam."""

MAX_STATUS_CHECK_RETRIES = int(os.environ.get('IBEAM_MAX_STATUS_CHECK_RETRIES', 120))
"""How many times to reattempt the status check."""

MAX_REAUTHENTICATE_RETRIES = int(os.environ.get('IBEAM_MAX_REAUTHENTICATE_RETRIES', 3))
"""How many times to reattempt the reauthentication before restarting the Gateway."""

UI_SCALING = float(os.environ.get('IBEAM_UI_SCALING', 1))
"""The resolution UI scaling to be used by the browser."""

########### TWO-FACTOR AUTHENTICATION ###########

TWO_FA_EL_ID = os.environ.get('IBEAM_TWO_FA_EL_ID', 'ID@@twofactbase')
"""HTML element check for if Gateway will require 2FA code authentication."""

TWO_FA_NOTIFICATION_EL = os.environ.get('IBEAM_TWO_FA_NOTIFICATION_EL', 'CLASS_NAME@@login-step-notification')
"""HTML element check for if Gateway will require 2FA notification authentication."""

TWO_FA_INPUT_EL_ID = os.environ.get('IBEAM_TWO_FA_INPUT_EL_ID', 'ID@@xyz-field-bronze-response')
"""HTML element to input 2FA code into"""

TWO_FA_HANDLER = os.environ.get('IBEAM_TWO_FA_HANDLER', None)
"""Which 2FA handler should be used to acquire the code."""

STRICT_TWO_FA_CODE = to_bool(os.environ.get('IBEAM_STRICT_TWO_FA_CODE', True))
"""Whether to ensure only 2FA code made of 6 digits can be used."""

TWO_FA_SELECT_EL_ID = os.environ.get('IBEAM_TWO_FA_SELECT_EL_ID', 'ID@@xyz-field-bronze-response')
"""HTML element check for if Gateway requires to select the 2FA method."""

TWO_FA_SELECT_TARGET = os.environ.get('IBEAM_TWO_FA_SELECT_TARGET', 'IB Key')
"""Option that is to be chosen in the 2FA select dropdown"""

CUSTOM_TWO_FA_HANDLER = os.environ.get('IBEAM_CUSTOM_TWO_FA_HANDLER', 'custom_two_fa_handler.CustomTwoFaHandler')
"""Fully qualified path of the custom 2FA handler in the inputs directory."""

all_variables = {key: value for key, value in vars().items() if (not key.startswith("__") and key.isupper() and key != 'UNDEFINED')}
