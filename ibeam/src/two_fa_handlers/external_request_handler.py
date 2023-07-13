import json
import logging
import os
from pathlib import Path
from typing import Union

import requests

from ibeam.src.two_fa_handlers.two_fa_handler import TwoFaHandler

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)

_EXTERNAL_REQUEST_METHOD = os.environ.get('IBEAM_EXTERNAL_REQUEST_METHOD', 'GET')
"""Method to use by the external request 2FA handler."""

_EXTERNAL_REQUEST_URL = os.environ.get('IBEAM_EXTERNAL_REQUEST_URL')
"""URL to use by the external request 2FA handler."""

_EXTERNAL_REQUEST_TIMEOUT = int(os.environ.get('IBEAM_EXTERNAL_REQUEST_TIMEOUT', 300))
"""Timeout for the external 2FA request."""

_EXTERNAL_REQUEST_PARAMS = os.environ.get('IBEAM_EXTERNAL_REQUEST_PARAMS')
"""JSON-formatted URL params to use by the external request 2FA handler."""

_EXTERNAL_REQUEST_DATA = os.environ.get('IBEAM_EXTERNAL_REQUEST_DATA')
"""JSON-formatted POST data to use by the external request 2FA handler."""

_EXTERNAL_REQUEST_HEADERS = os.environ.get('IBEAM_EXTERNAL_REQUEST_HEADERS')
"""JSON-formatted headers to use by the external request 2FA handler."""


def parse_json(s):
    if s is None:
        return None
    try:
        return json.loads(s)
    except Exception as e:
        _LOGGER.exception(f'Error loading JSON string: "{e}" | for JSON: {s}')
        return None


class ExternalRequestTwoFaHandler(TwoFaHandler):

    def __init__(self, method: str = None,
                 url: str = None,
                 timeout: int = None,
                 params=None,
                 data=None,
                 headers=None,
                 *args, **kwargs
                 ):

        self.method = method if method is not None else _EXTERNAL_REQUEST_METHOD
        self.url = url if url is not None else _EXTERNAL_REQUEST_URL
        self.timeout = timeout if timeout is not None else _EXTERNAL_REQUEST_TIMEOUT
        self.params = params if params is not None else parse_json(_EXTERNAL_REQUEST_PARAMS)
        self.data = data if data is not None else parse_json(_EXTERNAL_REQUEST_DATA)
        self.headers = headers if headers is not None else parse_json(_EXTERNAL_REQUEST_HEADERS)
        super().__init__(*args, **kwargs)

    def get_two_fa_code(self, _) -> Union[str, None]:
        try:
            response = requests.request(method=self.method,
                                        url=self.url,
                                        timeout=self.timeout,
                                        params=self.params,
                                        data=self.data,
                                        headers=self.headers, )
            response.raise_for_status()
            return response.content.decode("utf-8")
        except requests.exceptions.HTTPError as err:
            _LOGGER.error(err)
            return None

    def __str__(self):
        return f"ExternalRequestTwoFaHandler(method={self.method}, url={self.url}, timeout={self.timeout}, params={self.params}, headers={self.headers})"
