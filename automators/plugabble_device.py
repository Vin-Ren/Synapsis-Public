
from automators.data_structs import Config
from automators.plugins.base import BasePlugin
from automators.device import Device
from automators.utils.logger import Logging

logger = Logging.get_logger(__name__)


class PluggableDevice(Device):
    CONFIG: Config
    PLUGINS = {'__base__': BasePlugin} # Dummy plugin data, change this for use.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        app_list = self.u2_device.app_list()
        self.plugins = {name: plugin(self) for name, plugin in self.__class__.PLUGINS.items() if len(plugin.PACKAGE) and plugin.PACKAGE in app_list}
    
    def refresh_plugins(self):
        app_list = self.u2_device.app_list()
        self.plugins = {name: plugin(self) for name, plugin in self.__class__.PLUGINS.items() if len(plugin.PACKAGE) and plugin.PACKAGE in app_list}
    
    @classmethod
    def configure(cls, config: Config):
        cls.CONFIG = config
        [plugin_cls.configure(config.get('automators', {}).get(name, {})) for name, plugin_cls in cls.PLUGINS.items()]
