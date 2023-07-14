from ibeam.config import Config
from ibeam.src.handlers.secrets_handler import SecretsHandler
from ibeam.src.login.authenticate import log_in
from ibeam.src.login.driver import DriverFactory
from ibeam.src.login.targets import Targets
from ibeam.src.two_fa_handlers.two_fa_handler import TwoFaHandler


class LoginHandler():

    def __init__(self,
                 cnf:Config,
                 secrets_handler:SecretsHandler,
                 two_fa_handler:TwoFaHandler,
                 driver_factory:DriverFactory,
                 targets: Targets,
                 ):

        self.cnf = cnf
        self.secrets_handler = secrets_handler
        self.two_fa_handler = two_fa_handler
        self.driver_factory = driver_factory
        self.targets = targets


    def login(self):
        return log_in(
            targets=self.targets,
            driver_factory=self.driver_factory,
            account=self.secrets_handler.account,
            password=self.secrets_handler.password,
            key=self.secrets_handler.key,
            base_url=self.cnf.GATEWAY_BASE_URL,
            two_fa_handler=self.two_fa_handler,
            route_auth=self.cnf.ROUTE_AUTH,
            two_fa_select_target=self.cnf.TWO_FA_SELECT_TARGET,
            strict_two_fa_code=self.cnf.STRICT_TWO_FA_CODE,
            max_immediate_attempts=self.cnf.MAX_IMMEDIATE_ATTEMPTS,
            oauth_timeout=self.cnf.OAUTH_TIMEOUT,
            max_presubmit_buffer=self.cnf.MAX_PRESUBMIT_BUFFER,
            min_presubmit_buffer=self.cnf.MIN_PRESUBMIT_BUFFER,
            max_failed_auth=self.cnf.MAX_FAILED_AUTH,
            outputs_dir=self.cnf.OUTPUTS_DIR,
        )
