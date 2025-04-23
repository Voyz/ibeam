# IBeam TOTP Two-Factor Authentication Handler

This built-in handler for IBeam automatically generates Time-based One-Time Password (TOTP) codes for authentication, eliminating the need for manual input during the 2FA process.

## Features

- Fully automated TOTP code generation
- No manual user input required
- Compatible with standard TOTP implementations (Google Authenticator, Authy, etc.)
- Proper error handling and logging
- Built directly into IBeam

## Usage

1. Ensure the pyotp dependency is installed:
   ```bash
   pip install pyotp
   ```

2. Set the following environment variables:
   ```bash
   export IBEAM_TWO_FA_HANDLER=TOTP
   export IBEAM_TOTP_SECRET=YOUR_TOTP_SECRET
   ```

   Replace `YOUR_TOTP_SECRET` with your actual TOTP secret key (base32 encoded).

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `IBEAM_TWO_FA_HANDLER` | Yes | Must be set to `TOTP` |
| `IBEAM_TOTP_SECRET` | Yes | Your TOTP secret key (base32 encoded) |

## Testing

You can test the handler independently by creating a simple test script:

```python
import os
from ibeam.src.two_fa_handlers.totp_handler import TotpTwoFaHandler

# Set your TOTP secret
os.environ['IBEAM_TOTP_SECRET'] = 'YOUR_TOTP_SECRET'

# Create the handler
handler = TotpTwoFaHandler(outputs_dir="/tmp")

# Generate and print a code
code = handler.get_two_fa_code(None)
print(f"Generated TOTP code: {code}")
```

If everything is configured correctly, you should see output similar to:
```
2025-04-23 20:56:53,472 - ibeam.totp_handler - INFO - TotpTwoFaHandler initialized successfully
2025-04-23 20:56:53,472 - ibeam.totp_handler - INFO - Generated TOTP code successfully (last digits: ...30)
Generated TOTP code: 524230
```

## Security Considerations

- The TOTP secret is sensitive information. Store it securely and do not hardcode it in your scripts.
- Use environment variables or a secure secrets management system to provide the secret to IBeam.
- The handler logs only the last two digits of the generated TOTP code to avoid exposing the full code in logs.

## Troubleshooting

### Error: "IBEAM_TOTP_SECRET environment variable is not set"

Make sure you've set the `IBEAM_TOTP_SECRET` environment variable.

### Error: "Invalid TOTP secret"

The TOTP secret must be a valid base32-encoded string. Check that your secret is correctly formatted.

### TOTP Code Not Accepted

- Verify that your system clock is synchronized correctly. TOTP codes are time-based and require accurate time.
- Confirm that the TOTP secret matches the one used by the service you're authenticating with.
- Some services may have a specific TOTP implementation (e.g., different time step). Consult the service's documentation.

## License

This plugin is released under the same license as IBeam.