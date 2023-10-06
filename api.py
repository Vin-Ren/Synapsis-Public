from fastapi import FastAPI
import uvicorn

from automators.data_structs import Config

from api_routers import DatabaseRouter, ServerRouter, DeviceRouter, MiddlewareRouter, ConfigurationRouter, TranslatorRouter, ProductRouter, UtilitiesRouter


class API:
    HOST = '0.0.0.0'
    PORT = 8080
    CONFIG: Config
    CONFIG_FILENAME = 'config.yaml'
    CONFIG_FILE_FORMAT = 'yaml'
    UVICORN_OPTS = {}
    
    ROUTERS = [DatabaseRouter, ServerRouter, DeviceRouter, MiddlewareRouter, ConfigurationRouter, TranslatorRouter, ProductRouter, UtilitiesRouter]
    
    def __init__(self, app):
        self.app = app
        self.fast_api = FastAPI()
        self.router_instances = [cls(self, self.app) for cls in self.__class__.ROUTERS]
        [instance.register_router(self.fast_api) for instance in self.router_instances]
    
    @classmethod
    def configure(cls, config: Config):
        cls.CONFIG = config
        cls.CONFIG_FILENAME = config.get('config_filename', cls.CONFIG_FILENAME)
        cls.CONFIG_FILE_FORMAT= config.get('config_file_format', cls.CONFIG_FILE_FORMAT)
        cls.HOST = config.get('host', cls.HOST)
        cls.PORT = config.get('port', cls.PORT)
        cls.UVICORN_OPTS = config.get('uvicorn_opts', cls.UVICORN_OPTS)
    
    def run(self):
        cls=self.__class__
        uvicorn.run(self.fast_api, host=cls.HOST, port=cls.PORT, **cls.UVICORN_OPTS)
