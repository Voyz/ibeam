import json
import logging
import socket
import ssl
from pathlib import Path
from urllib import request

from urllib.error import HTTPError, URLError
import urllib.request
import urllib.parse

from ibeam.src.handlers.inputs_handler import InputsHandler
from ibeam.src.utils.py_utils import exception_to_string

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)


class Status():
    """
    A class to represent the status of the Gateway and our connection to IBKR servers.

    Attributes:
        running (bool): Whether the Gateway is running.
        session (bool): Whether there is an active session.
        response (dict): The server response to the request.
        connected (bool): Whether the server reports 'connected' to the Gateway.
        authenticated (bool): Whether the session is authenticated.
        competing (bool): Whether there are competing sessions on the server.
        collision (bool): Currently no idea what this flag means.
        session_id (str): The ID of the current session, if one exists.
        server_name (str): The name of the server.
        server_version (str): The version of the server.
        expires (int): The expiration time of the current session, represented as milliseconds.

    """
    def __init__(self,
                 running: bool = False,
                 session: bool = False,
                 response = None,

                 # parsed args
                 connected: bool = False,
                 authenticated: bool = False,
                 competing: bool = False,
                 collision: bool = False,
                 session_id: str = None,
                 server_name: str = None,
                 server_version: str = None,
                 expires: int = None,
                 ):
        self.running = running
        self.session = session
        self.response = response

        # parsed args
        self.connected = connected
        self.authenticated = authenticated
        self.competing = competing
        self.collision = collision
        self.session_id = session_id
        self.server_name = server_name
        self.server_version = server_version
        self.expires = expires

    def expiration_time(self):
        if self.expires is None:
            return None

        return f'{int(self.expires / 1000)} seconds'

    @property
    def parsed_status(self):
        if not self.running:
            return 'NOT RUNNING'
        if not self.session:
            return 'NO SESSION'
        if not self.connected:
            return 'NOT CONNECTED'
        if self.competing:
            return 'COMPETING'
        if self.collision:
            return 'COLLISION'
        if self.authenticated:
            return 'AUTHENTICATED'

        return 'NOT AUTHENTICATED'

    def __repr__(self):
        d = self.__dict__.copy()
        if 'response' in d:
            d.pop('response')
        return f'Status({", ".join([f"{k}={repr(v)}" for k, v in d.items()])})'

    def __str__(self):
        return f'{self.parsed_status} {repr(self)}'
