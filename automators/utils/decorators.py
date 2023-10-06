from functools import wraps
from typing import Union, Callable

from automators.utils.exception import MaxTriesReachedError


__all__ = ['wrap_func', 'before', 'after', 'state', 'reset_state', 'state_automator', 'reset_state_automator']


def before(to_call: Callable, isMethod=None):
    "Simple decorator to call a function before the decorated function runs."
    def method_decor(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            to_call(self)
            rv=func(self, *args, **kwargs)
            return rv
        return wrapper
    def decor(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            to_call()
            rv=func(*args, **kwargs)
            return rv
        return wrapper
    return method_decor if isMethod else decor


def after(to_call: Callable, isMethod=None):
    "Simple decorator to call a function after the decorated function runs."
    def method_decor(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            rv=func(self, *args, **kwargs)
            to_call(self)
            return rv
        return wrapper
    def decor(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            rv=func(*args, **kwargs)
            to_call()
            return rv
        return wrapper
    return method_decor if isMethod else decor


def wrap_func(before=None, after=None, onException=None, beforekwargs={}, afterkwargs={}):
    def decor(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                if before is not None:
                    before(**beforekwargs)
                rv = func(*args, **kwargs)
                if after:
                    after(**afterkwargs)
                return rv
            except Exception as exc:
                if onException is None:
                    raise
                onException(exc)
        return wrapper
    return decor


def state(state_getter: Union[Callable, str]):
    "Simple decorator to modify the state string of a device. For use in devices. state_getter can be a function or a string."
    if not callable(state_getter):
        def handler(self):self.state=state_getter
    else:
        def handler(self):self.state=state_getter()
    return before(handler, isMethod=True)


def reset_state(func):
    "Simple decorator to reset the state of a device after the function call. For use in devices."
    def handler(self):self.state=''
    return after(handler, isMethod=True)(func)


def state_automator(state_getter: Union[Callable, str]):
    "Simple decorator to modify the state string of a device. For use in automators. state_getter can be a function or a string."
    if not callable(state_getter):
        def handler(self):self.device.state=state_getter
    else:
        def handler(self):self.device.state=state_getter()
    return before(handler, isMethod=True)


def reset_state_automator(func):
    "Simple decorator to reset the state of a device after the function call. For use in automators."
    def handler(self):self.device.state=''
    return after(handler, isMethod=True)(func)


def retry_decorator(exceptions=Exception, maxTries=3):
    '''wraps the decorated function, and then rerun the function again if it raises the exception(s).
    :param exceptions: exception(s) to be catched
    :param maxTries: maximum amount of tries before giving up
    '''
    def decor(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tries=0
            while tries < maxTries:
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    pass
            raise MaxTriesReachedError('{} Tries reached'.format(maxTries))
        return wrapper
    return decor
