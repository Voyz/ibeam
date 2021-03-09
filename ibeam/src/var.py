import os

INPUTS_DIR = os.environ.get('IBEAM_INPUTS_DIR', '/srv/inputs/')
"""Directory path of Inputs Directory."""

OUTPUTS_DIR = os.environ.get('IBEAM_OUTPUTS_DIR',
                             os.path.abspath(
                                 os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', 'outputs')))
"""Directory path of Outputs Directory."""

GATEWAY_DIR = os.environ.get('IBEAM_GATEWAY_DIR')
"""Path to the root of the IBKR Gateway."""

CHROME_DRIVER_PATH = os.environ.get('IBEAM_CHROME_DRIVER_PATH')
"""Path to the Chrome Driver executable file."""

GATEWAY_STARTUP = int(os.environ.get('IBEAM_GATEWAY_STARTUP', 20))
"""How many seconds to wait for the Gateway to respond after its startup."""

GATEWAY_PROCESS_MATCH = os.environ.get('IBEAM_GATEWAY_PROCESS_MATCH', 'ibgroup.web.core.clientportal.gw.GatewayStart')
"""The gateway process' name to match against."""

MAINTENANCE_INTERVAL = int(os.environ.get('IBEAM_MAINTENANCE_INTERVAL', 60))
"""How many seconds between each maintenance."""

LOG_LEVEL = os.environ.get('IBEAM_LOG_LEVEL', 'INFO')
"""Verbosity level of the logger used."""

REQUEST_RETRIES = int(os.environ.get('IBEAM_REQUEST_RETRIES', 1))
"""How many times to reattempt a request to the gateway."""

REQUEST_TIMEOUT = int(os.environ.get('IBEAM_REQUEST_TIMEOUT', 15))
"""How many seconds to wait for a request to complete."""

########### GATEWAY ROUTES ###########

GATEWAY_BASE_URL = os.environ.get('IBEAM_GATEWAY_BASE_URL', "https://localhost:5000")
"""Base URL of the gateway."""

ROUTE_AUTH = os.environ.get('IBEAM_ROUTE_AUTH', '/sso/Login?forwardTo=22&RL=1&ip2loc=on')
"""Gateway route with authentication page."""

ROUTE_USER = os.environ.get('IBEAM_ROUTE_USER', '/v1/api/one/user')
"""Gateway route with user information."""

ROUTE_VALIDATE = os.environ.get('IBEAM_ROUTE_VALIDATE', '/v1/portal/sso/validate')
"""Gateway route with validation call."""

ROUTE_REAUTHENTICATE = os.environ.get('IBEAM_ROUTE_REAUTHENTICATE', '/v1/portal/iserver/reauthenticate?force=true')
"""Gateway route with reauthentication call."""

ROUTE_AUTH_STATUS = os.environ.get('IBEAM_ROUTE_AUTH_STATUS', '/v1/api/iserver/auth/status')
"""Gateway route with authentication status call."""

ROUTE_TICKLE = os.environ.get('IBEAM_ROUTE_TICKLE', '/v1/api/tickle')
"""Gateway route with tickle call."""

########### AUTHENTICATION ###########

USER_NAME_EL_ID = os.environ.get('IBEAM_USER_NAME_EL_ID', 'user_name')
"""HTML element id containing the username input field."""

PASSWORD_EL_ID = os.environ.get('IBEAM_PASSWORD_EL_ID', 'password')
"""HTML element id containing the password input field."""

SUBMIT_EL_ID = os.environ.get('IBEAM_SUBMIT_EL_ID', 'submitForm')
"""HTML element id containing the submit button."""

ERROR_EL_ID = os.environ.get('IBEAM_ERROR_EL_ID', 'ERRORMSG')
"""HTML element id containing the submit button."""

SUCCESS_EL_TEXT = os.environ.get('IBEAM_SUCCESS_EL_TEXT', 'Client login succeeds')
"""HTML element text indicating successful authentication."""

OAUTH_TIMEOUT = int(os.environ.get('IBEAM_OAUTH_TIMEOUT', 15))
"""How many seconds to wait for the OAuth login request to complete."""

ERROR_SCREENSHOTS = bool(os.environ.get('IBEAM_ERROR_SCREENSHOTS', False))
"""Whether to save login page screenshots on error."""

MAX_FAILED_AUTH = int(os.environ.get('IBEAM_MAX_FAILED_AUTH', 5))
"""Maximum number of failed authentication attempts."""

########### TWO-FACTOR AUTHENTICATION ###########

TWO_FA_EL_ID = os.environ.get('IBEAM_TWO_FA_EL_ID', 'twofactbase')
"""HTML element check for if Gateway will require 2FA authentication."""

TWO_FA_INPUT_EL_ID = os.environ.get('TWO_FA_INPUT_EL_ID', 'chlginput')
"""HTML element to input 2FA code into"""

TWO_FA_HANDLER = os.environ.get('IBEAM_TWO_FA_HANDLER', None)
"""Which 2FA handler should be used to acquire the code."""

STRICT_TWO_FA_CODE = bool(os.environ.get('IBEAM_STRICT_TWO_FA_CODE', True))
"""Whether to ensure only 2FA code made of 6 digits can be used."""

all_variables = {item: value for item, value in vars().items() if (not item.startswith("__") and item.isupper())}
