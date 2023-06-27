import logging
import time
from pathlib import Path

from ibeam.src.http_handler import Status, HttpHandler
from ibeam.src.process_utils import kill_gateway

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)


def condition_authenticated_true(status:Status) -> bool:
    # unhappy cases, we don't need to keep on retrying
    if not status.running or not status.session:
        return True

    # happy case, wa don't need to keep on retrying
    if status.authenticated:
        return True

    return False

def condition_logged_out(status:Status) -> bool:
    # unhappy cases, we don't need to keep on retrying
    if not status.running or not status.session or status.competing:
        return True

    # happy case, wa don't need to keep on retrying
    if not status.connected and not status.authenticated:
        return True

    return False

def condition_not_competing(status:Status) -> bool:
    # unhappy cases, we don't need to keep on retrying
    if not status.running or not status.session:
        return True

    # happy case, wa don't need to keep on retrying
    if not status.competing and status.connected and status.authenticated:
        return True

    return False

class StrategyHandler():

    def __init__(self,
                 http_handler:HttpHandler,
                 authentication_strategy:str,
                 reauthenticate_wait:int,
                 restart_failed_sessions:bool,
                 restart_wait:int,
                 max_reauthenticate_retries:int,
                 max_status_check_retries:int,
                 gateway_process_match:str,
                 log_in_function:callable
                 ):
        self.http_handler = http_handler
        self.authentication_strategy = authentication_strategy
        self.reauthenticate_wait = reauthenticate_wait
        self.restart_failed_sessions = restart_failed_sessions
        self.restart_wait = restart_wait
        self.max_reauthenticate_retries = max_reauthenticate_retries
        self.max_status_check_retries = max_status_check_retries
        self.gateway_process_match = gateway_process_match
        self.log_in_function = log_in_function

    def try_authenticating(self, request_retries=1) -> (bool, bool, Status):

        status = self.http_handler.get_status(max_attempts=request_retries)
        if status.authenticated and not status.competing:  # running, authenticated and not competing
            return True, False, status

        _LOGGER.info(str(status))

        if not status.running:  # no gateway running
            _LOGGER.error('Cannot communicate with the Gateway. Consider increasing IBEAM_GATEWAY_STARTUP')
            return False, False, status
        else:
            _LOGGER.info(f'Authentication strategy: "{self.authentication_strategy}"')

            if self.authentication_strategy == 'A':
                return self._authentication_strategy_A(status, request_retries)
            elif self.authentication_strategy == 'B':
                return self._authentication_strategy_B(status, request_retries)
            else:
                _LOGGER.error(f'Unknown authentication strategy: "{self.authentication_strategy}". Defaulting to strategy A.')
                return self._authentication_strategy_A(status, request_retries)

    def _authentication_strategy_A(self, status:Status, request_retries=1) -> (bool, bool, Status):
        if status.session:
            if not status.connected or status.competing:
                _LOGGER.info('Competing Gateway session found, restarting and logging in...')
                self._logout()

            _LOGGER.info('Gateway session found but not authenticated, logging in...')
        else:
            _LOGGER.info('No active sessions, logging in...')

        success, shutdown = self.log_in_function()
        _LOGGER.info(f'Logging in {"succeeded" if success else "failed"}')
        if shutdown:
            return False, True, status
        if not success:
            return False, False, status

        time.sleep(3)  # buffer for session to be authenticated

        # double check if authenticated
        status = self.http_handler.get_status(max_attempts=max(request_retries, 2))
        if not status.authenticated:
            if status.session:
                _LOGGER.error('Logging in succeeded, but active session is still not authenticated')
                self.http_handler.reauthenticate()

                if self.reauthenticate_wait > 0:
                    _LOGGER.info(f'Waiting {self.reauthenticate_wait} seconds to reauthenticate before restarting.')
                    time.sleep(self.reauthenticate_wait)

                if self.restart_failed_sessions:
                    _LOGGER.info('Logging out and reattempting full authentication')
                    self._logout()
                    return self.try_authenticating(request_retries=request_retries)
            elif status.running:
                _LOGGER.error('Logging in succeeded but there are still no active sessions')
            else:
                _LOGGER.error('Logging in succeeded but now cannot communicate with the Gateway')
            return False, False, status
        elif not status.connected or status.competing:
            _LOGGER.info('Logging in succeeded, session is authenticated but competing, reauthenticating...')
            self.http_handler.reauthenticate()
            time.sleep(self.restart_wait)
            return False, False, status

        return True, False, status

    def _authentication_strategy_B(self, status:Status, request_retries=1) -> (bool, bool, Status):
        if not status.session:
            _LOGGER.info('No active sessions, logging in...')
            return self._log_in(status)

        elif not status.connected or status.competing:
            _LOGGER.info('Competing or disconnected Gateway session found, logging out and reauthenticating...')
            return self._reauthenticate(status, first_logout=True)
        else:
            _LOGGER.info('Active session found but not authenticated, reauthenticating...')
            return self._reauthenticate(status)

    def _log_in(self, status):
        try:
            success, shutdown = self.log_in_function()
            _LOGGER.info(f'Logging in {"succeeded" if success else "failed"}')

            if not success or shutdown:
                return False, shutdown, status
        except Exception as e:
            _LOGGER.exception(f'Error logging in: {e}')
            return False, False, status

        return self._post_authentication()

    def _reauthenticate(self, status, first_logout=False):
        try:
            if first_logout:
                self._logout()
            self.http_handler.reauthenticate()
        except Exception as e:
            _LOGGER.exception(f'Error reauthenticating: {e}')
            return False, False, status

        return self._post_authentication()
    def _logout(self):
        try:
            logout_response = self.http_handler.logout()
            logout_success = logout_response.read().decode('utf8') == '{"status":true}'
            _LOGGER.info(f'Gateway logout {"successful" if logout_success else "unsuccessful"}')
        except Exception as e:
            _LOGGER.exception(f'Exception logging out: {e}')

    def _post_authentication(self):
        """This method double-checks that the authentication was successful, and if not, reauthenticates"""

        # if we only just logged in and succeeded, this will not reauthenticate but only check status
        status = self._repeatedly_reauthenticate(self.max_reauthenticate_retries, condition_authenticated_true)

        if not status.running or not status.session:
            return False, False, status

        if not status.connected or status.competing or not status.authenticated:
            _LOGGER.error(f'Repeatedly reauthenticating failed {self.max_reauthenticate_retries} times. Killing the Gateway and restarting the authentication process.')

            try:
                success = kill_gateway(self.gateway_process_match)
            except Exception as e:
                _LOGGER.exception(f'Error killing the Gateway: {e}')
                success = False

            if not success:
                _LOGGER.error(f'Killing the Gateway process failed')

            return False, False, status

        return True, False, status


    def _repeatedly_check_status(self, max_attempts=1, condition:callable=condition_authenticated_true):
        if not callable(condition):
            raise ValueError(f'Condition must be a callable, found: "{type(condition)}": {condition}')

        status = None

        for attempt in range(max_attempts):
            status = self.http_handler.get_status()

            if condition(status):
                return status

            if attempt < max_attempts - 1:
                time.sleep(1)
                if attempt == 0:
                    _LOGGER.info(f'Repeating status check attempts another {max_attempts - attempt - 1} times')

        _LOGGER.info(f'Max status check retries reached after {max_attempts} attempts. Consider increasing the retries by setting IBEAM_MAX_STATUS_CHECK_ATTEMPTS environment variable')
        return status

    def _repeatedly_reauthenticate(self, max_attempts=1, condition:callable=condition_authenticated_true):
        if not callable(condition):
            raise ValueError(f'Condition must be a callable, found: "{type(condition)}": {condition}')

        status = None

        for attempt in range(max_attempts):
            status = self._repeatedly_check_status(self.max_status_check_retries, condition)
            _LOGGER.info(str(status))

            if condition(status):
                return status

            if attempt < max_attempts - 1:
                self.http_handler.reauthenticate()
                _LOGGER.info(f'Repeated reauthentication attempt number {attempt + 2}')

        _LOGGER.info(f'Max reauthenticate retries reached after {max_attempts} attempts. Consider increasing the retries by setting IBEAM_MAX_REAUTHENTICATE_RETRIES environment variable')
        return status