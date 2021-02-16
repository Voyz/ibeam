import os

IBEAM_INPUTS_DIR = os.environ.get('IBEAM_INPUTS_DIR', '/srv/inputs/')
"""Directory path of Inputs Directory."""

IBEAM_GATEWAY_DIR = os.environ.get('IBEAM_GATEWAY_DIR')
"""Path to the root of the IBKR Gateway."""

IBEAM_CHROME_DRIVER_PATH = os.environ.get('IBEAM_CHROME_DRIVER_PATH')
"""Path to the Chrome Driver executable file."""

GATEWAY_STARTUP = int(os.environ.get('IBEAM_GATEWAY_STARTUP', 3))
"""How many seconds to wait before attempting to communicate with the gateway after its startup."""

GATEWAY_BASE_URL = os.environ.get('IBEAM_GATEWAY_BASE_URL', "https://localhost:5000")
"""Base URL of the gateway."""

GATEWAY_PROCESS_MATCH = os.environ.get('IBEAM_GATEWAY_PROCESS_MATCH', 'ibgroup.web.core.clientportal.gw.GatewayStart')
"""The gateway process' name to match against."""

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

USER_NAME_EL_ID = os.environ.get('IBEAM_USER_NAME_EL_ID', 'user_name')
"""HTML element id containing the username input field."""

PASSWORD_EL_ID = os.environ.get('IBEAM_PASSWORD_EL_ID', 'password')
"""HTML element id containing the password input field."""

SUBMIT_EL_ID = os.environ.get('IBEAM_SUBMIT_EL_ID', 'submitForm')
"""HTML element id containing the submit button."""

SUCCESS_EL_TEXT = os.environ.get('IBEAM_SUCCESS_EL_TEXT', 'Client login succeeds')
"""HTML element text indicating successful authentication."""

TWO_FAC_EL_ID = os.environ.get('IBEAM_TWO_FAC_EL_ID', 'chlginput')
"""HTML element indicating 2FA authentication."""

SMS_QR_CODE_CLASS = os.environ.get('IBEAM_SMS_QR_CODE_CLASS', 'qr-code')
"""HTML element indicating web messages needs authorization."""

SMS_AUTH_REMEMBER_CLASS = os.environ.get('IBEAM_SMS_AUTH_REMEMBER_CLASS', 'local-storage-checkbox')
"""HTML element to remember web messages device pairing."""

SMS_MESSAGES_LIST_CLASS = os.environ.get('IBEAM_SMS_MESSAGES_LIST_CLASS', 'snippet-text')
"""HTML element indicating web messages has loaded."""

SMS_2FA_HEADING = os.environ.get('IBEAM_SMS_2FA_HEADING', 'Your requested authentication code')
"""HTML element text indicating 2fa message received."""

MAINTENANCE_INTERVAL = int(os.environ.get('IBEAM_MAINTENANCE_INTERVAL', 60))
"""How many seconds between each maintenance."""

LOG_LEVEL = os.environ.get('IBEAM_LOG_LEVEL', 'INFO')
"""Verbosity level of the logger used."""

REQUEST_RETRIES = int(os.environ.get('IBEAM_REQUEST_RETRIES', 1))
"""How many times to reattempt a request to the gateway."""

REQUEST_TIMEOUT = int(os.environ.get('IBEAM_REQUEST_TIMEOUT', 15))
"""How many seconds to wait for a request to complete."""

OAUTH_TIMEOUT = int(os.environ.get('IBEAM_OAUTH_TIMEOUT', 15))
"""How many seconds to wait for the OAuth login request to complete."""
