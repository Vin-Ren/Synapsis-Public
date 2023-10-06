
from typing import Literal
from fastapi import HTTPException, status
from fastapi_class.decorators import get, post, put

from automators.data_structs import Config

from .base import BaseAPIRouter
from .utils import recursive_auto_resolve
from .models import GenericResponse, ConfigWrapper
from .tags import tags


class ConfigurationRouter(BaseAPIRouter):
    ROUTE_PREFIX = '/configuration'
    TAGS = [tags.CONFIGURATION]
    def __init__(self, api, app):
        super().__init__(api, app)
        self._config = self.app.CONFIG
        self.config_filename = self.api.CONFIG_FILENAME
        self.config_file_format = self.api.CONFIG_FILE_FORMAT
    
    def refresh_config_info(self):
        self.config_filename = self.api.CONFIG_FILENAME
        self.config_file_format = self.api.CONFIG_FILE_FORMAT
    
    @property
    def config(self):
        return self._config
    
    @config.setter
    def config(self, new_config: Config):
        self._config = new_config
        self.app.CONFIG = new_config
    
    @get("/app", summary="Gets root config", description="Gets root config", response_model=ConfigWrapper)
    def get_root_config(self):
        return {'config': recursive_auto_resolve(self.config)}
    
    @get("/app/{config_path:path}", summary="Gets specific config", description="Gets specific config", response_model=ConfigWrapper)
    def get_config(self, config_path: str):
        if len(config_path) <= 0:
            return self.get_root_config()
        accessors = [l for l in config_path.split('/') if len(l) > 0]
        traversed = []
        conf = self.config
        try:
            while len(accessors):
                level = accessors.pop(0)
                traversed.append(level)
                conf = conf[level]
            return {'config': conf}
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No config found at path '{}'.".format("/".join(traversed)))
    
    @put("/app", summary="Updates and reload current app config", description="Updates and reload current app config", response_model=GenericResponse, tags=[tags.DANGEROUS])
    def update_root_config(self, config: dict, replace: bool = False):
        if replace:
            config = Config(config)
        else:
            config = Config(self.config, **config)

        try:
            config = Config(config)
            self.app.configure(config)
            self.config = config
            return {'status': True, 'detail': '{} config and reconfigured app successfully.'.format('Replaced' if replace else 'Updated')}
        except Exception as exc:
            self.app.configure(self.config)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provided config can not configure app correctly.")
    
    @put("/app/{config_path:path}", summary="Updates and reload specified config", description="Updates and reload specified config", response_model=GenericResponse, tags=[tags.DANGEROUS])
    def update_config(self, config_path: str, config: dict, replace: bool = False):
        updater_config = Config(config)
        root_config = Config(self.config.copy())
        config = root_config
        
        accessors = [l for l in config_path.split('/') if len(l) > 0]
        to_update = accessors.pop() # last accessor, it is fine if it does not exists
        traversed = []
        try:
            while len(accessors):
                level = accessors.pop(0)
                traversed.append(level)
                config = config[level]
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No config found at path '{}'.".format("/".join(traversed)))
        
        if replace:
            config[to_update] = updater_config
        else:
            config[to_update] = config.get(to_update, Config())
            config[to_update].update(updater_config)
        
        try:
            self.app.configure(root_config)
            self.config = root_config
            return {'status': True, 'detail': "{} config at path '{}' and reconfigured app successfully.".format('Replaced' if replace else 'Updated', config_path)}
        except Exception as exc:
            self.app.configure(self.config)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provided config can not configure app correctly.")
    
    @post("/save", summary="Saves current config to file", description="Saves current config to file", response_model=GenericResponse, tags=[tags.DANGEROUS])
    def save_config(self, filename: str = '', file_format: Literal['json', 'yaml', ''] = ''):
        try:
            filename = filename or self.config_filename
            file_format = file_format or self.config_file_format # type: ignore
            if file_format in ['json']:
                self.config.to_json(filename)
            elif file_format in ['yml', 'yaml']:
                self.config.to_yaml(filename)
            return {'status': True, 'detail': "Saved config to file='{}' with format='{}'.".format(filename, file_format)}
        except Exception as exc:
            return {'status': False, 'detail': 'Exception<{}{}> caught when trying to create file.'.format(exc.__class__, exc.args)}
    
    @put("/reload", summary="Reloads config", description="Reloads config", response_model=GenericResponse)
    def reload_config(self):
        try:
            self.app.configure(self.config)
            return {'status': True, 'detail': 'Reconfigured app.'}
        except Exception as exc:
            return {'status': False, 'detail': 'Exception<{}{}> caught when trying to reconfigure app.'.format(exc.__class__, exc.args)}

    @put("/reload_file", summary="Reload config from file", description="Reload config from file. Param filename if supplied will load from that file instead, otherwise load from config_filename.", response_model=GenericResponse, tags=[tags.DANGEROUS])
    def reload_config_from_file(self, filename: str = ''):
        try:
            filename = filename or self.config_filename
            config = Config.from_file(filename)
            self.app.configure(self.config)
            self.config = config
            return {'status': True, 'detail': "Reloaded config from file '{}' and reconfigured app.".format(filename)}
        except Exception as exc:
            self.app.configure(self.config)
            return {'status': False, 'detail': 'Exception<{}{}> caught when trying to reconfigure app. Reconfigured app with previous config.'.format(exc.__class__, exc.args)}
