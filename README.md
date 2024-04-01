*This library is currently being beta-tested. See something that's broken? Did we get something
wrong? [Create an issue and let us know!][issues]*

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

IBeam is an authentication and maintenance tool used for
the [Interactive Brokers Client Portal Web API Gateway.][gateway]

Features:

* **Facilitates continuous headless run of the Gateway.**

* **No physical display required** - virtual display buffer can be used instead.
* **No interaction from the user required** - automated injection of IBKR credentials into the authentication page used
  by the Gateway.
* **TLS certificate support** - you can provide your own certificates.
* **Containerised using Docker** - it's a plug and play image, although IBeam can be used as standalone too.
* **Not so secure** - Yupp, you'll need to store the credentials somewhere, and that's a risk. Read more about it
  in [Security](#security).

**NOTE**: IBeam is not designed to automate logging into TWS or IB Gateway (also known as TWS Gateway). Use [IBC](ibc) for that.
There are also [Docker image projects that include TWS/Gateway and IBC](ib-gateway-docker).

## Documentation:

* Setup
    * [Installation and Startup][installation-and-startup]
    * [Runtime Environment][runtime-environment]
* Advanced
    * [Inputs And Outputs][inputs-and-outputs]
    * [IBeam Configuration][ibeam-configuration]
    * [Gateway Configuration][gateway-configuration]
    * [TLS Certificates and HTTPS][tls-and-https]
    * [Two Factor Authentication][two-fa]
* More
    * [Troubleshooting][troubleshooting]

<a href="https://www.youtube.com/watch?v=603n4xV26S0">
    <img src="https://github.com/Voyz/voyz_public/blob/master/ibeam_promo_vidA_A01.gif" alt="IBeam showcase gif" title="IBeam showcase gif" width="500"/>
</a>

## Quick start

### Installation

#### Docker Image (Recommended):

```posh
docker pull voyz/ibeam
```

#### Standalone:

```posh
pip install ibeam
```

### Startup

#### Docker

```posh
docker run --env IBEAM_ACCOUNT=your_account123 --env IBEAM_PASSWORD=your_password123 -p 5000:5000 voyz/ibeam
```

#### docker-compose:

Create a `docker-compose.yml` file with the following contents:

```yaml
version: "2.1"

services:
  ibeam:
    image: voyz/ibeam
    container_name: ibeam
    env_file:
      - env.list
    ports:
      - 5000:5000
      - 5001:5001
    network_mode: bridge # Required due to clientportal.gw IP whitelist
    restart: 'no' # Prevents IBEAM_MAX_FAILED_AUTH from being exceeded
```

Create an `env.list` file in the same directory with the following contents:

```posh
IBEAM_ACCOUNT=your_account123
IBEAM_PASSWORD=your_password123
```

Run the following command:

```posh
docker-compose up -d
```

#### Standalone:

```posh
python ibeam_starter.py
```

----
Once started, verify the Gateway is running by calling:

```posh
curl -X GET "https://localhost:5000/v1/api/one/user" -k
```

Read more in [Installation and Startup][installation-and-startup] and [Advanced Secrets][advanced-secrets].

## <a name="how-ibeam-works"></a>How does IBeam work?

In a standard startup IBeam performs the following:

1. **Copy inputs** from the Inputs Directory to Gateway's `root` folder (if provided).
1. **Ensure the Gateway is running** by calling the tickle endpoint. If not:
    1. Start the Gateway in a new shell.
1. **Ensure the Gateway has an active session that is authenticated** by calling the tickle endpoint. If not:
    1. Create a new Chrome Driver instance using `selenium`.
    1. Start a virtual display using `pyvirtualdisplay`.
    1. Access the Gateway's authentication website.
    1. Once loaded, input username and password and submit the form.
    1. Wait for the login confirmation and quit the website.
    1. Verify once again if Gateway is running and authenticated.
1. **Start the maintenance**, attempting to keep the Gateway alive and authenticated. Will repeat login if finds no
   active session or the session is not authenticated.

## <a name="security"></a>Security

Please feel free to suggest improvements to the security risks currently present in IBeam and the Gateway
by [opening an issue][issues] on GitHub.

### Credentials

The Gateway requires credentials to be provided on a regular basis. The only way to avoid manually having to input them
every time is to store the credentials somewhere. This alone is a security risk.

By default, IBeam expects the credentials to be available as environment variables during runtime. Whether running IBeam
in a container or directly on a host machine, an unwanted user may gain access to these credentials. If your setup is
exposed to a risk of someone unauthorised reading the credentials, you may want to look for other solutions than IBeam
or use the Gateway standalone and authenticate manually each time.

There are currently two proposed solutions to this problem:

1. **Docker Swarm**

    You can remove one of the attack vectors by using a locked Docker Swarm instance, installing your credentials into it using Docker Secrets, and telling IBeam to read the secrets from the container's in-memory `/run` filesystem.
    This configuration allows the credentials to be encrypted when at rest. 
    But the credentials are still accessible in plaintext via the running container, so if a security issue arises where an exploit exists for the port 5000 API, or if your host is compromised and an attacker can access your running container, then the secret could be exposed. 
2. **GCP Secret Manager**

    If you're deploying IBeam on Google Cloud Platform, you can securely use the Service Account's credentials to access [GCP Secret Manager][secret-manager-docs]. This is possible since all types of GCP deployment (currently: Compute Engine, Kubernetes, Cloud Run and Cloud Functions) are running within a context that has a Service Account available. IBeam can query Google's metadata server when running on GCP for the Service Account's access token, and use that to read secrets from the Secret Manager.


See [Advanced Secrets][advanced-secrets] for more information.

## Roadmap

IBeam was built by traders just like you. We made it open source in order to collectively build a reliable solution. If
you enjoy using IBeam, we encourage you to attempt implementing one of the following tasks:

* ~~Include TLS certificates.~~
* ~~Two Factor Authentictaion.~~
* Remove necessity to install Java.
* ~~Remove necessity to install Chrome or find a lighter replacement.~~
* Add usage examples.
* Full test coverage.
* ~~Improve the security issues.~~
* Find a lighter replacement to using Chromium

Read the [CONTRIBUTING](https://github.com/Voyz/ibeam/blob/master/CONTRIBUTING.md) guideline to get started.

----

## Licence

See [LICENSE](https://github.com/Voyz/ibeam/blob/master/LICENSE)

## Disclaimer

IBeam is not built, maintained, or endorsed by the Interactive Brokers.

Use at own discretion. IBeam and its authors give no guarantee of uninterrupted run of and access to the Interactive
Brokers Client Portal Web API Gateway. You should prepare for breaks in connectivity to IBKR servers and should not
depend on continuous uninterrupted run of the Gateway. IBeam requires your private credentials to be exposed to a
security risk, potentially resulting in, although not limited to interruptions, loss of capital and loss of access to
your account. To partially reduce the potential risk use Paper Account credentials.

IBeam is provided on an AS IS and AS AVAILABLE basis without any representation or endorsement made and without warranty
of any kind whether express or implied, including but not limited to the implied warranties of satisfactory quality,
fitness for a particular purpose, non-infringement, compatibility, security and accuracy. To the extent permitted by
law, IBeam's authors will not be liable for any indirect or consequential loss or damage whatever (including without
limitation loss of business, opportunity, data, profits) arising out of or in connection with the use of IBeam. IBeam's
authors make no warranty that the functionality of IBeam will be uninterrupted or error free, that defects will be
corrected or that IBeam or the server that makes it available are free of viruses or anything else which may be harmful
or destructive.

## Built by Voy

Hi! Thanks for checking out and using this library. If you are interested in discussing your project, require
mentorship, consider hiring me, or just wanna chat - I'm happy to talk.

You can send me an email to get in touch: hello@voyzan.com

Or if you'd just want to give something back, I've got a Buy Me A Coffee account:

<a href="https://www.buymeacoffee.com/voyzan" rel="nofollow">
    <img src="https://raw.githubusercontent.com/Voyz/voyz_public/master/vz_BMC.png" alt="Buy Me A Coffee" style="max-width:100%;" width="192">
</a>

Thanks and have an awesome day 👋

[home]: https://github.com/Voyz/ibeam/wiki

[installation-and-startup]: https://github.com/Voyz/ibeam/wiki/Installation-and-startup

[runtime-environment]: https://github.com/Voyz/ibeam/wiki/Runtime-environment

[ibeam-configuration]: https://github.com/Voyz/ibeam/wiki/IBeam-Configuration

[gateway-configuration]: https://github.com/Voyz/ibeam/wiki/Gateway-Configuration

[inputs-and-outputs]: https://github.com/Voyz/ibeam/wiki/Inputs-And-Outputs

[two-fa]: https://github.com/Voyz/ibeam/wiki/Two-Factor-Authentication

[tls-and-https]: https://github.com/Voyz/ibeam/wiki/TLS-Certificates-and-HTTPS

[advanced-secrets]: https://github.com/Voyz/ibeam/wiki/Advanced-Secrets

[troubleshooting]: https://github.com/Voyz/ibeam/wiki/Troubleshooting

[issues]: https://github.com/Voyz/ibeam/issues

[gateway]: https://ibkrcampus.com/ibkr-api-page/webapi-doc/

[ibc]: https://github.com/IbcAlpha/IBC

[ib-gateway-docker]: https://github.com/UnusualAlpha/ib-gateway-docker

[secret-manager-docs]: https://cloud.google.com/secret-manager/docs