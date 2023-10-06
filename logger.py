
import logging
from logging.handlers import RotatingFileHandler

from automators.utils.logger import Logging as AutomatorLogging


def list_loggers_handlers():
    return {logging.getLogger(name): logging.getLogger(name).handlers for name in logging.root.manager.loggerDict}


def setupLogger(filename: str = 'logs.log', maxMB: float = 10, backupCount: int = 5):
    # External libs
    logging.getLogger('urllib3').setLevel(logging.INFO)
    logging.getLogger('uiautomator2').setLevel(logging.INFO)
    # Just leave these components unlogged. They behave strangely.
    # uvicorn.error, uvicorn.access, uiautomator2.client, logzero, logzero_default
    
    AutomatorLogging.enable()
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    handler = RotatingFileHandler(filename=filename, encoding='utf-8', mode='a', maxBytes=int(maxMB*(1024*1024)), backupCount=backupCount)
    FMT = logging.Formatter(fmt='[%(asctime)s,%(msecs)d %(levelname)s %(threadName)s:%(name)s:%(filename)s:%(lineno)d] %(message)s',
                            datefmt='%d-%m-%Y %H:%M:%S')
    handler.setFormatter(FMT)
    root_logger.addHandler(handler)
