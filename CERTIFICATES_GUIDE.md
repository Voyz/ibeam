# IBeam Proprietary TLS Certificates

This is a guide on setting up TLS certificates in IBeam.

See [IBeam's GitHub][ibeam-github] page for the remaining documentation.

This documentation includes:

* [Overview](#overview)
* [Why two certificates?](#two-certificates)
* [Certificates in Conf.yaml](#certificates-in-conf-yaml)
* [Generating Certificates](#generating-certificates)
* [Summary](#summary)
* [Use your certificate](#use-your-certificate)


## <a name="overview"></a>Overview 
Gateway (and as such IBeam) supports providing your own certificate and using it for HTTPS verification. Unfortunately, it isn't very straightforward. Make sure to familiarize yourself with the following before proceeding:

* [Inputs Directory](https://github.com/Voyz/ibeam#inputs-directory)
* [Gateway Configuration](https://github.com/Voyz/ibeam#gateway-configuration)

In short, to enable custom certificates' support you will need to:

1. Generate the `cacert.jks` and `cacert.pem` certificates.
1. Alter the `conf.yaml`.
1. Provide these three files to IBeam using the Inputs Directory before startup.

## <a name="two-certificates"></a>Why two certificates?

Gateway is a Java application which requires a [Java KeyStore][jks] (.jks) certificate. However, most modern clients use other formats, such as [Privacy-Enhanced Mail][pem] (.pem) or [Public-Key Cryptography Standards][pkcs] (.p12). 

As a result you will need to provide both `cacert.jks` and `cacert.pem` certificates. The `cacert.jks` is used by the Gateway, while the `cacert.pem` is used by IBeam to communicate with the Gateway.

Upon startup, IBeam will look for `cacert.jks` and `cacert.pem` files in the [Inputs Directory](https://github.com/Voyz/ibeam#inputs-directory). If none are found, IBeam will use the [default TLS certificate](https://github.com/Voyz/ibeam#default-tls-certificate) and ignore certificate verification.

You can read more about generating right certificates in [Generating Certificates](#generating-certificates).

## <a name="certificates-in-conf-yaml"></a>Certificates in Conf.yaml

Apart from [providing the certificates](#two-certificates) using the Inputs Directory, you also need to [provide an altered `conf.yaml`](https://github.com/Voyz/ibeam#gateway-configuration) file to tell Gateway to use your `cacert.jks` certificate instead of the default one.

To do so, change the following two fields in `conf.yaml`:

```yaml
sslCert: "vertx.jks"
sslPwd: "mywebapi"
```

to:

```yaml
sslCert: "cacert.jks"
sslPwd: "YOUR_CERTIFICATE_PASSWORD"
```

Such altered `conf.yaml` needs to be stored in the same Input Directory as the `cacert.jks` and `cacert.pem` certificates.

## <a name="generating-certificates"></a>Generating Certificates

You can generate your own self-signed certificate in two ways:

* [Using Keytool](#using-keytool) to generate `cacert.jks`
* [Using OpenSSL](#using-openssl) to generate `cacert.pem`

Either way you chose, you will then need to convert one certificate into the other and provide IBeam with both. Therefore, you will need both [Keytool][jre] and [OpenSSL][openssl] to generate your certificates.

Note that you can't generate `cacert.jks` and `cacert.pem` independently. You must generate only one certificate first using either method and then convert it into the other format.

### <a name="using-keytool"></a>Using Keytool

#### Generate JKS

Keytool is a Java tool shipped with [Java Runtime Environment][jre] (JRE). It can be found in `JRE_ROOT/bin/keytool`.

1. To generate the `cacert.jks` run:
    ```posh
    keytool -genkey -keyalg RSA -alias selfsigned -keystore cacert.jks -storepass YOUR_CERTIFICATE_PASSWORD -validity 730 -keysize 2048
    ```
    
    Note the YOUR_CERTIFICATE_PASSWORD field. Replace it which certificate password you want to use. This is the password you will need to [provide in the `sslPwd` field of the `conf.yaml`](#certificates-in-conf-yaml). You will need to use this same password in later steps.
    
    Optionally, you may want to add additional option to provide Subject Alternative Names (SAN) in order for the certificate to accept requests from your client hosts. For instance, if the server with IBeam is to be communicated with from two client machines, one with IP address of `10.148.0.0` and one with DNS of `my-client.machine.com`, your keytool command line should include:
        
    ```posh
    -ext SAN=ip:10.147.0.0,dns:my-client.machine.com
    ```

1. Upon running command from Step 1, you will be asked the following questions which you may chose to ignore:
    * What is your first and last name?
    * What is the name of your organizational unit?
    * What is the name of your organization?
    * What is the name of your City or Locality?
    * What is the name of your State or Province?
    * What is the two-letter country code for this unit?

1. Eventually, Keytool will ask for your confirmation, along the lines of:
    
    > Is CN=Unknown, OU=Unknown, O=Unknown, L=Unknown, ST=Unknown, C=Unknown correct?

    Type `yes` to continue if the information is correct.

1. Finally, Keytool will ask you for the key password. You may simply hit return to use the same password as specified in the `-storepass` flag in Step 1. DO NOT provide a different password than YOUR_CERTIFICATE_PASSWORD specified above.

1. You should now have the `cacert.jks` file generated in your current directory.





#### Convert JKS to PEM

To convert a `cacert.jks` to `cacert.pem` file you need to:

1. Convert `cacert.jks` to `cacert.p12` using Keytool:
    ```posh
    keytool -importkeystore -srckeystore cacert.jks -destkeystore cacert.p12 -srcstoretype jks -deststoretype pkcs12
    ```
   You will be asked for a new password for `cacert.p12`, as well as for the original password of `cacert.jks`. Ensure you use the same password as when generating the `cacert.jks`.

1. Convert `cacert.p12` to `cacert.pem` using OpenSSL:
    ```posh
    openssl pkcs12 -in cacert.p12 -out cacert.pem
    ```
   Again, you will be asked for a new password for `cacert.pem`, as well as for the original password of `cacert.p12`. Ensure you use the same password as when generating the `cacert.jks` and `cacert.p12`.

1. You should now have the `cacert.pem` file generated in your current directory.

You should now have `cacert.jks`, `cacert.p12` and `cacert.pem`. You will only need the `.jks` and `.pem` files. You may delete the redundant `cacert.p12` file.

### <a name="using-openssl"></a>Using OpenSSL

#### Generate PEM

1. To generate a `cacert.pem` using OpenSSL run:

    ```posh
    openssl req -x509 -days 730 -newkey rsa:2048 -keyout key.pem -out cert.pem
    ```
   
    Optionally, you may want to add additional option to provide Subject Alternative Names (SAN) in order for the certificate to accept requests from your client hosts. To do so, you must create a `san.cnf` used as a configuration file for openssl, and add the following to the openssl command line:
    
    ```posh
    -config san.cnf
    ```
   
   Your `san.cnf` can take multiple forms, yet to support SAN it requires the subjectAltName field. For your convinence, we prepared a template [san.cnf](support/san.cnf) file that you can use as a basis to specify your SANs.
   
   For instance, if the server with IBeam is to be communicated with from two client machines, one with IP address of `10.148.0.0` and one with DNS of `my-client.machine.com`, your `san.cnf` should contain:
   
   ```cfg
   [alt_names]
   IP.1 = 10.148.0.0
   DNS.1 = my-client.machine.com
   ```
   
1. You will be asked for a password. This is the password you will need to [provide in the `sslPwd` field of the `conf.yaml`](#certificates-in-conf-yaml). You will need to use this same password in later steps.

1. You should now have `key.pem` and `cert.pem`files in your current directory.

1. Combine `key.pem` and `cert.pem` to create `cacert.pem`:

    ```posh
    cat key.pem cert.pem > cacert.pem 
    ```
   
   You can also merge these two files manually if you prefer.
   
1. You should now have `cacert.pem`, `key.pem` and `cert.pem`. You will only need the `cacert.pem` file. You may delete the redundant `key.pem` and `cert.pem` files.

#### PEM to JKS

To convert a `cacert.pem` to `cacert.jks` file you need to:


1. Convert `cacert.pem` to `cacert.p12` using OpenSSL:
    ```posh
    openssl pkcs12 -export -in cacert.pem -out cacert.p12
    ```
   
    You will be asked for a new password for `cacert.p12`, as well as for the original password of `cacert.pem`. Ensure you use the same password as when generating the `cacert.pem`.

1. Convert `cacert.p12` to `cacert.jks` using Keytool:
    ```posh
    keytool -importkeystore -srckeystore cacert.p12 -srcstoretype pkcs12 -destkeystore cacert.jks
    ```
   
    Again, you will be asked for a new password for `cacert.jks`, as well as for the original password of `cacert.p12`. Ensure you use the same password as when generating the `cacert.pem` and `cacert.p12`.

1. You should now have the `cacert.jks` file generated in your current directory.

You should now have `cacert.pem`, `cacert.p12` and `cacert.jks`. You will only need the `.jks` and `.pem` files. You may delete the redundant `cacert.p12` file.

## <a name="summary"></a>Summary

To provide proprietary TLS certificate you need to:

1. Generate `cacert.pem` and `cacert.jks` files.
1. Modify the `conf.yaml` to point at the `cacert.jks` file and to provide its password.
1. Use the Input Directory to provide IBeam with these three files.
1. Start IBeam.

## <a name="use-your-certificate"></a>Use your certificate

Once IBeam started the Gateway successfully using the the certificates and `conf.yaml` you provided, you may communicate with the Gateway using the `cacert.pem`.

#### cURL

cURL accepts `--cacert` flag that can be used to pass the certificate. See [cURL documentation][curl-ssl] for more.
```posh
curl -X GET "https://localhost:5000/v1/api/one/user" --cacert cacert.pem
```

#### Python urllib3

Python [urllib3][urllib3] library allows you to specify a SSL context through which you can specify the location of your certificate.

```python
context = ssl.create_default_context()
context.verify_mode = ssl.CERT_REQUIRED
context.check_hostname = True
context.load_verify_locations('cacert.pem')
urllib.request.urlopen("https://localhost:5000/v1/api/one/user", context=context)
```

#### Python requests
Python [requests][requests-ssl] library allows you to set the `verify` parameter to specify the location of your certificate.  
```python
requests.get("https://localhost:5000/v1/api/one/user", verify='cacert.pem')
```

[jre]: https://www.java.com/en/download/
[pem]: https://en.wikipedia.org/wiki/Privacy-Enhanced_Mail
[pkcs]: https://en.wikipedia.org/wiki/PKCS
[jks]: https://en.wikipedia.org/wiki/Java_KeyStore
[openssl]: https://www.openssl.org/
[ibeam-github]: https://github.com/Voyz/ibeam
[curl-ssl]: https://curl.haxx.se/docs/sslcerts.html
[urllib3]: https://urllib3.readthedocs.io/en/latest/
[requests-ssl]: https://2.python-requests.org/en/master/user/advanced/#ssl-cert-verification