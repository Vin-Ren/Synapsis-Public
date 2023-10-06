from typing import Callable, Optional, Any

from automators.utils.logger import Logging
from automators.utils.exception import MaxTriesReachedError

logger = Logging.get_logger(__name__)


__all__ = ['retry', 'convertVersion']


def retry(function: Callable, args=(), kwargs={}, successValidator: Optional[Callable[[Any], bool]] = None, maxTries: int = 3, logInfo: str = ''):
    '''retry(function, args, kwargs, successValidator=None, maxTries=3)
    Calls the given function repeatedly
    :param function: the function to call
    :param args: positional arguments to be passed to the function
    :param kwargs: keyword arguments to be passed to the function
    :param successValidator: validator will be fed the function return value, if validator returns True, returns the return value, else continue.
    :param maxTries: if provided, used as max try count instead of cls.MAX_TRIES.
    :param logInfo: Additional text to be logged out through logger.debug
    :type maxTries: int
    '''
    logger.debug("retry: started with function={} args={} kwargs={} successValidator={} maxTries={}".format(function.__name__, args, kwargs, successValidator, maxTries))
    if logInfo:
        logger.debug("retry: "+logInfo)
    defaultValidator = lambda res: True if res is not None else False
    validator = successValidator if successValidator is not None else defaultValidator

    tries = 0
    rv = None
    while tries < maxTries:
        logger.debug("retry: try#{i}: function={} args={} kwargs={}".format(function.__name__, args, kwargs, i=tries))
        rv = function(*args, **kwargs)
        if validator(rv):
            logger.debug("retry: Condition satisifed.")
            return rv
        tries += 1
    raise MaxTriesReachedError('{} Tries reached.'.format(maxTries))


def convertVersion(version_name: str):
    if not version_name:
        return 0
    intified = version_name.replace('.', '0')
    if intified.isdigit():
        return int(intified)
    else:
        intified = intified.replace('a', '1').replace('b', '2').replace('s', '3')
        if intified.isdigit():
            return intified
        else:
            raise ValueError('Cannot convert version name={}'.format(version_name))
