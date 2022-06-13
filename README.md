*This library is currently being beta-tested. See something that's broken? Did we get something wrong? [Create an issue and let us know!][issues]*

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

#### Docker Image with environment variable secrets
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

#### Docker Swarm with Docker Secrets

This section discusses running an instance of IBeam inside a locked Docker Swarm, and using the Docker Swarm facilities for managing secrets.
Please refer to the following articles for in-depth details on Docker Swarm, locking the swarm, and using Docker secrets.

- [Swarm mode overview](https://docs.docker.com/engine/swarm/)
- [Lock your swarm to protect its encryption key](https://docs.docker.com/engine/swarm/swarm_manager_locking/)
- [Manage sensitive data with Docker secrets](https://docs.docker.com/engine/swarm/secrets/)

It's important to understand that if you fail to lock your swarm then it's possible for an attacker to read the encryption key for the swarm.
That in turn would allow them to decrypt any secrets stored in your swarm.

Once you have a locked Docker Swarm instance initialized, you can create the secrets.
On your host system create two secure (meaning not world-readable) files containing your Interactive Brokers account name and password:

1. ib.account.txt
2. ib.password.txt

Next, inject these secrets into the Docker Swarm by using the `docker secret create` command.

```posh
docker secret create IBEAM_ACCOUNT_v1 ib.account.txt
docker secret create IBEAM_PASSWORD_v1 ib.password.txt
```
Once you've initialized the secrets delete the original files from your host system.

Next, create an [Inputs Directory][inputs-and-outputs] with a `conf.yaml` file.  The format of this file is discussed on the the [Gateway Configuration][gateway-configuration] page.
Toward the end of the `conf.yaml` there is a block to define IPs to trust and reject, e.g.,

```yaml
...
ips:
  allow:
    - 127.0.0.1
  deny:
    - 0-255.*.*.*
```
The example above grants access from the local loopback interface, `127.0.0.1`, and denies all other addresses (`0-255.*.*.*`).

To deploy IBeam as a service named 'ibeam' we will use the `docker service create` command.

```posh
docker service create \
    --name ibeam \
    --network host \
    --publish published=5000,target=5000,mode=host \
    --secret source=IBEAM_ACCOUNT_v1,uid=1000,gid=1000,mode=0400 \
    --secret source=IBEAM_PASSWORD_v1,uid=1000,gid=1000,mode=0400 \
    --env IBEAM_SECRETS_SOURCE=fs \
    --env IBEAM_ACCOUNT=/run/secrets/IBEAM_ACCOUNT_v1 \
    --env IBEAM_PASSWORD=/run/secrets/IBEAM_PASSWORD_v1 \
    --mount type=bind,source=/path/to/inputs/directory,target=/srv/inputs,ro=true \
    voyz/ibeam:latest
```

Note that you need to change the `/path/to/inputs/directory` in the `--mount` parameter of this example to the actual filesystem path you created for your [Inputs Directory][inputs-and-outputs].

Docker will prepare the `ibeam` container by writing the secrets into the container's tmpfs filesystem `/run/secrets/`.
When IBeam starts it will read the file paths indicated via the environment variables `IBEAM_ACCOUNT` and `IBEAM_PASSWORD`.

You can verify that the container is running by using `docker ps` and `docker logs`.

If you examine the output of the `docker ps` command we run below, you will see at the far right it lists the name of the running container as `ibeam.1.q4jovvg0bsu7svzak17lrm22e`.
We'll have to specify that full name when we call `docker logs` in the subsequent command.

```posh
$ docker ps
CONTAINER ID   IMAGE         COMMAND               CREATED          STATUS          PORTS                                       NAMES
bde337ce7216   test:latest   "/srv/ibeam/run.sh"   54 seconds ago   Up 52 seconds   0.0.0.0:5000->5000/tcp, :::5000->5000/tcp   ibeam.1.q4jovvg0bsu7svzak17lrm22e

$ docker logs ibeam.1.q4jovvg0bsu7svzak17lrm22e
2022-06-10 14:09:01,642|I| ############ Starting IBeam version 0.4.0 ############
2022-06-10 14:09:01,643|I| Custom conf.yaml found and will be used by the Gateway
2022-06-10 14:09:01,646|I| Secrets source: fs
2022-06-10 14:09:01,647|I| Gateway not found, starting new one...
...
2022-06-10 14:09:02,654|I| Gateway started with pid: 12
2022-06-10 14:09:03,826|I| No active sessions, logging in...
2022-06-10 14:09:15,845|I| Authentication process succeeded
2022-06-10 14:09:19,146|I| Gateway running and authenticated.
2022-06-10 14:09:19,167|I| Starting maintenance with interval 60 seconds
```

Once IBeam has started, verify the Gateway is running by sending a request with curl.

```posh
curl -X GET "https://localhost:5000/v1/api/one/user" -k
```

##### Docker Stack

You can also manage deployment of the IBeam service into Docker Swarm by using a [docker stack](https://docs.docker.com/engine/swarm/stack-deploy/) managed through a `docker-compose.yml` file.
Below is an example of a `docker-compose.yml` file specifying the same directives that we used when deploying the Docker service manually.

```yaml
version: "3.7"

secrets:
  IBEAM_ACCOUNT_v1:
    external: true
  IBEAM_PASSWORD_v1:
    external: true

services:
  ibeam:
    image: "voyz/ibeam:latest"
    environment:
      IBEAM_SECRETS_SOURCE: "fs"
      IBEAM_ACCOUNT: "/run/secrets/IBEAM_ACCOUNT_v1"
      IBEAM_PASSWORD: "/run/secrets/IBEAM_PASSWORD_v1"
    ports:
      - published: 5000
        target: 5000
        mode: host
    secrets:
      - source: "IBEAM_ACCOUNT_v1"
        uid: "1000"
        gid: "1000"
        mode: 0400
      - source: "IBEAM_PASSWORD_v1"
        uid: "1000"
        gid: "1000"
        mode: 0400
    volumes:
      - type: "bind"
        source: "inputs"
        target: "/srv/inputs"
        read_only: true
```

When accessed from the local host Docker Swarm will route traffic over a gateway interface, `docker_gwbridge`, that it sets up.

We need to modify the `conf.yaml` in our [Inputs Directory][inputs-and-outputs] to account for this address.

To determine the gateway interface address, use the `docker network inspect` command to look at the `docker_gwbridge` network.

```posh
docker network inspect docker_gwbridge
...
        "IPAM": {
            "Driver": "default",
            "Options": null,
            "Config": [
                {
                    "Subnet": "172.18.0.0/16",
                    "Gateway": "172.18.0.1"
                }
            ]
        },
...
```

Here we can see the address is `172.18.0.1`.  Edit your `conf.yaml` file and add the address to the allow list.

```yaml
...
ips:
  allow:
    - 127.0.0.1
    - 172.18.0.1
  deny:
    - 0-255.*.*.*
```

To deploy our Docker stack we will use the `docker stack deploy` command.
Here we're going to name the stack `ib`.

```posh
docker stack deploy -c docker-compose.yml ib
```

Docker will create the IBeam container as a new service named `ib_ibeam`.
You can verify that the container is running by using `docker ps` and `docker logs`.

If you examine the output of the `docker ps` command we run below, you will see at the far right it lists the name of the running container as `ib_ibeam.1.rknycfzbs5i76euv9xfx6mbtw`.
We'll have to specify that full name when we call `docker logs` in the subsequent command.

```posh
$ docker ps
CONTAINER ID   IMAGE         COMMAND                  CREATED              STATUS              PORTS                                       NAMES
c5ed2dfe4757   ibcp:latest   "/bin/sh -c 'python …"   About a minute ago   Up About a minute   0.0.0.0:5000->5000/tcp, :::5000->5000/tcp   ib_ibeam.1.rknycfzbs5i76euv9xfx6mbtw

$ docker logs -f ib_ibeam.1.rknycfzbs5i76euv9xfx6mbtw
2022-06-10 14:24:26,906|I| ############ Starting IBeam version 0.4.0 ############
2022-06-10 14:24:26,646|I| Secrets source: fs
2022-06-10 14:24:26,909|I| Gateway not found, starting new one...
...
2022-06-10 14:24:27,915|I| Gateway started with pid: 11
2022-06-10 14:24:28,817|I| No active sessions, logging in...
2022-06-10 14:24:39,602|I| Authentication process succeeded
2022-06-10 14:24:42,726|I| Gateway running and authenticated.
2022-06-10 14:24:42,733|I| Starting maintenance with interval 60 seconds
```

Once IBeam has started, verify the Gateway is running by sending a request with curl.

```posh
curl -X GET "https://localhost:5000/v1/api/one/user" -k
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

Read more in [Installation and Startup][installation-and-startup].

## <a name="how-ibeam-works"></a>How does IBeam work?

In a standard startup IBeam performs the following:

1. **Copy inputs** from the Inputs Directory to Gateway's `root` folder (if provided).
1. **Ensure the Gateway is running** by calling the tickle endpoint. If not:
    1. Start the Gateway in a new shell.
1. **Ensure the Gateway has an active session that is  authenticated** by calling the tickle endpoint. If not:
    1. Create a new Chrome Driver instance using `selenium`.
    1. Start a virtual display using `pyvirtualdisplay`.
    1. Access the Gateway's authentication website.
    1. Once loaded, input username and password and submit the form.
    1. Wait for the login confirmation and quit the website.
    1. Verify once again if Gateway is running and authenticated.
1. **Start the maintenance**, attempting to keep the Gateway alive and authenticated. Will repeat login if finds no active session or the session is not authenticated. 


## <a name="security"></a>Security
Please feel free to suggest improvements to the security risks currently present in IBeam and the Gateway by [opening an issue][issues] on GitHub.

### Credentials

The Gateway requires credentials to be provided on a regular basis. The only way to avoid manually having to input them every time is to store the credentials somewhere. This alone is a security risk.

By default, IBeam expects the credentials to be available as environment variables during runtime. Whether running IBeam in a container or directly on a host machine, an unwanted user may gain access to these credentials. If your setup is exposed to a risk of someone unauthorised reading the credentials, you may want to look for other solutions than IBeam or use the Gateway standalone and authenticate manually each time.

We considered providing a possibility to read the credentials from an external credentials store, such as GCP Secrets, yet that would require some authentication credentials too, which brings back the same issue it was to solve.

You can remove one of the attack vectors by using a locked Docker Swarm instance, installing your credentials into it using Docker Secrets, and telling IBeam to read the secrets from the container's in-memory `/run` filesystem.
This configuration allows the credentials to be encrypted when at rest.
But the credentials are still accessible in plaintext via the running container, so if a security issue arises where an exploit exists for the port 5000 API, or if your host is compromised and an attacker can access your running container, then the secret could be exposed.

## Roadmap

IBeam was built by traders just like you. We made it open source in order to collectively build a reliable solution. If you enjoy using IBeam, we encourage you to attempt implementing one of the following tasks:

* ~~Include TLS certificates.~~
* ~~Two Factor Authentictaion.~~
* Remove necessity to install Java.
* ~~Remove necessity to install Chrome or find a lighter replacement.~~
* Add usage examples.
* Full test coverage.
* Improve the security issues.
* Find a lighter replacement to using Chromium

Read the [CONTRIBUTING](https://github.com/Voyz/ibeam/blob/master/CONTRIBUTING.md) guideline to get started.

----

## Licence

See [LICENSE](https://github.com/Voyz/ibeam/blob/master/LICENSE)



## Disclaimer

IBeam is not built, maintained, or endorsed by the Interactive Brokers. 

Use at own discretion. IBeam and its authors give no guarantee of uninterrupted run of and access to the Interactive Brokers Client Portal Web API Gateway. You should prepare for breaks in connectivity to IBKR servers and should not depend on continuous uninterrupted run of the Gateway. IBeam requires your private credentials to be exposed to a security risk, potentially resulting in, although not limited to interruptions, loss of capital and loss of access to your account. To partially reduce the potential risk use Paper Account credentials.

IBeam is provided on an AS IS and AS AVAILABLE basis without any representation or endorsement made and without warranty of any kind whether express or implied, including but not limited to the implied warranties of satisfactory quality, fitness for a particular purpose, non-infringement, compatibility, security and accuracy. To the extent permitted by law, IBeam's authors will not be liable for any indirect or consequential loss or damage whatever (including without limitation loss of business, opportunity, data, profits) arising out of or in connection with the use of IBeam. IBeam's authors make no warranty that the functionality of IBeam will be uninterrupted or error free, that defects will be corrected or that IBeam or the server that makes it available are free of viruses or anything else which may be harmful or destructive.

## Built by Voy

Hi! Thanks for checking out and using this library. If you are interested in discussing your project, require mentorship, consider hiring me, or just wanna chat - I'm happy to talk.

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
[troubleshooting]: https://github.com/Voyz/ibeam/wiki/Troubleshooting

[issues]: https://github.com/Voyz/ibeam/issues
[gateway]: https://interactivebrokers.github.io/cpwebapi/
