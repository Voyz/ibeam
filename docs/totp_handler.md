# TOTP Two-Factor Authentication Handler

The TOTP (Time-based One-Time Password) handler provides fully automated 2FA code generation for Interactive Brokers accounts that have TOTP-based authentication enabled.

## Features

- Fully automated TOTP code generation
- No manual user input required
- Compatible with standard TOTP implementations (Google Authenticator, Authy, etc.)
- Proper error handling and logging

## Availability Notice

TOTP-based two-factor authentication may not be available to all IBKR users. While IBKR documentation doesn't explicitly state limitations, some users may only have access to SMS-based 2FA. If you're unable to set up TOTP authentication in your IBKR account settings, please contact IBKR customer support for assistance.

## Step-by-Step Setup Guide

### 1. Enable TOTP 2FA in your IBKR Account

1. Log in to your IBKR account at [ibkr.com](https://www.ibkr.com)
2. Navigate to User Settings > Security > Security Settings
3. Under Two-Factor Authentication, select "Security Code Generator (Authenticator App)"
4. Follow IBKR's instructions to set up your authenticator app
   - You'll be shown a QR code to scan with your authenticator app
   - IMPORTANT: During setup, IBKR will also display a text-based secret key - save this key securely as you'll need it for IBeam

### 2. Install Required Dependencies

Ensure the `pyotp` package is installed:

```bash
pip install pyotp
```

If you're using the Docker image, this dependency is already included.

### 3. Configure IBeam to Use TOTP

Set the following environment variables:

```bash
export IBEAM_TWO_FA_HANDLER=TOTP
export IBEAM_TOTP_SECRET=YOUR_TOTP_SECRET
```

Replace `YOUR_TOTP_SECRET` with the base32-encoded secret key you saved during IBKR TOTP setup.

#### Docker Example:

```bash
docker run --env IBEAM_ACCOUNT=your_account123 \
           --env IBEAM_PASSWORD=your_password123 \
           --env IBEAM_TWO_FA_HANDLER=TOTP \
           --env IBEAM_TOTP_SECRET=YOUR_TOTP_SECRET \
           -p 5000:5000 voyz/ibeam
```

#### Docker Compose Example:

Add to your `env.list` file:
```
IBEAM_TWO_FA_HANDLER=TOTP
IBEAM_TOTP_SECRET=YOUR_TOTP_SECRET
```

### 4. Verify Setup

You can test if your TOTP configuration is working correctly by running:

```bash
python -m ibeam.src.two_fa_handlers.totp_handler
```

If configured correctly, you should see output similar to:
```
2025-04-23 20:56:53,472 - ibeam.totp_handler - INFO - TotpTwoFaHandler initialized successfully
2025-04-23 20:56:53,472 - ibeam.totp_handler - INFO - Generated TOTP code successfully (last digits: ...30)
Generated TOTP code: 524230
Handler is working correctly!
```

## How It Works

The TOTP handler uses the `pyotp` library to generate time-based one-time passwords based on the secret key provided in the `IBEAM_TOTP_SECRET` environment variable. When IBeam needs a 2FA code during the login process, the handler automatically generates the current valid code without requiring any user interaction.

## Security Considerations

- The TOTP secret is sensitive information. Store it securely and do not hardcode it in your scripts.
- Use environment variables or a secure secrets management system to provide the secret to IBeam.
- The handler logs only the last two digits of the generated TOTP code to avoid exposing the full code in logs.
- Consider using Docker Secrets or GCP Secret Manager as described in the [Advanced Secrets](https://github.com/Voyz/ibeam/wiki/Advanced-Secrets) documentation.

## Troubleshooting

### Error: "IBEAM_TOTP_SECRET environment variable is not set"

Make sure you've set the `IBEAM_TOTP_SECRET` environment variable.

### Error: "Invalid TOTP secret"

The TOTP secret must be a valid base32-encoded string. Check that your secret is correctly formatted.

### TOTP Code Not Accepted

- Verify that your system clock is synchronized correctly. TOTP codes are time-based and require accurate time.
- Confirm that the TOTP secret matches the one used by the service you're authenticating with.
- If IBKR displays a 'Failed' error despite entering the correct code, try generating a new code and submitting it immediately, as TOTP codes have a limited validity period.
- If problems persist, you may need to disable and re-enable TOTP in your IBKR account settings.