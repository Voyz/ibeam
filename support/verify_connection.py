#!/usr/bin/env python3
import os
import ssl
import urllib.request
from ssl import SSLContext

import urllib3

PORT = '5000'
url = f'https://localhost:{PORT}/v1/api/one/user'
cacert_filename = 'cacert.pem'
cert_filename = 'cert.pem'
key_filename = 'key.pem'
inputs = os.environ.get('IBEAM_INPUTS_DIR', os.path.join(os.path.dirname(__file__), 'cert'))
cacert = os.path.abspath(os.path.join(inputs, cacert_filename))
cert = os.path.abspath(os.path.join(inputs, cert_filename))
key = os.path.abspath(os.path.join(inputs, key_filename))
print(cacert)

context = ssl.create_default_context()
context.verify_mode = ssl.CERT_REQUIRED

context.check_hostname = True
context.load_verify_locations(cacert)
r = urllib.request.urlopen(url, context=context, timeout=15)
print(r.read())

headers = {'User-Agent': 'ibeam/0.1.0'}
http = urllib3.PoolManager(cert_reqs='REQUIRED', ca_certs=cacert)
r = http.urlopen('GET', url, headers=headers)
print(r.data)

#########################################################################

# import requests
# r = requests.get(url, verify=cacert)
# print(r.content)
