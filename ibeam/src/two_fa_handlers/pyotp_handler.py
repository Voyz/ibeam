"""
PyOTP 2FA Handler for IBeam - generates codes from a TOTP secret key using 'pyotp' package.

Setup:
  1. Enable TOTP (Mobile Authenticator) in IBKR Account Management
  2. During setup, copy the secret key (base32 string)
  3. Set IBEAM_PYOTP_SECRET=<your-secret-key>

Environment variables:
  IBEAM_PYOTP_SECRET - Base32-encoded TOTP secret key (required)

This file and its guides were contributed by user https://github.com/frequentfliar in https://github.com/Voyz/ibeam/issues/279
"""

import logging
import os
import time
from pathlib import Path

from ibeam.src.two_fa_handlers.two_fa_handler import TwoFaHandler

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)

_EXPIRY_BUFFER_SECONDS = int(os.getenv('IBEAM_PYOTP_EXPIRY_BUFFER_SECONDS', 8))
_MAX_RETRIES = int(os.getenv('IBEAM_PYOTP_MAX_RETRIES', 3))
_RETRY_DELAY_SECONDS = int(os.getenv('IBEAM_PYOTP_RETRY_DELAY_SECONDS', 2))


class PyotpHandler(TwoFaHandler):
    """IBeam custom 2FA handler that generates TOTP codes from a secret key using 'pyotp' package."""

    def __init__(self, outputs_dir):
        try:
            import pyotp
        except ImportError:
            raise ImportError("'pyotp' package not found - must be installed to use this handler")

        super().__init__(outputs_dir)

        self.secret = os.environ.get('IBEAM_PYOTP_SECRET')
        if self.secret is None:
            raise ValueError("IBEAM_PYOTP_SECRET must be set")

        self._totp = pyotp.TOTP(self.secret)
        code = self._totp.now()
        remaining = self._time_remaining()
        _LOGGER.info(f"PyotpHandler initialized - test code ending in {code[-3:]}, expires in {remaining:.0f}s")

    def _time_remaining(self):
        """Seconds until current TOTP code expires."""
        return self._totp.interval - (time.time() % self._totp.interval)

    def _generate_fresh_code(self):
        """Generate a TOTP code, waiting for a fresh period if close to expiry."""
        remaining = self._time_remaining()

        if remaining < _EXPIRY_BUFFER_SECONDS:
            _LOGGER.info(f"TOTP code expires in {remaining:.1f}s (<{_EXPIRY_BUFFER_SECONDS}s buffer), stalling until a fresh code can be generated...")
            time.sleep(remaining + 0.5)

        code = self._totp.now()
        new_remaining = self._time_remaining()
        _LOGGER.info(f"Generated TOTP code ending in {code[-3:]} (valid for {new_remaining:.0f}s)")
        return code

    def get_two_fa_code(self, driver=None):
        """Generate and return the current 6-digit TOTP code."""
        last_error = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                return self._generate_fresh_code()
            except Exception as e:
                last_error = e
                _LOGGER.warning(f"TOTP generation attempt {attempt}/{_MAX_RETRIES} failed: {e}")
                if attempt < _MAX_RETRIES:
                    time.sleep(_RETRY_DELAY_SECONDS)

        raise RuntimeError(f"All {_MAX_RETRIES} TOTP attempts failed: {last_error}")

    def __str__(self):
        status = "ready" if self._totp else "not initialized"
        return f"PyoptHandler(status={status})"