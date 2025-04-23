# TOTP Two-Factor Authentication Handler

The TOTP (Time-based One-Time Password) handler provides fully automated 2FA code generation for services that use TOTP-based authentication.

## Features

- Fully automated TOTP code generation
- No manual user input required
- Compatible with standard TOTP implementations (Google Authenticator, Authy, etc.)
- Proper error handling and logging

## Requirements

- The `pyotp` Python package must be installed:
  ```bash
  pip install pyotp
  ```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `IBEAM_TWO_FA_HANDLER` | Yes | Must be set to `TOTP` |
| `IBEAM_TOTP_SECRET` | Yes | Your TOTP secret key (base32 encoded) |

Example:
```bash
export IBEAM_TWO_FA_HANDLER=TOTP
export IBEAM_TOTP_SECRET=YOUR_TOTP_SECRET
```

Replace `YOUR_TOTP_SECRET` with your actual TOTP secret key (base32 encoded).

## How It Works

The TOTP handler uses the `pyotp` library to generate time-based one-time passwords based on the secret key provided in the `IBEAM_TOTP_SECRET` environment variable. When IBeam needs a 2FA code, the handler automatically generates the current valid code without requiring any user interaction.

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