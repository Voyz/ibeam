import importlib
import importlib.util
import os
from pathlib import Path
from typing import Union

from ibeam.src import var
from ibeam.src.inputs_handler import InputsHandler
from ibeam.src.two_fa_handlers.external_request_handler import ExternalRequestTwoFaHandler
from ibeam.src.two_fa_handlers.google_msg_handler import GoogleMessagesTwoFaHandler
from ibeam.src.two_fa_handlers.notification_resend_handler import NotificationResendTwoFaHandler
from ibeam.src.two_fa_handlers.two_fa_handler import TwoFaHandler

_CUSTOM_TWO_FA_HANDLER = os.environ.get('IBEAM_CUSTOM_TWO_FA_HANDLER', 'custom_two_fa_handler.CustomTwoFaHandler')
"""Fully qualified path of the custom 2FA handler in the inputs directory."""


def select(handler_name, driver_path, inputs_handler: InputsHandler) -> Union[TwoFaHandler, None]:

    if handler_name == 'GOOGLE_MSG':
        handler = GoogleMessagesTwoFaHandler(driver_path)
    elif handler_name == 'EXTERNAL_REQUEST':
        handler = ExternalRequestTwoFaHandler()
    elif handler_name == 'NOTIFICATION_RESEND':
        handler = NotificationResendTwoFaHandler()
    elif handler_name == 'CUSTOM_HANDLER':
        handler = load_custom_two_fa_handler(_CUSTOM_TWO_FA_HANDLER, inputs_handler)()
    else:
        handler = None

    return handler


def load_custom_two_fa_handler(two_fa_handler_fqp, inputs_handler: InputsHandler):
    module_name, class_name = two_fa_handler_fqp.rsplit('.', 1)
    handler_filepath = Path(inputs_handler.inputs_dir, module_name + '.py')
    try:
        spec = importlib.util.spec_from_file_location(module_name, os.fspath(handler_filepath))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except ModuleNotFoundError as e:
        if str(e) == f'No module named \'{module_name}\'':
            raise RuntimeError(
                f'Invalid handler path: "{two_fa_handler_fqp}". Module "{module_name}" not found. You need to provide the MODULE_NAME.CLASS_NAME of your custom handler as IBEAM_CUSTOM_TWO_FA_HANDLER environment variable.') from e
        else:
            raise e

    try:
        klass = getattr(module, class_name)
    except AttributeError as e:
        if str(e) == f'module \'{module_name}\' has no attribute \'{class_name}\'':
            raise RuntimeError(
                f'Invalid handler path: "{two_fa_handler_fqp}". Module "{module_name}" has no class "{class_name}". You need to provide the MODULE_NAME.CLASS_NAME of your custom handler as IBEAM_CUSTOM_TWO_FA_HANDLER environment variable.') from e
        else:
            raise e

    return klass
