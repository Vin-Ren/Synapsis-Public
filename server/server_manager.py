from queue import Queue
from threading import Thread
import time
import logging

from .jabber import JabberServer

# Type hint only
try:
    from automators.data_structs import Config
except:
    pass

logger = logging.getLogger(__name__)


class ServerManager:
    KEEP_ALIVE_SLEEP_DURATION = 10
    SERVERS = [JabberServer]
    CREDENTIALS = {}
    CONFIG: 'Config'
    
    def __init__(self, request_out: Queue):
        cls = self.__class__
        self.request_out = request_out
        self.servers = {server_cls.SERVER_NAME: server_cls(self.request_out, self.CREDENTIALS[server_cls.SERVER_NAME]) for server_cls in cls.SERVERS}
        self.runner_threads = {name: Thread(target=server.run, daemon=True) for name, server in self.servers.items()}
        self._stop = False
    
    @property
    def stop(self):
        return self._stop
    
    @stop.setter
    def stop(self, value: bool):
        self._stop = value
        [setattr(srv, 'stop', value) for srv in self.servers.values()]
        if value:
            stopped_threads = [name for name, thread in self.runner_threads.items() if not thread.is_alive()]
            new_runners = {name: Thread(target=self.servers[name].run, daemon=True) for name in stopped_threads}
            [thread.run() for thread in new_runners.values()]
            self.runner_threads.update(new_runners)
    
    @property
    def server_shards(self):
        return {name: srv.shards_identifiers for name, srv in self.servers.items()}
    
    @classmethod
    def configure(cls, config: 'Config'):
        cls.CONFIG = config
        cls.KEEP_ALIVE_SLEEP_DURATION = config.get('keep_alive_sleep_duration', cls.KEEP_ALIVE_SLEEP_DURATION)
        for server in cls.SERVERS:
            conf = config.get(server.SERVER_NAME, {})
            server.configure(conf)
            cls.CREDENTIALS[server.SERVER_NAME] = [server.CREDENTIAL_CLS.from_dict(cred) for cred in conf.get('credential_list', [])]
    
    def add_contact(self, server_name: str, shard_identifier: str, user_iddentifier: str) -> bool:
        """Calls add contact method of the server."""
        server = self.servers.get(server_name)
        if server is None:
            return False
        return server.add_contact(shard_identifier, user_iddentifier)
    
    def remove_contact(self, server_name: str, shard_identifier: str, user_iddentifier: str) -> bool:
        """Calls remove contact method of the server."""
        server = self.servers.get(server_name)
        if server is None:
            return False
        return server.remove_contact(shard_identifier, user_iddentifier)
    
    def restart_server(self, server_name):
        try:
            server = self.servers.pop(server_name)
            server_cls = server.__class__
        except KeyError:
            return
        logger.info("Restarting server '{}'.".format(server_name))
        server.stop = True
        logger.info("Set server '{}'.stop -> True. Waiting for it to exit...".format(server_name))
        del server
        self.runner_threads[server_name].join()
        logger.info("Server '{}' stopped. Initializing another server object and starting it...".format(server_name))
        self.servers[server_cls.SERVER_NAME] = server_cls(self.request_out, self.CREDENTIALS[server_cls.SERVER_NAME])
        self.runner_threads[server_name] = Thread(target=self.servers[server_cls.SERVER_NAME].run, daemon=True)
        self.runner_threads[server_name].start()
        logger.info("Server '{}' Restarted.".format(server_name))
    
    def run(self):
        [thread.start() for thread in self.runner_threads.values()]
        while True:
            time.sleep(self.__class__.KEEP_ALIVE_SLEEP_DURATION)
            if self.stop:
                logger.info("ServerManager is stopped by signal.")
                return
