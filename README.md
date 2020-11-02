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

## Documentation:

* Setup
  * [Installation and Startup][installation-and-startup]
  * [Runtime Environment][runtime-environment]
* Advanced
  * [Inputs Directory][inputs-directory]
  * [Gateway Configuration][gateway-configuration]
  * [TLS Certificates and HTTPS][tls-and-https]
* More
  * [Troubleshooting][troubleshooting]



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

Read more in [Installation and Startup][installation-and-startup].

### Standalone 

The entrypoint of IBeam is the `ibeam_starter.py` script. When called without any arguments, the script will start the Gateway (if not currently running) and will attempt to authenticate (if not currently authenticated).

```posh
python ibeam_starter.py
```

Verify the Gateway is running as standalone by calling:
```posh
curl -X GET "https://localhost:5000/v1/api/one/user" -k
```

You will need additional environment requirements to run IBeam standalone. Read more about it in [Standalone Environment](#standalone-environment)

Read more in [Installation and Startup][installation-and-startup].

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



[home]: https://github.com/Voyz/ibeam/wiki
[installation-and-startup]: https://github.com/Voyz/ibeam/wiki/Installation-and-startup
[runtime-environment]: https://github.com/Voyz/ibeam/wiki/Runtime-environment
[gateway-configuration]: https://github.com/Voyz/ibeam/wiki/Gateway-Configuration
[inputs-directory]: https://github.com/Voyz/ibeam/wiki/Inputs-Directory
[tls-and-https]: https://github.com/Voyz/ibeam/wiki/TLS-Certificates-and-HTTPS
[troubleshooting]: https://github.com/Voyz/ibeam/wiki/Troubleshooting

[issues]: https://github.com/Voyz/ibeam/issues
[gateway]: https://interactivebrokers.github.io/cpwebapi/
[docker-envs]: https://docs.docker.com/engine/reference/commandline/run/#set-environment-variables--e---env---env-file
