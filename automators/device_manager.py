import subprocess
import sys
from queue import Queue
from threading import Thread
import time

import adbutils

from automators.client import Client as BaseClient, lru_cache
from automators.data_structs import Config
from automators.requestable_device import RequestableDevice
from automators.utils.logger import Logging

logger = Logging.get_logger(__name__)


class Client(BaseClient):
    def __init__(self, *args, device_cls=RequestableDevice, request_queue: Queue = Queue(), results_queue: Queue = Queue(), **kwargs):
        super().__init__(*args, device_cls=device_cls, **kwargs)
        self.request_queue = request_queue
        self.results_queue = results_queue

    @lru_cache(maxsize=10)
    def get_device(self, serial: str):
        if issubclass(self.device_cls, RequestableDevice):
            return self.device_cls(self, serial, request_queue=self.request_queue, results_queue=self.results_queue)
        return super().get_device(serial)



class DeviceManager:
    CONFIG: Config
    
    ADB_PATH = 'adb'
    ADB_HOST = '127.0.0.1'
    ADB_PORT = 5037
    
    DEVICE_POLLING_RATE = 5
    DEVICE_CLS = RequestableDevice
    
    USE_INTERRUPTIBLE_RUNNER = False
    INTERRUPTIBLE_RUNNER_POLLING_RATE = 0.1
    
    def __init__(self, request_queue: Queue, results_queue: Queue):
        self.client = Client(self.__class__.ADB_HOST, self.__class__.ADB_PORT, device_cls=self.__class__.DEVICE_CLS, request_queue=request_queue, results_queue=results_queue)
        self.runner_threads = {} # serial:thread
        self.devices = [] # device objects
        self._stop = False
    
    @property
    def stop(self):
        return self._stop
    
    @stop.setter
    def stop(self, value):
        self._stop = value
        [setattr(device, 'stop', value) for device in self.devices]
    
    @classmethod
    def configure(cls, config: Config):
        cls.CONFIG = config
        cls.ADB_PATH = config.get('adb_path', cls.ADB_PATH)
        cls.ADB_HOST = config.get('adb_host', cls.ADB_HOST)
        cls.ADB_PORT = config.get('adb_port', cls.ADB_PORT)
        cls.DEVICE_POLLING_RATE = config.get('device_polling_rate', cls.DEVICE_POLLING_RATE)
        cls.USE_INTERRUPTIBLE_RUNNER = config.get('use_interruptible_runner', cls.USE_INTERRUPTIBLE_RUNNER)
        cls.INTERRUPTIBLE_RUNNER_POLLING_RATE = config.get('interruptible_runner_polling_rate', cls.INTERRUPTIBLE_RUNNER_POLLING_RATE)
        cls.DEVICE_CLS.configure(config['device']) # must exist
    
    @property
    def current_requests(self):
        return [d.current_request for d in self.devices if d.current_request is not None]
    
    @property
    def current_processing(self):
        return [d.serial for d in self.devices if d.current_request is not None]
    
    def adb_command(self, *args):
        return subprocess.run(["{}".format(self.__class__.ADB_PATH), *args], capture_output=True, shell=True)
    
    def restart_adb(self):
        self.adb_command("kill-server")
        return self.adb_command("start-server").returncode == 0
    
    def get_device(self, serial: str):
        return ([device for device in self.devices if device.serial == serial] + [None])[0]
    
    def _handle_device(self, device: RequestableDevice):
        """Wrapper for device.run"""
        device.run()
    
    def handle_device(self, device: RequestableDevice):
        """Wrapper for _handle_device, adds support for interruptible runner."""
        if self.__class__.USE_INTERRUPTIBLE_RUNNER:
            thread = Thread(target=self._handle_device, args=(device,))
            thread.start()
            while not (device.stop or device.is_offline):
                time.sleep(self.__class__.INTERRUPTIBLE_RUNNER_POLLING_RATE)
        else:
            self._handle_device(device)
        self.runner_threads.pop(device.serial)
        logger.info("Handler for device '{}' has been stopped.".format(device.serial))
    
    def run(self):
        while True:
            try:
                self.devices=self.client.devices()
                if self.stop:
                    logger.info("DeviceManager is stopped by signal.")
                    return
                for device in self.devices:
                    if device.serial in self.runner_threads:
                        continue
                    if device.stop:
                        continue
                    device.refresh_plugins()
                    device.is_offline = False
                    thread = Thread(target=self.handle_device, args=(device,), daemon=True)
                    self.runner_threads[device.serial] = thread
                    logger.info("Handler for device '{}' has been started.".format(device.serial))
                    thread.start()
                time.sleep(self.__class__.DEVICE_POLLING_RATE)
            except RuntimeError as exc:
                logger.info("Catched a runtime error. Restarting ADB server...")
                logger.exception("Exception: {}{}".format(exc.__class__, exc.args), exc_info=sys.exc_info())
                self.restart_adb()
            except adbutils.AdbError as exc:
                logger.info("Catched an ADB error. Restarting ADB server...")
                self.restart_adb()
            except Exception as exc:
                logger.exception("Catched an exception of type=<{}>.".format(exc.__class__), exc_info=sys.exc_info())
                time.sleep(1)
