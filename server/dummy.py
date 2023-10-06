from .request import Request
from .base import BaseServer


class DummyServer(BaseServer):
    """Dummy server for creating requests from api."""
    def __init__(self, *args, **kwargs):
        pass
    
    @classmethod
    def configure(cls, config):
        pass
    
    @property
    def shards_identifiers(self):
        pass
    
    def create_request(self, *args, **kwargs):
        return Request(self, 'dummy_request', 'DummyServer', {})
    
    def reply(self, *args, **kwargs):
        pass
    
    def add_contact(self, shard_identifier: str, user_identifier: str):
        pass
    
    def remove_contact(self, shard_identifier: str, user_identifier: str):
        pass
    
    def run(self):
        pass
    
    def stop(self):
        pass
