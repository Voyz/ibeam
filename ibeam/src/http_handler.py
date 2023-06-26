import json
import logging
import os
import shutil
import socket
import ssl
from pathlib import Path
from ibeam.src import var
from urllib.error import HTTPError, URLError
import urllib.request
import urllib.parse

from ibeam.src.inputs_handler import InputsHandler
from ibeam.src.py_utils import exception_to_string

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)


class Status():
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

    def __repr__(self):
        d = self.__dict__
        if 'response' in d:
            d.pop('response')
        return f'Status({", ".join([f"{k}={repr(v)}" for k, v in d.items()])})'

    def __str__(self):
        return f'{self.parsed_status} {repr(self)}'
class HttpHandler():

    def __init__(self,
                 inputs_handler: InputsHandler,
                 request_timeout: int = None):

        self.inputs_handler = inputs_handler

        self.request_timeout = request_timeout if request_timeout is not None else var.REQUEST_TIMEOUT
        self.build_ssh_context()

    def build_ssh_context(self):
        self.ssl_context = ssl.SSLContext()
        if self.inputs_handler.valid_certificates:
            self.ssl_context.verify_mode = ssl.CERT_REQUIRED
            self.ssl_context.check_hostname = True
            self.ssl_context.load_verify_locations(self.inputs_handler.cecert_pem_path)

    def url_request(self, url):
        _LOGGER.debug(f'HTTPS{"" if self.inputs_handler.valid_certificates else " (unverified)"} request to: {url}')
        return urllib.request.urlopen(url, context=self.ssl_context, timeout=self.request_timeout)

    def try_request(self, url, max_attempts=1) -> Status:
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
                response = self.url_request(url)
                status.running = True
                status.session = True
                status.response = response

                return status

            except HTTPError as e:
                status.running = True

                if e.code == 401:
                    # the gateway is running but there is no active session
                    pass

                elif e.code == 500 and 'Internal Server Error' in str(e):
                    _LOGGER.error(f'IBKR server error: "{e}". One of reasons for this error is IBKR server restart.')
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
                # try:
                #     raise RuntimeError('Unrecognised Exception') from e
                # except Exception as ee:
                #     _LOGGER.exception(ee)

            if max_attempts <= 1:
                return status
            else:
                if attempt >= max_attempts - 1:
                    _LOGGER.info(
                        f'Max validate request retries reached after {max_attempts} attempts. Consider increasing the retries by setting IBEAM_REQUEST_RETRIES environment variable')
                    return status
                else:
                    _LOGGER.info(f'Attempt number {attempt + 2}')
                    return _request(attempt + 1)

        return _request(0)

    def __getstate__(self):
        state = self.__dict__.copy()
        # ssl_context can't be pickled
        del state['ssl_context']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.build_ssh_context()
