import logging
import os
from pathlib import Path
from typing import Optional

import pyotp
from selenium import webdriver

from ibeam.src.two_fa_handlers.two_fa_handler import TwoFaHandler

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)

"""TOTP secret key used to generate time-based one-time passwords."""


class TotpTwoFaHandler(TwoFaHandler):
    """
    A 2FA handler that generates TOTP codes automatically.
    
    This handler uses the pyotp library to generate Time-based One-Time Passwords
    based on a secret key stored in the IBEAM_TOTP_SECRET environment variable.
    
    To use this handler:
    1. Set IBEAM_TWO_FA_HANDLER=TOTP
    2. Set IBEAM_TOTP_SECRET to your TOTP secret key
    """

    def __init__(self, outputs_dir=None, totp_secret=None):
        """
        Initialize the TOTP 2FA handler.
        
        Args:
            outputs_dir: Directory where IBeam stores output files
            totp_secret: Optional TOTP secret for testing purposes
        """
        super().__init__(outputs_dir=outputs_dir)
        
        # Get the TOTP secret from parameter or environment variable
        totp_secret = totp_secret or os.environ.get('IBEAM_TOTP_SECRET')
        
        # Check if TOTP secret is set
        if not totp_secret:
            _LOGGER.error("IBEAM_TOTP_SECRET environment variable is not set")
            raise ValueError("IBEAM_TOTP_SECRET environment variable is required for TOTP authentication")
        
        # Validate that the secret is a valid base32 string
        try:
            # Ensure the secret is properly formatted (remove spaces and ensure uppercase)
            self.secret = totp_secret.replace(' ', '').upper()
            pyotp.TOTP(self.secret).now()
        except Exception as e:
            _LOGGER.error(f"Invalid TOTP secret: {str(e)}")
            raise ValueError(f"Invalid TOTP secret: {str(e)}")
        
        _LOGGER.info("TotpTwoFaHandler initialized successfully")

    def get_two_fa_code(self, driver: webdriver.Chrome) -> Optional[str]:
        """
        Generate and return a current TOTP code.
        
        Args:
            driver: Selenium WebDriver instance (not used in this implementation)
            
        Returns:
            A string containing the current TOTP code or None if an error occurs
        """
        try:
            # Generate the TOTP code
            totp = pyotp.TOTP(self.secret)
            code = totp.now()
            
            # Log success without exposing the actual code
            _LOGGER.info(f"Generated TOTP code successfully (last digits: ...{code[-2:]})")
            
            return code
        except Exception as e:
            _LOGGER.error(f"Error generating TOTP code: {str(e)}")
            return None

    def __str__(self) -> str:
        """
        Return a string representation of this handler.
        
        Returns:
            A string describing this handler
        """
        return "TotpTwoFaHandler(Automated TOTP Code Generator)"


if __name__ == "__main__":
    """
    Standalone test for the TOTP handler.
    
    Usage:
        export IBEAM_TOTP_SECRET=YOUR_TOTP_SECRET
        python -m ibeam.src.two_fa_handlers.totp_handler
    """
    import sys
    
    # Check if TOTP secret is set
    if not os.environ.get('IBEAM_TOTP_SECRET'):
        print("Error: IBEAM_TOTP_SECRET environment variable is not set")
        print("Usage: export IBEAM_TOTP_SECRET=YOUR_TOTP_SECRET")
        sys.exit(1)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Create handler
        handler = TotpTwoFaHandler(outputs_dir="/tmp")
        
        # Generate code
        code = handler.get_two_fa_code(None)
        
        # Print code
        print(f"Generated TOTP code: {code}")
        
        # Success message
        print("Handler is working correctly!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)