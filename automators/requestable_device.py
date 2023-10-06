
import cProfile
import pstats
import time
from queue import Empty, Queue
from typing import Optional

from automators.plugabble_device import PluggableDevice
from automators.data_structs import Config
from automators.plugins import *
from automators.request import Request
from automators.result import Result
from automators.utils.logger import Logging

logger = Logging.get_logger(__name__)


class RequestableDevice(PluggableDevice): # not a good name but ok.
    PLUGINS = {'linkaja': LinkajaAutomator, 'digipos': DigiposAutomator, 'mitra_tokopedia': MitraTokopediaAutomator}
    DEFAULT_AUTOMATOR = 'linkaja'
    REQUEST_POLLING_RATE = 0.5
    ENABLE_PROFILER = False # For testing
    
    def __init__(self, *args, request_queue: Queue[Request], results_queue: Queue[Result], **kwargs):
        super().__init__(*args, **kwargs)
        self.request_queue = request_queue
        self.results_queue = results_queue
        self.current_request: Optional[Request] = None
        self.is_offline = False
        self.stop = False
    
    @classmethod
    def configure(cls, config: Config):
        super().configure(config)
        cls.REQUEST_POLLING_RATE = config.get('request_polling_rate', cls.REQUEST_POLLING_RATE)
        cls.DEFAULT_AUTOMATOR = config.get('default_automator', cls.DEFAULT_AUTOMATOR)
        cls.ENABLE_PROFILER = config.get('enable_profiler', cls.ENABLE_PROFILER)
    
    def get_info(self, detailed=False):
        data = super().get_info(detailed=detailed)
        data['current_request'] = self.current_request
        return data
    
    def processRequest(self, request:Request):
        automator = self.plugins.get(request.automator or self.__class__.DEFAULT_AUTOMATOR) # defaults to LinkajaAutomator
        assert(automator) # assert it is not None
        self.current_request = request
        try:
            self.wakeUp()
            if self.__class__.ENABLE_PROFILER: # only for testing purposes
                start=time.time()
                with cProfile.Profile() as profiler:
                    res = automator.processRequest(request)
                end=time.time()
                res.execution_duration=int(end-start)
                pstats.Stats(profiler).dump_stats(filename=time.strftime("%b_%d_%H_%M")+'.prof')
            else:
                start=time.time()
                res = automator.processRequest(request)
                end=time.time()
                res.execution_duration=int(end-start)
            self.sleep()
        except Exception as exc:
            self.current_request=None
            raise exc
        self.current_request=None
        return res
    
    def run(self):
        """A while true loop, waiting for requests to be fulfilled and put result into the result queue."""
        self.is_offline = False
        while True:
            try:
                time.sleep(self.__class__.REQUEST_POLLING_RATE)
                if self.stop:
                    break
                if self.request_queue.empty():
                    continue
                req: 'Request' = self.request_queue.queue[0]
                if (req.automator or self.__class__.DEFAULT_AUTOMATOR) not in self.plugins:
                    continue
                if len(req.device) > 0 and req.device != self.serial:
                    continue
                request = self.request_queue.get()
            except (Empty, IndexError): # Empty from Queue.get, IndexError from Queue.queue[0]
                continue
            
            try:
                result = self.processRequest(request)
                self.results_queue.put(result)
            except Exception as exc:
                device_offline = isinstance(exc, RuntimeError) and 'offline' in (exc.args+('',))[0]
                if device_offline:
                    logger.info("Device %s is offline" % self.serial)
                else:
                    logger.debug("Unexpected exception: {}: {}".format(type(exc), str(exc)))
                    logger.exception(exc)
                if self.processing_request: # so if device is processing then its requeue-able.
                    logger.info("Re-queueing an unfulfilled request. Request={}".format(request))
                    print("A transaction is not processed yet, putting it back into queue.")
                    self.request_queue.put(request)
                if device_offline:
                    self.is_offline = True
                    return # stops the device handler.
