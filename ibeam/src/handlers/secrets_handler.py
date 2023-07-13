import logging
import os
from pathlib import Path
from typing import Optional



_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)

SECRETS_SOURCE_ENV = 'env'
SECRETS_SOURCE_FS = 'fs'

"""If IBEAM_SECRETS_SOURCE is set to
SECRETS_SOURCE_ENV, or if it is not set, then
environment values will be assumed to hold the
secret values directly.

If IBEAM_SECRETS_SOURCE is set to SECRETS_SOURCE_FS
then the environment values are assumed to be file
paths to read for the secret value."""

class SecretsHandler():
    ...
    def __init__(self, secrets_source):
        self.secrets_source = secrets_source

        """Character encoding for secret files"""
        self.encoding = os.environ.get(
            'IBEAM_ENCODING', default='UTF-8')

    def secret_value(self, encoding, name: str,
                     lstrip=None, rstrip='\r\n') -> Optional[str]:
        """
        secret_value reads secrets from os.environ or from
        the filesystem.

        Given a name, such as 'IBEAM_ACCOUNT', it will
        examine os.environ for a value associated with that
        name.

        If no value has been set, None is returned.
        Otherwise the self.secrets_source will be evaluated
        to determine how to handle the value.

        If self.secrets_source has been set to
        SECRETS_SOURCE_ENV the os.environ value will be
        returned as the secret value.

        If self.secrets_source has been set to
        SECRETS_SOURCE_FS then the os.environ value is
        treated as a filesystem path.  The file will be read
        as text and its contents returned as the secret
        value.

        Parameters:
          name:
            The identifier for the value, e.g.,
            'IBEAM_ACCOUNT', 'IBEAM_PASSWORD', or
            'IBEAM_KEY'.
          lstrip:
            If not None, strip these characters from the
            left of the returned value (default: None).
          rstrip:
            If not None, strip these characters from the
            right of the returned value (default: '\r\n')
        Returns:
          If the name is not defined in os.environ then None
          is returned.

          If self.secrets_source is SECRETS_SOURCE_ENV then
          the os.environ value is returned as the secret
          value.

          If self.secrets_source is SECRETS_SOURCE_FS then
          the os.environ value is treated as file path.  The
          file is read as a text file and its contents
          returned as the secret value.

          If an error is encountered reading the file then
          an error is logged and None is returned.
        """
        # read the environment value for name
        value = os.environ.get(name)
        if value is None:
            # no key for this name, nothing to do
            return None

        if self.secrets_source == SECRETS_SOURCE_ENV:
            # treat environment values as the secrets themselves
            if lstrip is not None:
                value = value.lstrip(lstrip)

            if rstrip is not None:
                value = value.rstrip(rstrip)

            return value
        elif self.secrets_source == SECRETS_SOURCE_FS:
            # treat environment values as filesystem paths to the secrets
            if not os.path.isfile(value):
                _LOGGER.error(
                    f'Unable to read env value for {name}: value is not a file')
                return None

            try:
                with open(value, mode='rt', encoding=encoding) as fh:
                    secret = fh.read()

                    if lstrip is not None:
                        secret = secret.lstrip(lstrip)

                    if rstrip is not None:
                        secret = secret.rstrip(rstrip)

                    return secret
            except IOError:
                _LOGGER.error(
                    f'Unable to read env value for {name} as a file.')
                return None
        else:
            _LOGGER.error(
                f'Unknown Secrets Source: {self.secrets_source}')
            return None


    @property
    def account(self):
        """IBKR account name."""
        return self.secret_value(self.encoding, 'IBEAM_ACCOUNT')

    @property
    def password(self):
        """IBKR account password."""
        return self.secret_value(self.encoding, 'IBEAM_PASSWORD')

    @property
    def key(self):
        """Key to the IBKR password."""
        return self.secret_value(self.encoding, 'IBEAM_KEY')