class HttpHandler():

    def __init__(self,
                 inputs_handler: InputsHandler,
                 base_url:str,
                 route_validate: str,
                 route_tickle: str,
                 route_logout: str,
                 route_reauthenticate: str,
                 route_initialise: str,
                 request_timeout: int,
                 ):

        self.inputs_handler = inputs_handler
        self.base_url = base_url

        self.route_validate = route_validate
        self.route_tickle = route_tickle
        self.route_logout = route_logout
        self.route_reauthenticate = route_reauthenticate
        self.route_initialise = route_initialise
        self.request_timeout = request_timeout
        self.build_ssh_context()

    def build_ssh_context(self):
        self.ssl_context = ssl.SSLContext()
        if self.inputs_handler.valid_certificates:
            self.ssl_context.verify_mode = ssl.CERT_REQUIRED
            self.ssl_context.check_hostname = True
            self.ssl_context.load_verify_locations(self.inputs_handler.cacert_pem_path)

    def url_request(self, url, method='GET'):
        _LOGGER.debug(f'{method} {url}{"" if self.inputs_handler.valid_certificates else " (unverified)"}')
        req = request.Request(url, method=method)
        return urllib.request.urlopen(req, context=self.ssl_context, timeout=self.request_timeout)

    def try_request(self, url, method='GET', max_attempts=1) -> Status:
        """Attempts a HTTP request and returns Status object indicating whether the gateway can be reached, whether there is an active session and whether it is authenticated. Attempts to repeat the request up to max_attempts times.

        status.running -> gateway running
        status.session -> active session present
        status.authenticated -> session authenticated (equivalent to 'all good')
        status.competing -> session competing
        """

        def _request(attempt=0) -> Status:
            status = Status()
            try:
                # if this doesn't throw an exception, the gateway is running and there is an active session
                response = self.url_request(url, method=method)
                status.running = True
                status.response = response.read().decode('utf8')

                if status.response == '{"error":"no session"}':
                    _LOGGER.error(f'Error: "no session" returned.')
                    status.session = False
                else:
                    status.session = True

                return status

            except HTTPError as e:
                status.running = True

                if e.code == 401:
                    # the gateway is running but there is no active session
                    pass

                elif e.code == 500 and 'Internal Server Error' in str(e):
                    _LOGGER.error(f'IBKR server error: "{e}". One of reasons for this error is IBKR server restart.')
                    status.session = False  # ensure we reauthenticate


                elif e.code == 503 and 'Service Unavailable' in str(e):
                    _LOGGER.error(f'IBKR service unavailable: "{e}". It seems IBKR servers are not ready to handle requests. We may need to wait until the servers are ready.')
                    status.session = False  # ensure we reauthenticate

                else:  # todo: possibly other codes could appear when not authenticated, fix when necessary
                    try:
                        raise RuntimeError('Unrecognised HTTPError') from e
                    except Exception as ee:
                        _LOGGER.exception(ee)

            except (URLError, socket.timeout) as e:
                reason = str(e)

                """
                    No connection... - happens when port isn't open
                    Cannot assign... - happens when calling a port taken by Docker but not served, when called from within the container.
                    Errno 0... - happens when calling a port taken by Docker but not served, when called from the host machine.
                """

                if 'No connection could be made because the target machine actively refused it' in reason \
                        or 'Cannot assign requested address' in reason \
                        or '[Errno 0] Error' in reason:
                    pass  # we expect these errors and don't need to log them

                elif "timed out" in reason \
                        or "The read operation timed out" in reason:
                    #TODO: this will cause full relogin, we probably only need to repeat the request
                    _LOGGER.error(
                        f'Connection timeout after {self.request_timeout} seconds. Consider increasing timeout by setting IBEAM_REQUEST_TIMEOUT environment variable. Error: {reason}')
                    status.running = True

                elif 'Connection refused' in reason:
                    _LOGGER.info(
                        f'Gateway running but not serving yet. Consider increasing IBEAM_GATEWAY_STARTUP timeout. Error: {reason}')
                    status.running = True

                elif 'An existing connection was forcibly closed by the remote host' in reason:
                    _LOGGER.error(
                        'Connection to Gateway was forcibly closed by the remote host. This means something is closing the Gateway process.')

                elif 'certificate verify failed: self signed certificate' in reason:
                    _LOGGER.error(
                        'Failed to verify the self-signed certificate. This could mean your self-generated .jks certificate and password are not correctly provided in Inputs Directory or listed in conf.yaml. Ensure your certificate\'s filename and password are correctly listed in conf.yaml, or see https://github.com/Voyz/ibeam/wiki/TLS-Certificates-and-HTTPS#certificates-in-confyaml for more information.')

                else:
                    try:
                        raise RuntimeError('Unrecognised URLError or socket.timeout') from e
                    except Exception as ee:
                        _LOGGER.exception(ee)
                    status.running = True

            except ConnectionResetError as e:
                if 'An existing connection was forcibly closed by the remote host' in str(e):
                    _LOGGER.error(
                        'Connection to Gateway was forcibly closed by the remote host. This means something is closing the Gateway process.')
                else:
                    try:
                        raise RuntimeError('Unrecognised ConnectionResetError') from e
                    except Exception as ee:
                        _LOGGER.exception(ee)

            except Exception as e:  # all other exceptions
                _LOGGER.exception(f'Unrecognised Exception:\n{exception_to_string(e)}')

            if max_attempts <= 1:
                return status
            else:
                if attempt >= max_attempts - 1:
                    _LOGGER.info(
                        f'Max request retries reached after {max_attempts} attempts. Consider increasing the retries by setting IBEAM_REQUEST_RETRIES environment variable')
                    return status
                else:
                    _LOGGER.info(f'Attempt number {attempt + 2}')
                    return _request(attempt + 1)

        return _request(0)

    def get_status(self, max_attempts=1) -> Status:
        """We use tickle instead of iserver/auth/status because it is more versatile."""
        status = self.tickle(max_attempts=max_attempts)

        if status.session:
            json_response = json.loads(status.response)

            status.authenticated = json_response['iserver']['authStatus']['authenticated']
            status.competing = json_response['iserver']['authStatus']['competing']
            status.connected = json_response['iserver']['authStatus']['connected']
            status.collision = json_response['collission']
            status.session_id = json_response['session']
            status.expires = int(json_response['ssoExpires'])

            # some fields are not present if unauthenticated
            status.server_name = json_response['iserver']['authStatus'].get('serverInfo', {}).get('serverName')
            status.server_version = json_response['iserver']['authStatus'].get('serverInfo', {}).get('serverVersion')

        return status

    def validate(self) -> bool:
        """Validate provides information on the current session. Works also after logout."""
        status = self.try_request(self.base_url + self.route_validate, 'GET')
        if status.session:
            return json.loads(status.response)['RESULT']
        return False

    def tickle(self, max_attempts=1) -> Status:
        return self.try_request(self.base_url + self.route_tickle, 'POST', max_attempts=max_attempts)

    def logout(self):
        """Logout will log the user out, but maintain the session, allowing us to reauthenticate directly."""
        return self.url_request(self.base_url + self.route_logout, 'POST')

    def reauthenticate(self):
        """Reauthenticate will work only if there is an existing session."""
        return self.url_request(self.base_url + self.route_reauthenticate, 'POST')

    def initialise(self):
        """Initialise the session."""
        return self.url_request(self.base_url + self.route_initialise, 'POST')

    def base_route(self):
        """Call base base_url"""
        return self.try_request(self.base_url)


    def __getstate__(self):
        state = self.__dict__.copy()
        # ssl_context can't be pickled
        del state['ssl_context']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.build_ssh_context()
