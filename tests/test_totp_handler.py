import os
import unittest
from unittest.mock import patch

import pyotp

from ibeam.src.two_fa_handlers.totp_handler import TotpTwoFaHandler


class TestTotpTwoFaHandler(unittest.TestCase):
    """Test cases for the TOTP Two-Factor Authentication Handler."""

    # Test secret from pyotp documentation (base32 encoded)
    TEST_SECRET = "JBSWY3DPEHPK3PXP"

    def setUp(self):
        """Set up test environment before each test."""
        # Save original environment variable if it exists
        self.original_secret = os.environ.get('IBEAM_TOTP_SECRET')
        
        # Set test environment variable
        os.environ['IBEAM_TOTP_SECRET'] = self.TEST_SECRET

    def tearDown(self):
        """Clean up test environment after each test."""
        # Restore original environment variable
        if self.original_secret:
            os.environ['IBEAM_TOTP_SECRET'] = self.original_secret
        else:
            if 'IBEAM_TOTP_SECRET' in os.environ:
                del os.environ['IBEAM_TOTP_SECRET']

    def test_initialization(self):
        """Test that the handler initializes correctly with a valid secret."""
        handler = TotpTwoFaHandler(outputs_dir="/tmp", totp_secret=self.TEST_SECRET)
        self.assertIsNotNone(handler)
        self.assertEqual(str(handler), "TotpTwoFaHandler(Automated TOTP Code Generator)")

    def test_get_two_fa_code(self):
        """Test that the handler generates a valid TOTP code."""
        handler = TotpTwoFaHandler(outputs_dir="/tmp", totp_secret=self.TEST_SECRET)
        code = handler.get_two_fa_code(None)
        
        # Verify the code is a 6-digit string
        self.assertIsNotNone(code)
        self.assertTrue(code.isdigit())
        self.assertEqual(len(code), 6)
        
        # Verify the code matches what pyotp would generate directly
        expected_code = pyotp.TOTP(self.TEST_SECRET).now()
        self.assertEqual(code, expected_code)

    def test_missing_secret(self):
        """Test that the handler raises an error when the secret is missing."""
        # Remove the environment variable
        del os.environ['IBEAM_TOTP_SECRET']
        
        # Verify that initialization fails
        with self.assertRaises(ValueError) as context:
            TotpTwoFaHandler(outputs_dir="/tmp")
        
        self.assertIn("IBEAM_TOTP_SECRET environment variable is required", str(context.exception))

    def test_invalid_secret(self):
        """Test that the handler raises an error when the secret is invalid."""
        # Set an invalid secret
        os.environ['IBEAM_TOTP_SECRET'] = "INVALID!SECRET"
        
        # Verify that initialization fails
        with self.assertRaises(ValueError) as context:
            TotpTwoFaHandler(outputs_dir="/tmp")
        
        self.assertIn("Invalid TOTP secret", str(context.exception))

    @patch('logging.Logger.info')
    def test_logging(self, mock_info):
        """Test that the handler logs appropriately."""
        handler = TotpTwoFaHandler(outputs_dir="/tmp", totp_secret=self.TEST_SECRET)
        code = handler.get_two_fa_code(None)
        
        # Verify that the handler logs the code generation (without exposing the full code)
        mock_info.assert_any_call(f"Generated TOTP code successfully (last digits: ...{code[-2:]})")


if __name__ == '__main__':
    unittest.main()