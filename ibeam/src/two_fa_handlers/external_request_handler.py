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
"""URL to use by the external request 2FA handler."""

_EXTERNAL_REQUEST_PARAMS = os.environ.get('IBEAM_EXTERNAL_REQUEST_PARAMS')
"""Params to use by the external request 2FA handler."""

_EXTERNAL_REQUEST_HEADERS = os.environ.get('IBEAM_EXTERNAL_REQUEST_HEADERS')
"""Headers to use by the external request 2FA handler."""


def parse_json(s):
    if s is None:
        return None
    try:
        return json.loads(s)
    except Exception as e:
        _LOGGER.exception(e)
        return None


class ExternalRequestTwoFaHandler(TwoFaHandler):

    def __init__(self, method: str = None,
                 url: str = None,
                 timeout: int = None,
                 params=None,
                 headers=None):

        self.method = method if method is not None else _EXTERNAL_REQUEST_METHOD
        self.url = url if url is not None else _EXTERNAL_REQUEST_URL
        self.timeout = timeout if timeout is not None else _EXTERNAL_REQUEST_TIMEOUT
        self.params = params if params is not None else parse_json(_EXTERNAL_REQUEST_PARAMS)
        self.headers = headers if headers is not None else parse_json(_EXTERNAL_REQUEST_HEADERS)

    def get_two_fa_code(self) -> Union[str, None]:
        try:
            response = requests.request(method=self.method,
                                        url=self.url,
                                        timeout=self.timeout,
                                        params=self.params,
                                        headers=self.headers, )
            response.raise_for_status()
            return response.content
        except requests.exceptions.HTTPError as err:
            _LOGGER.error(err)
            return None

    def __str__(self):
        return f"ExternalRequestTwoFaHandler(method={self.method}, url={self.url}, timeout={self.timeout}, params={self.params}, headers={self.headers})"
