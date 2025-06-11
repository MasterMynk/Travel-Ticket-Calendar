from typing import TypeVar, Self
from collections.abc import Callable


class ValueFlag:
    _T = TypeVar('_T')

    def __init__(self, name: str, missing_msg: str, ask: Callable[[], _T], as_str: Callable[[Self], str], val_err_msg: str = '', with_data: Callable[[str], _T] = lambda data: data, initial_val: _T | None = None):
        self.flag = f'--{name}'
        self.val_err_msg = val_err_msg
        self.missing_msg = missing_msg
        self.with_data = with_data
        self.ask = ask
        self._val: self._T | None = initial_val
        self.as_str = as_str
        self._initial_val = initial_val

    def __str__(self):
        return self.as_str(self)

    @property
    def val(self):
        return self._val

    @val.setter
    def val(self, data):
        if data == None:
            self._val = self._initial_val
        else:
            self._val = data


class BoolFlag:
    def __init__(self, name: str):
        self.flag = f'--{name}'
        self.val = False
