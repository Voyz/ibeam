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

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)


class Status():
    def __init__(self,
                 running: bool = False,
                 session: bool = False,
                 authenticated: bool = False
                 ):
        self.running = running
        self.session = session
        self.authenticated = authenticated


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

    def try_request(self, url, check_auth=False, max_attempts=1) -> (bool, bool, bool):
        """Attempts a HTTP request and returns Status object indicating whether the gateway can be reached, whether there is an active session and whether it is authenticated. Attempts to repeat the request up to max_attempts times.

        status.running -> gateway running
        status.session -> active session present
        status.authenticated -> session authenticated (equivalent to 'all good')
        """

        def _request(attempt=0) -> Status:
            status = Status(running=False, session=False, authenticated=False)
            try:
                response = self.url_request(url)
                status.running = True
                status.session = True

                if check_auth:
                    data = json.loads(response.read().decode('utf8'))
                    status.authenticated = data['iserver']['authStatus']['authenticated']
                else:
                    status.authenticated = True

                return status

            except HTTPError as e:
                status.running = True

                if e.code == 401:
                    # we expect this error, no need to log
                    pass

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
                try:
                    raise RuntimeError('Unrecognised Exception') from e
                except Exception as ee:
                    _LOGGER.exception(ee)

            if max_attempts <= 1:
                return status
            else:
                if attempt >= max_attempts - 1:
                    _LOGGER.debug(
                        f'Max validate request retries reached after {max_attempts} attempts. Consider increasing the retries by setting IBEAM_REQUEST_RETRIES environment variable')
                    return status
                else:
                    _LOGGER.debug(f'Attempt number {attempt + 2}')
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
