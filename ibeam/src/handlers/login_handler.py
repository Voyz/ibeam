from ibeam.config import Config
from ibeam.src.handlers.credentials_handler import CredentialsHandler
from ibeam.src.login.authenticate import log_in
from ibeam.src.two_fa_handlers.two_fa_handler import TwoFaHandler


class LoginHandler():

    def __init__(self,
                 cnf:Config,
                 credentials_handler:CredentialsHandler,
                 two_fa_handler:TwoFaHandler,

                 ):

        self.cnf = cnf
        self.credentials_handler = credentials_handler
        self.two_fa_handler = two_fa_handler


    def login(self):
        return log_in(
            driver_path=self.cnf.CHROME_DRIVER_PATH,
            account=self.credentials_handler.account,
            password=self.credentials_handler.password,
            key=self.credentials_handler.key,
            base_url=self.cnf.GATEWAY_BASE_URL,
            two_fa_handler=self.two_fa_handler
        )
