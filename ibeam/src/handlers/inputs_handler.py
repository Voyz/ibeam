import logging
import os
import shutil
from pathlib import Path

_LOGGER = logging.getLogger('ibeam.' + Path(__file__).stem)


class InputsHandler():

    def __init__(self,
                 inputs_dir: str,
                 gateway_dir: str):
        self._inputs_dir = inputs_dir
        self._gateway_dir = gateway_dir

        self._cacert_jks_path = os.path.join(inputs_dir, 'cacert.jks')
        self._cacert_pem_path = os.path.join(inputs_dir, 'cacert.pem')

        self._valid_certificates = os.path.isfile(self._cacert_jks_path) and os.path.isfile(self._cacert_pem_path)
        if self._valid_certificates:
            _LOGGER.info('TLS certificates found and will be used for verification')

        gateway_root_dir = os.path.join(self._gateway_dir, 'root')

        config_source = os.path.join(self._inputs_dir, 'conf.yaml')
        if os.path.isfile(config_source):
            _LOGGER.info('Custom conf.yaml found and will be used by the Gateway')
            config_target = os.path.join(gateway_root_dir, 'conf.yaml')
            shutil.copy2(config_source, config_target)

        if self._valid_certificates:
            cacert_target = os.path.join(gateway_root_dir, os.path.basename(self._cacert_jks_path))
            shutil.copy2(self._cacert_jks_path, cacert_target)

    @property
    def inputs_dir(self):
        return self._inputs_dir

    @property
    def gateway_dir(self):
        return self._gateway_dir

    @property
    def cacert_jks_path(self):
        return self._cacert_jks_path

    @property
    def cacert_pem_path(self):
        return self._cacert_pem_path

    @property
    def valid_certificates(self):
        return self._valid_certificates