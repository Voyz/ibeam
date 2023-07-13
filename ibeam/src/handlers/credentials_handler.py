import os

from ibeam.src.handlers.secrets_handler import SecretsHandler


class CredentialsHandler():
    def __init__(self,
                 secrets_handler: SecretsHandler,
                 ):
        self.secrets_handler = secrets_handler

        """Character encoding for secret files"""
        self.encoding = os.environ.get(
            'IBEAM_ENCODING', default='UTF-8')


    def account(self):
        """IBKR account name."""
        self.account = self.secrets_handler.secret_value(self.encoding, 'IBEAM_ACCOUNT')

    def password(self):
        """IBKR account password."""
        self.password = self.secrets_handler.secret_value(self.encoding, 'IBEAM_PASSWORD')

    def key(self):
        """Key to the IBKR password."""
        self.key = self.secrets_handler.secret_value(self.encoding, 'IBEAM_KEY')
