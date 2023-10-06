from dataclasses import dataclass
import abc
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from automators.data_structs import Config


@dataclass
class Credentials:
    "Credentials to log into the account serving as a server/shard interface."
    username: str
    password: str
    
    @classmethod
    def from_dict(cls, dct):
        return cls(dct['username'], dct['password'])


class BaseShard:
    """Rough structure of possible shard. You can deviate from this, as there is no integration with such structure."""
    def __init__(self, credentials: Credentials, masterServer: 'BaseServer', **kwargs):
        """Do your shard initialization here"""
    
    def run(self):
        """This runs your shard"""


class BaseServer:
    "Base structure for any server, should be followed."
    SERVER_NAME = 'base' # all lower case
    CREDENTIAL_CLS = Credentials
    CONFIG: 'Config'
    
    def __init__(self, transaction_queue, credential_list):
        self.transaction_queue = transaction_queue
        self.credential_list = credential_list
        self._stop = False
    
    @property
    def stop(self):
        return self._stop
    
    @stop.setter
    def stop(self, value: bool):
        self._stop = value
    
    @classmethod
    def configure(cls, config: 'Config'):
        """Configure class variables with config."""
        cls.CONFIG = config
    
    @property
    @abc.abstractmethod
    def shards_identifiers(self) -> List[str]:
        """Returns list of shards user identifiers. user_identifier, but for the server shards."""
    
    @abc.abstractmethod
    def reply(self, reply_message: str, interaction_data: dict):
        """Reply to a given message with reply_message as its reply. 
        interaction_data is used to store data for interacting e.g: replying. Structure of interaction_data is not specified/restrained at all."""
    
    @abc.abstractmethod
    def add_contact(self, shard_identifier: str, user_identifier: str) -> bool:
        """Registers an user to the shard's list of contact if available. 
        Returns whether the user is registered successfully or not. 
        Does not interface with database."""
    
    @abc.abstractmethod
    def remove_contact(self, shard_identifier: str, user_identifier: str) -> bool:
        """Unregister user from the shard's list of contact if available. 
        Returns whether the user is unregistered successfully or not. 
        Does not interface with database."""
    
    @abc.abstractmethod
    def run(self):
        """A runner function, usually will be run with a seperate thread. If self.stop is true, stops itself."""
