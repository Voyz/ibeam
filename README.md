
# IBeam

IBeam is an authentication and maintenance tool used for the Interactive Brokers Client Portal Web API Gateway.

Features:

* Facilitates continuous headless run of the Gateway.
* Executes automated injection of IBKR credentials into the authentication page used by the Gateway.
* No physical display required.
* No interaction from the user required.
* Built to be run within a Docker container, although it can be used as standalone too.
* Not so secure. Yupp, you'll need to store the credentials somewhere, and that's a risk. Read more about it here.

## Usage

#### Using Docker image (recommended)

IBeam's Docker image is configured to work out of the box. Run the IBeam image exposing the default port 8081 and providing the environment variable credentials either directly or through a file.

Using env.list file:
```
docker run --env-file env.list -p 8081:8081 ibeam
```

Providing environment variables directly:
```
docker run --env IB_ACCOUNT=your_account123 --env IB_PASSWORD=your_password123 -p 8081:8081 ibeam
```

Verify the Gateway is running by calling:
```
curl -x localhost:8081 -X GET "https://localhost:5000/v1/api/one/user" -k
```

Note that IBeam uses a proxy to expose the communication with the Gateway. Read more about it here.


#### Standalone 

The entrypoint of IBeam is the `ibeam_starter.py` script. When called without any arguments, the script will start the Gateway (if not currently running) and will attempt to authenticate (if not currently authenticated).

```
python ibeam_starter.py
```

Following exclusive flags can be provided when running the starter script:

* `-a`, `--authenticate` - Authenticate the currently running gateway.
* `-s`, `--start` - Start the gateway if not already running.
* `-l`, `--validate` - Validate authentication.
* `-t`, `--tickle` - Tickle the gateway.
* `-u`, `--user` - Get the user info.

Additionally the following flag can be supplied with any other flags to log additional runtime information:

* `-v`, `--verbose` - More verbose output.

## Runtime environment requirements

#### Credentials
Whether running using an image or as standalone, IBeam expects IBKR credentials to be provided as environment variables.

* `IB_ACCOUNT` - IBKR account name 
* `IB_PASSWORD` - IBKR account password

IBeam expects an optional third credential `IB_KEY`. If provided, it will be used to decrypt the password given in the `IB_PASSWORD` variable. [cryptography.fernet][fernet] decryption is used, therefore to encrypt your password use:

```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
f = Fernet(key)
password = f.encrypt(b"your_ibkr_password123")
print(f'IB_PASSWORD={password}, IB_KEY={key}')
```

If any of the required credentials environment variables is not found, user will be prompted to enter them directly in the terminal.

#### Standalone environment 

When running standalone, IBeam requires the following to be set up:

* IBKR Client Portal API Gateway
* Java JRE capable of running the Gateway
* Google Chrome
* Chrome Driver

Additionally, the following environment variables:

* `CHROME_DRIVER_PATH` - path to the Chome Driver executable
* `GATEWAY_PATH` - path to the root of the Gateway 

Note that you can chose to not use the `ibeam_starter.py` script and instantiate and use the `ibeam.gateway_client.GatewayClient` directly in your script instead. This way you will be able to provide any of the credentials, as well as the Chrome Driver and Gateway paths directly upon construction of the `GatewayClient`.

#### Optional environment variables

To facilitate custom usage and become more future-proof, IBeam expects the following environment variables altering its behaviour:


| Variable name | Default value | Description |
| ---  | ----- | --- |
| `GATEWAY_STARTUP_SECONDS` | 3 | How many seconds to wait before attempting to communicate with the gateway after  its startup. |
| `GATEWAY_BASE_URL` | `https://localhost:5000` | Base URL of the gateway. |
| `ROUTE_AUTH` | /sso/Login?forwardTo=22&RL=1&ip2loc=on | Gateway route with authentication page.
| `ROUTE_USER` | /v1/api/one/user | Gateway route | with user information. |
| `ROUTE_VALIDATE` | /v1/portal/sso/validate | Gateway route with validation call. |
| `ROUTE_TICKLE` | /v1/api/tickle | Gateway route with tickle call. |
| `USER_NAME_EL_ID` | user_name | HTML element id containing the username input field. |
| `PASSWORD_EL_ID` | password | HTML element id containing the password input field. |
| `SUBMIT_EL_ID` | submitForm | HTML element id containing the submit button. |
| `SUCCESS_EL_TEXT` | Client login succeeds | HTML element text indicating successful authentication. |

[fernet]: https://cryptography.io/en/latest/fernet/