from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app import App
    from api import API

from fastapi import FastAPI
from fastapi_class.routable import Routable


class BaseAPIRouter(Routable):
    ROUTE_PREFIX = ''
    TAGS = []
    def __init__(self, api: 'API', app: 'App'):
        super().__init__()
        self.api = api
        self.app = app
    
    def register_router(self, fast_api_instance: FastAPI):
        cls = self.__class__
        fast_api_instance.include_router(self.router, prefix=cls.ROUTE_PREFIX, tags=cls.TAGS)
