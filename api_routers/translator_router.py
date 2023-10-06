import os
from typing import List, Literal

import yaml
from fastapi import File, HTTPException, status
from fastapi.responses import FileResponse
from fastapi_class.decorators import get, post, put

from translator import i18n

from .base import BaseAPIRouter
from .models import GenericResponse
from .tags import tags


class TranslatorRouter(BaseAPIRouter):
    ROUTE_PREFIX = '/translator'
    TAGS = [tags.TRANSLATOR]
    def __init__(self, api, app):
        super().__init__(api, app)
        self.translator = i18n.TranslatorGroup()
    
    @get("/", summary="Lists all translations available", description="Lists all translations available")
    def get_all_keys(self):
        return {locale: list(translations) for locale, translations in i18n.translations.container.items()}
    
    def get_namespace_to_file_dict(self, path_list: List[os.PathLike]):
        remove_ext = lambda s: s[::-1].split('.',1)[1][::-1] # reverse name, remove extension, reverse name back
        data = {}
        for path in path_list:
            for name in os.listdir(path):
                data[remove_ext(name)] = os.path.join(path, name)
        return data
    
    @get("/namespaces", summary="Lists all available namespace", description="Lists all available namespace")
    def get_all_namespaces(self):
        return {'namespaces': list(self.get_namespace_to_file_dict(i18n.load_path).keys())}
    
    @get("/namespaces/{namespace}/file", summary="Returns the namespace file", description="Returns the namespace file")
    def get_namespace_file(self, namespace: str):
        try:
            return FileResponse(self.get_namespace_to_file_dict(i18n.load_path)[namespace])
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Namespace '{}' is not available.".format(namespace))
    
    @post("/namespaces/{namespace}/file", summary="Upload a new namespace file", description="Upload a new namespace file. Namespace file must be of format yaml.", tags=[tags.DANGEROUS])
    def upload_namespace_file(self, namespace: str, file: bytes = File(b''), replace_exists: bool = False):
        try:
            data = yaml.load(file, yaml.Loader)
            if not isinstance(data, (dict, list)):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='File is not of valid translation format.')
            elif len(data) < 1:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Translation file can not be empty.')
        except yaml.error.YAMLError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Translation file is not valid yaml.')
        
        available_namespaces = self.get_namespace_to_file_dict(i18n.load_path)
        if namespace in available_namespaces:
            file_path = available_namespaces[namespace]
            if not replace_exists:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Namespace already exists. set replace_exists flag=true to replace.')
        else:
            file_path = os.path.join(i18n.load_path[0], namespace+'.yaml')
            
        try:
            with open(file_path, 'wb') as fl:
                fl.write(file)
            return {'status': True, 'detail': "Namespace '{}' successfully added.".format(namespace)}
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Namespace '{}' is not available.".format(namespace))
    
    @get("/locales/{locale}", summary="Lists all translations available in the given locale", description="Lists all translations available in the given locale")
    def get_locale_keys(self, locale: Literal['id', 'en']):
        try:
            return i18n.translations.container[locale]
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locale '{}' is not available.".format(locale))
    
    @get("/translate", summary="Calls the translate method", description="Calls the translate method. Translation key format: 'namespace.key'")
    def get_translation(self, key: str, locale: Literal['id', 'en'] = 'en'):
        return {'translation': i18n.t(key=key, locale=locale)}
    
    @post("/add", summary="Add a new translation key", description="Add a new translation key for current session, not saved to file. translation key format: 'namespace.key'", response_model=GenericResponse, tags=[tags.DANGEROUS])
    def add_translation(self, key: str, value: str, locale: Literal['id', 'en'] = 'en'):
        try:
            i18n.add_translation(key, value=value, locale=locale)
            return {'status': True, 'detail': "Translation '{}' added.".format(key)}
        except Exception as exc:
            return {'status': False, 'detail': 'Exception<{}{}> caught when trying to add translation.'.format(exc.__class__, exc.args)}
    
    @put("/reset_all", summary="Resets all loaded translation", description="Resets all loaded translation", response_model=GenericResponse)
    def reset_all(self):
        try:
            translator = i18n.TranslatorGroup()
            translator.reset(all_locale=True)
            del translator
            return {'status': True, 'detail': "Successfully reset translations."}
        except Exception as exc:
            return {'status': False, 'detail': 'Exception<{}{}> caught when resetting translations.'.format(exc.__class__, exc.args)}
