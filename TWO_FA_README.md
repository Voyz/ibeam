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

### Features of TOTP Handler

- Fully automated TOTP code generation
- No manual user input required
- Compatible with standard TOTP implementations (Google Authenticator, Authy, etc.)
- Proper error handling and logging

### Requirements for TOTP Handler

- The `pyotp` Python package must be installed (included in IBeam's requirements)
- You must have your TOTP secret key (the same key used to set up your authenticator app)

### Security Considerations for TOTP Handler

- The TOTP secret is sensitive information. Store it securely and do not hardcode it in your scripts.
- Use environment variables or a secure secrets management system to provide the secret to IBeam.
- The handler logs only the last two digits of the generated TOTP code to avoid exposing the full code in logs.

### Troubleshooting TOTP Handler

#### Error: "IBEAM_TOTP_SECRET environment variable is not set"

Make sure you've set the `IBEAM_TOTP_SECRET` environment variable.

#### Error: "Invalid TOTP secret"

The TOTP secret must be a valid base32-encoded string. Check that your secret is correctly formatted.

#### TOTP Code Not Accepted

- Verify that your system clock is synchronized correctly. TOTP codes are time-based and require accurate time.
- Confirm that the TOTP secret matches the one used by the service you're authenticating with.
- Some services may have a specific TOTP implementation (e.g., different time step). Consult the service's documentation.

## Custom Handler

If you need a custom 2FA handler, you can implement your own by:

1. Creating a class that inherits from `ibeam.src.two_fa_handlers.two_fa_handler.TwoFaHandler`
2. Implementing the `get_two_fa_code(self)` method
3. Setting the environment variables:
   ```bash
   export IBEAM_TWO_FA_HANDLER=CUSTOM_HANDLER
   export IBEAM_CUSTOM_TWO_FA_HANDLER=your_module.YourCustomHandler
   ```

For more details, see the [Custom Handler documentation](https://github.com/Voyz/ibeam/wiki/Two-Factor-Authentication#custom-handler).