import logging
import os
import shutil
from pathlib import Path

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)


class InputsHandler():

    def __init__(self,
                 inputs_dir: str,
                 gateway_dir: str):
        self.inputs_dir = inputs_dir
        self.gateway_dir = gateway_dir

        self.cecert_jks_path = os.path.join(inputs_dir, 'cacert.jks')
        self.cecert_pem_path = os.path.join(inputs_dir, 'cacert.pem')

        self.valid_certificates = os.path.isfile(self.cecert_jks_path) and os.path.isfile(self.cecert_pem_path)
        if self.valid_certificates:
            _LOGGER.debug('Certificates found and will be used for TLS verification')

        gateway_root_dir = os.path.join(self.gateway_dir, 'root')

        config_source = os.path.join(self.inputs_dir, 'conf.yaml')
        if os.path.isfile(config_source):
            _LOGGER.info('Custom conf.yaml found and will be used by the Gateway')
            config_target = os.path.join(gateway_root_dir, 'conf.yaml')
            shutil.copy2(config_source, config_target)

        if self.valid_certificates:
            cacert_target = os.path.join(gateway_root_dir, os.path.basename(self.cecert_jks_path))
            shutil.copy2(self.cecert_jks_path, cacert_target)
