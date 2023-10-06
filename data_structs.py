
from queue import Queue
from typing import Optional
from automators.request import Request as AutomatorRequest
from automators.result import Result
from server.request import Request as ServerRequest


class CallbackableQueue(Queue):
    def __init__(self, maxsize: int = 0, get_callback = lambda *_:None):
        super().__init__(maxsize)
        self.get_callback = get_callback
    
    def get(self, block=True, timeout=None):
        item = super().get(block, timeout)
        self.get_callback(item)
        return item


class InteractibleRequest(AutomatorRequest):
    def __init__(self, number, product_spec, automator='', device='', server_request=None, **kw):
        super().__init__(number, product_spec, automator, device)
        self.server_request: Optional[ServerRequest] = server_request
    
    def reply(self, message):
        self.server_request.reply(message)


class InteractibleResult(Result):
    def __init__(self, number, product_spec, refID=None, time=None, description=None, error=None, automator=None, execution_duration=-1, request=None, **kwargs):
        super().__init__(number, product_spec, refID, time, description, error, automator, execution_duration, request, **kwargs)
        self.request: Optional[InteractibleRequest]

    def reply(self, message):
        self.request.server_request.reply(message)
