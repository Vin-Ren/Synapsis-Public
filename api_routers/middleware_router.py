
from typing import List

from fastapi_class.decorators import get, post, put

from data_structs import InteractibleRequest
from server.dummy import DummyServer

from .base import BaseAPIRouter
from .models import RequestModel, GenericResponse
from .tags import tags


class MiddlewareRouter(BaseAPIRouter):
    ROUTE_PREFIX = '/middleware'
    TAGS = [tags.MIDDLEWARE]
    def __init__(self, api, app):
        super().__init__(api, app)
        self.request_middleware = self.app.request_middleware
        self.result_middleware = self.app.result_middleware
        self.dummy_server = DummyServer()
    
    @get("/request/list", summary="Gets pending requests", description="Gets pending requests", response_model=List[RequestModel])
    def list_request(self):
        q = self.request_middleware.out_queue
        return [req.dict for req in q.queue]
    
    @post("/request/create", summary="Creates a request", description="Creates a request", response_model=GenericResponse)
    def create_request(self, request:RequestModel):
        try:
            q = self.request_middleware.out_queue
            dummy_req = self.dummy_server.create_request()
            new_request = InteractibleRequest(request.number, request.product_spec, request.automator, device='', server_request=dummy_req)
            duplicate_status, opt_transaction = self.request_middleware.check_duplicate(new_request)
            if duplicate_status == 'in_queue':
                return {'status': False, 'detail': 'An existing request with the same parameters already exists.'}
            elif duplicate_status == 'in_process':
                return {'status': False, 'detail': 'An existing request with the same parameters is being processed.'}
            elif duplicate_status == 'in_cached_result':
                return {'status': False, 'detail': 'An existing request has been completed today.', 'detail_extra': {'transaction': opt_transaction.to_dict()}} # type: ignore
            else:
                self.request_middleware.out_queue.put(new_request)
                return {'status': True, 'detail': 'Request {} created.'.format(new_request)}
        except Exception as exc:
            return {'status': False, 'detail': 'Exception<{}{}> caught when trying to create request.'.format(exc.__class__, exc.args)}
    
    @put("/request/delete", summary="Deletes the request given", description="Deletes the request given", response_model=GenericResponse)
    def remove_request(self, request: RequestModel):
        try:
            q = self.request_middleware.out_queue
            q.queue.remove(InteractibleRequest(request.number, request.product_spec, request.automator))
            return {'status': True, 'detail': 'Removed corresponding request from request queue.'}
        except ValueError:
            return {'status': False, 'detail': 'Given request is not found in the request queue.'}
