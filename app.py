
import time
from queue import Queue
from threading import Thread
import logging

from automators.data_structs import Config
from automators.device_manager import DeviceManager
from server.server_manager import ServerManager

from api import API
from database import SynapsisDB
from data_structs import CallbackableQueue
from middlewares import RequestMiddleware, ResultMiddleware

logger = logging.getLogger(__name__)


class App:
    DATABASE_FILENAME = 'database.db'
    KEEP_ALIVE_SLEEP_DURATION = 10
    DUMMY_RUNTIME = 0
    
    CONFIG: Config
    API_CLS = API
    DEVICE_MANAGER_CLS = DeviceManager
    SERVER_MANAGER_CLS = ServerManager
    DATABASE_MANAGER_CLS = SynapsisDB # No configure method
    REQUEST_MIDDLEWARE_CLS = RequestMiddleware
    RESULT_MIDDLEWARE_CLS = ResultMiddleware
    
    def __init__(self):
        self.requests_in = Queue()
        self.requests_out = CallbackableQueue()
        self.results_out = Queue()
        self._stop = False
        
        cls = self.__class__
        
        logger.info("Initializing App...")
        self.server_manager = cls.SERVER_MANAGER_CLS(self.requests_in)
        self.device_manager = cls.DEVICE_MANAGER_CLS(self.requests_out, self.results_out)
        self.database_manager = cls.DATABASE_MANAGER_CLS(self.__class__.DATABASE_FILENAME)
        
        self.request_middleware = cls.REQUEST_MIDDLEWARE_CLS(self.device_manager, self.requests_in, self.requests_out)
        self.result_middleware = cls.RESULT_MIDDLEWARE_CLS(self.database_manager, self.results_out)
        self.api = cls.API_CLS(self)
        
        self.runner_threads = { 'api': Thread(target=self.api.run, name='API-Thread', daemon=True), 
                                'server_manager': Thread(target=self.server_manager.run, name='ServerManager-Thread', daemon=True),
                                'device_manager': Thread(target=self.device_manager.run, name='DeviceManager-Thread', daemon=True), 
                                'request_middleware': Thread(target=self.request_middleware.run, name='RequestMiddleware-Thread', daemon=True),
                                'result_middleware': Thread(target=self.result_middleware.run, name='ResultMiddleware-Thread', daemon=True)}
        logger.info("App Initialized.")
    
    @property
    def stop(self):
        return self._stop
    
    @stop.setter
    def stop(self, value):
        self._stop = value
        [setattr(obj, 'stop', value) for obj in [self.server_manager, self.device_manager]]
    
    @classmethod
    def configure(cls, config: Config):
        logger.info("Configuring App...")
        cls.CONFIG = config
        cls.DATABASE_FILENAME = config.get('database_filename', cls.DATABASE_FILENAME)
        cls.KEEP_ALIVE_SLEEP_DURATION = config.get('keep_alive_sleep_duration', cls.KEEP_ALIVE_SLEEP_DURATION)
        cls.DUMMY_RUNTIME = config.get('dummy_runtime', cls.DUMMY_RUNTIME)
        cls.API_CLS.configure(config['api'])
        cls.SERVER_MANAGER_CLS.configure(config['server_manager'])
        cls.DEVICE_MANAGER_CLS.configure(config['device_manager'])
        cls.REQUEST_MIDDLEWARE_CLS.configure(config['middlewares'])
        cls.RESULT_MIDDLEWARE_CLS.configure(config['middlewares'])
    
    def dummy_runner(self, runtime: int):
        logger.info("Setting up dummy server.".format(runtime))
        dummy_queue = Queue()
        dummy_server = self.__class__.SERVER_MANAGER_CLS(dummy_queue)
        dummy_runner_thread = Thread(target=dummy_server.run, name='DummyServer-Thread', daemon=True)
        print("Starting dummy server manager.")
        logger.info("Dummy server has been set up. Running dummy server...")
        dummy_runner_thread.start()
        time.sleep(runtime)
        print("Stopping dummy server manager.")
        logger.info("Dummy runtime fulfilled. Stopping dummy server...")
        return
    
    def run_dummy(self, runtime: int):
        Thread(self.dummy_runner(runtime)).run()
    
    def run(self):
        if self.__class__.DUMMY_RUNTIME > 0:
            logger.info("Dummy Runtime={} is greater than 0. Initializing dummy.".format(self.__class__.DUMMY_RUNTIME))
            self.run_dummy(self.__class__.DUMMY_RUNTIME)
        logger.info("Starting app...")
        
        for comp_name, thread in self.runner_threads.items():
            logger.info("Starting runner thread for Component<'{}'>".format(comp_name))
            thread.start()
        logger.info("All component has been started, starting keep alive.")
        while True: # Keep alive loop
            try:
                time.sleep(self.__class__.KEEP_ALIVE_SLEEP_DURATION)
                if self.stop:
                    logger.info("App is stopped by signal.")
                    return
            except KeyboardInterrupt:
                return
