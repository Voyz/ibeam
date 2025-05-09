# Two-Factor Authentication

IBeam supports various methods of handling two-factor authentication (2FA) when logging into Interactive Brokers. This allows for automated authentication even when 2FA is enabled on your IBKR account.

## Supported 2FA Methods

IBeam currently supports the following 2FA methods:

1. **Manual Input** - Default method where you manually enter the 2FA code
2. **Google Messages** - Automatically retrieves SMS codes from Google Messages web interface
3. **TOTP** - Automatically generates Time-based One-Time Password codes (compatible with Google Authenticator, Authy, etc.)

## Configuration

To configure 2FA handling, set the `IBEAM_TWO_FA_HANDLER` environment variable to one of the supported handler types:

```bash
# For manual input (default)
export IBEAM_TWO_FA_HANDLER=MANUAL

# For Google Messages
export IBEAM_TWO_FA_HANDLER=GOOGLE_MESSAGES

# For TOTP (Time-based One-Time Password)
export IBEAM_TWO_FA_HANDLER=TOTP
```

## Manual Input Handler

This is the default handler. When a 2FA code is required, IBeam will wait for you to manually enter the code.

No additional configuration is required for this handler.

## Google Messages Handler

This handler automatically retrieves SMS codes from the Google Messages web interface. It requires additional configuration:

```bash
export IBEAM_TWO_FA_HANDLER=GOOGLE_MESSAGES
export IBEAM_GOOGLE_MESSAGES_PHONE="+1234567890"  # Your phone number in international format
```

### Requirements for Google Messages Handler

1. You must have Google Messages set as your default SMS app on your Android phone
2. You must have previously paired your phone with Google Messages for web
3. The phone number must be provided in international format (e.g., "+1234567890")

## TOTP Handler

The TOTP handler automatically generates Time-based One-Time Password codes for authentication, eliminating the need for manual input during the 2FA process.

```bash
export IBEAM_TWO_FA_HANDLER=TOTP
export IBEAM_TOTP_SECRET=YOUR_TOTP_SECRET  # Your TOTP secret key (base32 encoded)
```

### Availability Notice

TOTP-based two-factor authentication may not be available to all IBKR users. While IBKR documentation doesn't explicitly state limitations, some users may only have access to SMS-based 2FA. If you're unable to set up TOTP authentication in your IBKR account settings, please contact IBKR customer support for assistance.

### Features of TOTP Handler

- Fully automated TOTP code generation
- No manual user input required
- Compatible with standard TOTP implementations (Google Authenticator, Authy, etc.)
- Proper error handling and logging

### Requirements for TOTP Handler

- The `pyotp` Python package must be installed (included in IBeam's requirements)
- You must have your TOTP secret key (the same key used to set up your authenticator app)

### Setup Guide

For a comprehensive step-by-step guide on setting up and using the TOTP handler, please see the [TOTP Handler Documentation](totp_handler.md).

The guide includes:
- How to enable TOTP 2FA in your IBKR account
- How to obtain and save your TOTP secret key
- Configuration examples for both standalone and Docker deployments
- Verification steps to ensure your setup is working correctly
- Troubleshooting common issues

### How It Works

The TOTP handler uses the `pyotp` library to generate time-based one-time passwords based on the secret key provided in the `IBEAM_TOTP_SECRET` environment variable. When IBeam needs a 2FA code, the handler automatically generates the current valid code without requiring any user interaction.

## Custom Handler

If you need a custom 2FA handler, you can implement your own by:

1. Creating a class that inherits from `ibeam.src.two_fa_handlers.two_fa_handler.TwoFaHandler`
2. Implementing the `get_two_fa_code(self)` method
3. Setting the environment variables:
   ```bash
   export IBEAM_TWO_FA_HANDLER=CUSTOM_HANDLER
   export IBEAM_CUSTOM_TWO_FA_HANDLER=your_module.YourCustomHandler
   ```

### Example Custom Handler Implementation

Here's a simple example of a custom handler that always returns a fixed code (not recommended for production use):

```python
from ibeam.src.two_fa_handlers.two_fa_handler import TwoFaHandler

class FixedCodeTwoFaHandler(TwoFaHandler):
    def __init__(self, outputs_dir=None):
        super().__init__(outputs_dir)
        self.fixed_code = "123456"  # Not recommended for production!
        
    def get_two_fa_code(self, driver=None):
        return self.fixed_code
        
    def __str__(self):
        return "Fixed Code Two-Factor Authentication Handler"
```

To use this handler, you would set:
```bash
export IBEAM_TWO_FA_HANDLER=CUSTOM_HANDLER
export IBEAM_CUSTOM_TWO_FA_HANDLER=path.to.your.module.FixedCodeTwoFaHandler
```

## Testing Your 2FA Handler

You can test your 2FA handler independently by creating a simple test script:

```python
import os
from ibeam.src.two_fa_handlers.two_fa_selector import get_two_fa_handler

# Set your environment variables
os.environ['IBEAM_TWO_FA_HANDLER'] = 'TOTP'  # Or your preferred handler
os.environ['IBEAM_TOTP_SECRET'] = 'YOUR_TOTP_SECRET'  # If using TOTP

# Create the handler
handler = get_two_fa_handler(outputs_dir="/tmp")

# Generate and print a code
code = handler.get_two_fa_code(None)
print(f"Generated 2FA code: {code}")
```