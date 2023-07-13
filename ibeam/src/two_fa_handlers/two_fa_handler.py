from abc import ABC, abstractmethod
from typing import Union


class TwoFaHandler(ABC):

    def __init__(self, outputs_dir:str):
        self.outputs_dir = outputs_dir

    @abstractmethod
    def get_two_fa_code(self, driver) -> Union[str, None]:
        raise NotImplementedError()

    def __str__(self):
        return "TwoFaHandler()"
