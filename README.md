# Warning: Pre-alpha version in active development - may not function as described below. 
*We expect to release a working version by the end of 2020.*

<p align="center">
    <a id="ibeam" href="#ibeam">
        <img src="https://github.com/Voyz/ibeam/blob/master/media/ibeam_logo.png" alt="IBeam logo" title="IBeam logo" width="600"/>
    </a>
</p>

<p align="center">
    <a href="https://opensource.org/licenses/Apache-2.0">
        <img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg"/> 
    </a>
    <a href="https://github.com/Voyz/ibeam/releases">
        <img src="https://img.shields.io/pypi/v/ibeam?label=version"/> 
    </a>
</p>

IBeam is an authentication and maintenance tool used for the [Interactive Brokers Client Portal Web API Gateway.][gateway]

Features:

* **Facilitates continuous headless run of the Gateway.**

* **No physical display required** - virtual display buffer can be used instead.
* **No interaction from the user required** - automated injection of IBKR credentials into the authentication page used by the Gateway. 
* **TLS certificate support** - you can provide your own certificates.
* **Containerised using Docker** - it's a plug and play image, although IBeam can be used as standalone too.
* **Not so secure** - Yupp, you'll need to store the credentials somewhere, and that's a risk. Read more about it in [Security](#security).

Documentation:

* [Installation](#installation)
* [Startup](#startup)
* [Runtime environment requirements](#runtime-environment)
* [Security](#security)
* [How does IBeam work?](#how-ibeam-works)
* [Roadmap](#roadmap)

## Installation

Docker image (recommended):
```posh
docker pull voyz/ibeam
```

Standalone:
```posh
pip install ibeam
```

## Startup

### Using Docker image (recommended)

IBeam's Docker image is configured to work out of the box. Run the IBeam image exposing the port 5000 and providing the environment variable credentials either [directly or through a file][docker-envs].

Using env.list file:
```posh
docker run --env-file env.list -p 5000:5000 voyz/ibeam
```

Providing environment variables directly:
```posh
docker run --env IBEAM_ACCOUNT=your_account123 --env IBEAM_PASSWORD=your_password123 -p 5000:5000 voyz/ibeam
```

Verify the Gateway is running inside of the container by calling:
```posh
curl -X GET "https://localhost:5000/v1/api/one/user" -k
```

### Standalone 

The entrypoint of IBeam is the `ibeam_starter.py` script. When called without any arguments, the script will start the Gateway (if not currently running) and will attempt to authenticate (if not currently authenticated).

```posh
python ibeam_starter.py
```

Following exclusive flags can be provided when running the starter script:

* `-a`, `--authenticate` - Authenticate the currently running gateway.
* `-k`, `--kill` - Kill the gateway.
* `-m`, `--maintain` - Maintain the gateway.
* `-s`, `--start` - Start the gateway if not already running.
* `-t`, `--tickle` - Tickle the gateway.
* `-u`, `--user` - Get the user info.
* `-l`, `--validate` - Validate authentication.

Additionally the following flag can be supplied with any other flags to log additional runtime information:

* `-v`, `--verbose` - More verbose output.

Verify the Gateway is running as standalone by calling:
```posh
curl -X GET "https://localhost:5000/v1/api/one/user" -k
```

You will need additional environment requirements to run IBeam standalone. Read more about it in [Standalone Environment](#standalone-environment)

### Once started

Once the Gateway is running and authenticated you can communicate with it like you would normally. Please refer to [Interactive Brokers' documentation][gateway] for more.

## <a name="runtime-environment"></a>Runtime environment requirements

### Credentials
Whether running using an image or as standalone, IBeam expects IBKR credentials to be provided as environment variables. We recommend you start using IBeam with your [paper account credentials][paper-account], and only switch to production account once you're ready to trade.

* `IBEAM_ACCOUNT` - IBKR account name 
* `IBEAM_PASSWORD` - IBKR account password

IBeam expects an optional third credential `IBEAM_KEY`. If provided, it will be used to decrypt the password given in the `IBEAM_PASSWORD` variable. [cryptography.fernet][fernet] decryption is used, therefore to encrypt your password use:

```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
f = Fernet(key)
password = f.encrypt(b"your_ibkr_password123")
print(f'IBEAM_PASSWORD={password}, IBEAM_KEY={key}')
```

If any of the required credentials environment variables is not found, user will be prompted to enter them directly in the terminal.

### <a name="standalone-environment"></a>Standalone environment 

When running standalone, IBeam requires the following to be present:

* [IBKR Client Portal API Gateway][gateway]
* [Java JRE capable of running the Gateway][jre]
* [Google Chrome][chrome]
* [Chrome Driver][chrome-driver]

Additionally, the following environment variables:

* `IBEAM_CHROME_DRIVER_PATH` - path to the Chome Driver executable
* `IBEAM_GATEWAY_DIR` - path to the root of the Gateway 

Note that you can chose to not use the `ibeam_starter.py` script and instantiate and use the `ibeam.gateway_client.GatewayClient` directly in your script instead. This way you will be able to provide any of the credentials, as well as the Chrome Driver and Gateway paths directly upon construction of the `GatewayClient`.

### Optional environment variables

To facilitate custom usage and become more future-proof, IBeam expects the following environment variables altering its behaviour:


| Variable name | Default value | Description |
| ---  | ----- | --- |
| `IBEAM_GATEWAY_STARTUP` | 3 | How many seconds to wait before attempting to communicate with the gateway after  its startup. |
| `IBEAM_GATEWAY_BASE_URL` | `https://localhost:5000` | Base URL of the gateway. |
| `IBEAM_GATEWAY_PROCESS_MATCH` | ibgroup.web.core.clientportal.gw.GatewayStart | The gateway process' name to match against |
| `IBEAM_ROUTE_AUTH` | /sso/Login?forwardTo=22&RL=1&ip2loc=on | Gateway route with authentication page.
| `IBEAM_ROUTE_USER` | /v1/api/one/user | Gateway route | with user information. |
| `IBEAM_ROUTE_VALIDATE` | /v1/portal/sso/validate | Gateway route with validation call. |
| `IBEAM_ROUTE_TICKLE` | /v1/api/tickle | Gateway route with tickle call. |
| `IBEAM_USER_NAME_EL_ID` | user_name | HTML element id containing the username input field. |
| `IBEAM_PASSWORD_EL_ID` | password | HTML element id containing the password input field. |
| `IBEAM_SUBMIT_EL_ID` | submitForm | HTML element id containing the submit button. |
| `IBEAM_SUCCESS_EL_TEXT` | Client login succeeds | HTML element text indicating successful authentication. |
| `IBEAM_MAINTENANCE_INTERVAL` | 60 | How many seconds between each maintenance. |
| `IBEAM_LOG_LEVEL` | INFO | Verbosity level of the logger used. |


## <a name="inputs-directory"></a>Inputs Directory

IBeam will look for a directory specified in the `IBEAM_INPUTS_DIR` environment variable (`/srv/inputs` by default). This directory is used by IBeam to provide files required by the Gateway. Note that these files will override any existing files if there is a conflict. 

Currently the following files are recognised and supported:

* conf.yaml - for [Gateway configuration](#gateway-configuration)
* cacert.jks - for [TLS certificate support](#proprietary-tls-certificate)
* cacert.pem - for [TLS certificate support](#proprietary-tls-certificate)

When using IBeam as a Docker image, you can pass the files to your container by [mounting a volume][docker-volumes] on runtime:

```posh
docker run -v /host/path/to/inputs:/container/path/to/inputs [OTHER_OPTIONS] voyz/ibeam
```

Remember that `/container/path/to/inputs` must be pointed to by `IBEAM_INPUTS_DIR` environment variable in the container.


## <a name="gateway-configuration"></a>Gateway Configuration

Gateway uses a `conf.yaml` file as the configuration API. At the moment there is no documentation on that configuration file, however luckily most fields are self-explanatory. Using it you may alter the behaviour of the Gateway, for instance by changing the port it will listen on or allowing additional IP addresses to communicate from. 

IBeam allows you to provide your own configuration file using the [Inputs Directory](#inputs-directory). Note that IBeam will use the `conf.yaml` file provided to overwrite the existing `conf.yaml` in the `root` subdirectory of Gateway, specified in the `IBEAM_GATEWAY_DIR` environment variable.

If using IBeam in standalone mode, you may edit the `conf.yaml` file directly in the Gateway's `root` folder.

## TLS Certificates

IBeam supports providing a custom TLS certificate to the Gateway. If no certificate is provided IBeam will use the default certificate auto-generated by the Gateway.

### <a name="default-tls-certificate"></a>Ignoring the default TLS certificate

By default, the Gateway will auto-generate its own TLS certificate. This means that all attempts to connect to it will be non-verifiable by your client, and as such will fail. However, you may chose to ignore certificates altogether, which is useful during development and debugging.

#### cURL

cURL accepts `--insecure` or `-k` flags that can be used to ignore verifying certificates. See [cURL documentation][curl-k] for more.
```posh
curl -X GET "https://localhost:5000/v1/api/one/user" -k
```

#### Python urllib3

Python [urllib3][urllib3] library allows you to specify an empty SSL context, which effectively will ignore verifying the certificates.

```python
empty_context = ssl.SSLContext()
urllib.request.urlopen("https://localhost:5000/v1/api/one/user", context=empty_context)
```

#### Python requests
Python [requests][requests-ssl] library allows you to set the `verify` parameter to `False` when making requests, which effectively will ignore verifying the certificates.  
```python
requests.get("https://localhost:5000/v1/api/one/user", verify=False)
```

### <a name="proprietary-tls-certificate"></a>Proprietary TLS certificate

Gateway (and as such IBeam) supports providing your own certificate and using it for HTTPS verification. Unfortunately, it isn't very straightforward. Make sure to familiarize yourself with the following before proceeding:

* [Inputs Directory](#inputs-directory)
* [Gateway Configuration](#gateway-configuration)

In short, to enable custom certificates' support you will need to:

1. Generate the `cacert.jks` and `cacert.pem` certificates.
1. Alter the `conf.yaml`.
1. Provide these three files to IBeam using the Inputs Directory before startup.

Please see [CERTIFICATES_GUIDE](CERTIFICATES_GUIDE.md) to learn how to enable custom certificates.

## <a name="how-ibeam-works"></a>How does IBeam work?

In a standard startup IBeam performs the following:

1. **Copy inputs** from the Inputs Directory to Gateway's `root` folder (if provided).
1. **Ensure the Gateway is running** by calling the tickle endpoint. If not:
    1. Start the Gateway in a new shell.
1. **Ensure the Gateway is authenticated** by calling the validation endpoint. If not:
    1. Create a new Chrome Driver instance using `selenium`.
    1. Start a virtual display using `pyvirtualdisplay`.
    1. Access the Gateway's authentication website.
    1. Once loaded, input username and password and submit the form.
    1. Wait for the login confirmation and quit the website.
    1. Verify once again if Gateway is running and authenticated.
1. **Start the maintenance**, attempting to keep the Gateway alive and authenticated.


## <a name="security"></a>Security
Please feel free to suggest improvements to the security risks currently present in IBeam and the Gateway by [opening an issue][issues] on GitHub.

### Credentials

The Gateway requires credentials to be provided on a regular basis. The only way to avoid manually having to input them every time is to store the credentials somewhere. This alone is a security risk.

Currently, IBeam expects the credentials to be available as environment variables during runtime. Whether running IBeam in a container or directly on a host machine, an unwanted user may gain access to these credentials. If your setup is exposed to a risk of someone unauthorised reading the credentials, you may want to look for other solutions than IBeam or use the Gateway standalone and authenticate manually each time.

We considered providing a possibility to read the credentials from an external credentials store, such as GCP Secrets, yet that would require some authentication credentials too, which brings back the same issue it was to solve.

## Troubleshooting

#### Access Denied.

`Access Denied.` is a cryptic message that Gateway sends when it receives a request from an IP address it doesn't allow requests from. To fix it specify your client's IP address in the `conf.yaml` under `ips/allow` and ensure your IP is not listed in `ips/deny`.

Eg.:

```yaml
ips:
  allow:
    10.148.0.0
    10.149.*
```

Learn how to provide IBeam with a custom `conf.yaml` in [Gateway Configuration section](#gateway-configuration).

#### Hostname X doesn't match Y

This should only appear if you use your own TLS certificates. It means your certificate was created without specifying the client host IP or DNS you're trying to communicate from. You will need to recreate your certificates including the IP or DNS of the machine you're communicating from.

See the optional SAN specification in Step 1 of either [Keytool](CERTIFICATES_GUIDE.md#using-keytool) or [OpenSSL](CERTIFICATES_GUIDE.md#using-openssl) certificate generation.

## Roadmap

IBeam was built by traders just like you. We made it open source in order to collectively build a reliable solution. If you enjoy using IBeam, we encourage you to attempt implementing one of the following tasks:

* ~~Include TLS certificates.~~
* Remove necessity to install Java.
* Remove necessity to install Chrome or find a lighter replacement.
* Add usage examples.
* Full test coverage.
* Improve the security issues.

Read the [CONTRIBUTING](https://github.com/Voyz/ibeam/blob/master/CONTRIBUTING.md) guideline to get started.

----

## Licence

See [LICENSE](https://github.com/Voyz/ibeam/blob/master/LICENSE)



## Disclaimer

IBeam is not built, maintained, or endorsed by the Interactive Brokers. 

Use at own discretion. IBeam and its authors give no guarantee of uninterrupted run of and access to the Interactive Brokers Client Portal Web API Gateway. You should prepare for breaks in connectivity to IBKR servers and should not depend on continuous uninterrupted run of the Gateway. IBeam requires your private credentials to be exposed to a security risk, potentially resulting in, although not limited to interruptions, loss of capital and loss of access to your account. To partially reduce the potential risk use Paper Account credentials.

IBeam is provided on an AS IS and AS AVAILABLE basis without any representation or endorsement made and without warranty of any kind whether express or implied, including but not limited to the implied warranties of satisfactory quality, fitness for a particular purpose, non-infringement, compatibility, security and accuracy.  To the extent permitted by law, IBeam's authors will not be liable for any indirect or consequential loss or damage whatever (including without limitation loss of business, opportunity, data, profits) arising out of or in connection with the use of IBeam.  IBeam's authors make no warranty that the functionality of IBeam will be uninterrupted or error free, that defects will be corrected or that IBeam or the server that makes it available are free of viruses or anything else which may be harmful or destructive.

[issues]: https://github.com/Voyz/ibeam/issues
[fernet]: https://cryptography.io/en/latest/fernet/
[gateway]: https://interactivebrokers.github.io/cpwebapi/
[jre]: https://www.java.com/en/download/
[chrome]: https://www.google.com/chrome/
[chrome-driver]: https://chromedriver.chromium.org/downloads
[docker-envs]: https://docs.docker.com/engine/reference/commandline/run/#set-environment-variables--e---env---env-file
[paper-account]: https://guides.interactivebrokers.com/am/am/manageaccount/aboutpapertradingaccounts.htm
[curl-k]: https://curl.haxx.se/docs/manpage.html#-k
[urllib3]: https://urllib3.readthedocs.io/en/latest/
[requests-ssl]: https://2.python-requests.org/en/master/user/advanced/#ssl-cert-verification
[docker-volumes]: https://docs.docker.com/storage/volumes/