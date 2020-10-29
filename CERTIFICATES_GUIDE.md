#IBeam Proprietary TLS Certificates

This is a guide on setting up TLS certificates in IBeam.


Gateway (and as such IBeam) supports providing your own certificate and using it for authentication. Unfortunately, it isn't very straightforward. Make sure to familiarize yourself with the following before proceeding:

* [Inputs Directory](https://github.com/Voyz/ibeam#inputs-directory)
* [Conf.yaml](https://github.com/Voyz/ibeam#conf-yaml)

In short, to enable custom certificates' support you will need to:

* Generate the `cacert.jks` and `cacert.pem` certificates
* Alter the `conf.yaml`
* Provide these three files to IBeam using the Inputs Directory
  * conf.yaml
  * cacert.jks
  * cacert.pem
#### <a name="two-certificates"></a>Two certificates

Gateway is a Java application which requires a [Java KeyStore][jks] (.jks) certificate. However, most modern clients use other formats, such as [Privacy-Enhanced Mail][pem] (.pem) or [Public-Key Cryptography Standards][pkcs] (.p12). 

As a result you will need to provide both `cacert.jsk` and `cacert.pem` certificates. The `cacert.jks` is used by the Gateway, while the `cacert.pem` is used by IBeam to communicate with the Gateway.

Upon startup, IBeam will look for `cacert.jks` and `cacert.pem` files in the [Inputs Directory](#inputs-directory). If none are found, IBeam will use the [default TLS certificate](https://github.com/Voyz/ibeam#default-tls-certificate) and ignore certificate verification.

You can read more about generating right certificates in [Generating Certificates](#generating-certificates).

#### <a name="certificates-in-conf-yaml"></a>Certificates in Conf.yaml

Apart from [providing the certificates](#two-certificates) using the Inputs Directory, you also need to [provide an altered `conf.yaml`](#conf-yaml) file to tell Gateway to use your `cacert.jks` certificate instead of the default one.

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

### <a name="generating-certificates"></a>Generating Certificates

You can generate your own self-signed certificates in two ways:

* [Using Keytool](#using-keytool) to generate `cacert.jks`
* [Using OpenSSL](#using-openssl) to generate `cacert.pem`

Either way you chose, you will then need to convert one certificate into the other and provide IBeam with both. Therefore, you will need both keytool and openssl to generate your certificates.

#### <a name="using-keytool"></a>Using Keytool

##### Generate JKS

Keytool is a Java tool shipped with [Java Runtime Environment][jre] (JRE). It can be found in `JRE_ROOT/bin/keytool`.

1. To generate the `cacert.jks` run:
    ```posh
    keytool -genkey -keyalg RSA -alias selfsigned -keystore cacert.jks -storepass YOUR_CERTIFICATE_PASSWORD -validity 730 -keysize 2048
    ```
    
    Note the YOUR_CERTIFICATE_PASSWORD field. Replace it which certificate password you want to use. This is the password you will need to [provide in the `sslPwd` field of the `conf.yaml`](#certificates-in-conf-yaml). You will need to use this same password in later steps.
    
    Optionally, you may want to add additional option to provide Subject Alternative Names in order for the certificate to accept requests from your client hosts. For instance, if the server with IBeam is to be communicated with from two client machines, one with IP address of `10.148.0.0` and one with DNS of `my-client.machine.com`, your keytool command line should include:
        
    ```posh
    -ext SAN=ip:10.147.0.0,dns:my-client.machine.com
    ```

2. Upon running the above line, you will be asked the following questions which you may chose to ignore:
    * What is your first and last name?
    * What is the name of your organizational unit?
    * What is the name of your organization?
    * What is the name of your City or Locality?
    * What is the name of your State or Province?
    * What is the two-letter country code for this unit?

3. Eventually, Keytool will ask for your confirmation, along the lines of:
    
    > Is CN=Unknown, OU=Unknown, O=Unknown, L=Unknown, ST=Unknown, C=Unknown correct?

    Type `yes` to continue if the information is correct.

4. Finally, Keytool will ask you for the key password. You may simply hit return to use the same password as specified in the `-storepass` flag above. DO NOT provide a different password than YOUR_CERTIFICATE_PASSWORD specified above.

5. You should now have the `cacert.jsk` file generated in your current directory.





#### Convert JKS to PEM

To convert a `cacert.jks` to `cacert.pem` file you need to:

1. Convert `cacert.jsk` to `cacert.p12`:
    ```posh
    keytool -importkeystore -srckeystore cacert.jks -destkeystore cacert.p12 -srcstoretype jks -deststoretype pkcs12
    ```
   You will be asked for a new password for `cacert.p12`, as well as for the original password of `cacert.jsk`. Ensure you use the same password as when generating the `cacert.jsk`.

1. Convert `cacert.p12` to `cacert.pem` using OpenSSL:
    ```posh
    openssl pkcs12 -in cacert.p12 -out cacert.pem
    ```
   Again, you will be asked for a new password for `cacert.pam`, as well as for the original password of `cacert.p12`. Ensure you use the same password as when generating the `cacert.jsk` and `cacert.p12`.

1. You should now have the `cacert.pem` file generated in your current directory.

#### <a name="using-openssl"></a>Using OpenSSL

#### Generate PEM

```posh
openssl req -x509 -days 730 -newkey rsa:2048 -keyout key.pem -out cert.pem
```

#### PEM to JKS

```posh
cat key.pem cert.pem | openssl pkcs12 -export -out cacert.p12
```

```posh
keytool -importkeystore -srckeystore cacert.p12 -srcstoretype pkcs12 -destkeystore cacert.jks
```

