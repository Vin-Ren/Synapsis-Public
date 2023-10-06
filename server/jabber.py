
import logging
import time
from datetime import datetime
from typing import Dict, List, Tuple, Callable, TYPE_CHECKING
from dataclasses import dataclass
import threading

import xmpp
from xmpp.protocol import InvalidFrom

from server.base import BaseServer
from server.request import Request

if TYPE_CHECKING:
    from automators.data_structs import Config


def StepOn(conn):
    try:
        conn : xmpp.dispatcher.Dispatcher
        if conn.isConnected():
            conn.Process(1)
    except KeyboardInterrupt:
        raise
    return 1

def KeepAlive(conn):
    while StepOn(conn): pass


logger = logging.getLogger(__name__)


class JabberClient:
    def __init__(self, jid, password, debug=[]):
        self.jid = jid
        self.password = password
        self.debug = debug
        self.JID = xmpp.protocol.JID(self.jid)
        self.xmpp: xmpp.Client = None
        self.connection_keeper = None
        self.initXMPP()
        logger.debug("Jabber Client Initialized. jid={} JID={} Password={} Debug={}".format(self.jid, self.JID, '*'*len(self.password), self.debug))

    def __repr__(self):
        return "<{} Object JID={}>".format(self.__class__.__name__, self.jid)
    
    @property
    def nick(self):
        return "<{}>".format(self.jid)

    def initXMPP(self):
        if self.xmpp:
            del self.xmpp
        self.JID = xmpp.protocol.JID(self.jid)
        self.xmpp = xmpp.Client(self.JID.getDomain(), debug=self.debug)
        logger.debug("XMPP Client initialized. self.xmpp={} jid={}".format(self.xmpp, self.jid))

    def handlerRegisterer(self, handlers: List[Tuple[str, Callable]]):
        for name, handler in handlers:
            self.xmpp.RegisterHandler(name, handler) # the RegisterHandler will somehow be added after connecting
        return

    def keepConnectionAlive(self, pooling_rate=120):
        while True:
            try:
                while self.xmpp.isConnected():
                    self.xmpp.sendPresence(requestRoster=1) # sendPresence first, so after isConnected is checked sendPresence can be executed.
                    #self.xmpp.Process(pooling_rate)
                    [StepOn(conn=self.xmpp) for _ in range(pooling_rate)]
                logger.debug(f"{self.nick} XMPP client disconnected. trying to reconnect...")
                self.reconnectXMPP()
            except (IOError, OSError, ConnectionResetError) as err:
                print('{} Disconnected from server with error, reinitializing and reconnecting XMPP.'.format(self.nick))
                logger.debug("{} XMPP disconnected with error={}. Reinitializing and reconnecting XMPP.".format(self.nick, str(err)))
                try:
                    self.initAndConnectXMPP()
                except Exception as exc:
                    logger.exception(exc)
            except InvalidFrom:
                pass
            except Exception as err:
                print('{} Disconnected from server with error, reinitializing and reconnecting XMPP.'.format(self.nick))
                logger.debug("{} XMPP disconnected with error={}. Reinitializing and reconnecting XMPP.".format(self.nick, str(err)))
                logger.exception(err)
                try:
                    self.initAndConnectXMPP()
                except Exception as exc:
                    logger.exception(exc)
                    time.sleep(15)
            except KeyboardInterrupt:
                break

    def reconnectXMPP(self):
        maxTries, tries = 3, 0
        while not self.xmpp.isConnected() and tries < maxTries:
            print("[{}] {} Client Reconnecting and reauth... {}".format(datetime.now().strftime('%y-%m-%d %H:%M:%S'), self.nick, '' if tries == 0 else '({})'.format(tries)))
            logger.debug("reconnectXMPP: {} try#{} to reconnect and reauth...".format(self.nick, tries+1))
            self.xmpp.reconnectAndReauth()
            self.xmpp.sendInitPresence()
        if self.xmpp.isConnected():
            logger.debug("reconnectXMPP: {} XMPP client reconnected and reauthenticated on try#{}.".format(self.nick, tries+1))
            print("[{}] {} Client Reconnected and reauthenticated.".format(datetime.now().strftime('%y-%m-%d %H:%M:%S'), self.nick))
        else:
            logger.debug("reconnectXMPP: {} XMPP client failed to reconnected and reauthenticated after {} tries.".format(self.nick, tries+1))
            print("[{}] {} Client Failed to reconnect and reauthenticate.".format(datetime.now().strftime('%y-%m-%d %H:%M:%S'), self.nick))
        if not self.onDisconnect in self.xmpp.disconnect_handlers:
            self.xmpp.RegisterDisconnectHandler(self.onDisconnect)
        logger.debug("reconnectXMPP: {} Client successfully reconnect xmpp client.".format(self.nick))
        return self.xmpp.isConnected()

    def initAndConnectXMPP(self, recursed=0):
        max_recursion = 3
        logger.debug("initAndConnectXMPP: {} reinitializing XMPP...".format(self.nick))
        self.initXMPP()
        maxTries, tries = 15, 0
        while tries < maxTries:
            try:
                logger.debug("initAndConnectXMPP: {} Client try#{} reconnecting XMPP...".format(self.nick, tries+1))
                conn_res = self.xmpp.connect()
                if not conn_res:
                    tries += 1
                    continue
                logger.debug("initAndConnectXMPP: {} authenticating client...".format(self.nick))
                self.xmpp.auth(user=self.JID.getNode(), password=self.password, resource=self.JID.getResource())
                self.handlerRegisterer([('message', self.on_message)])
                self.xmpp.RegisterDisconnectHandler(self.onDisconnect)
                self.xmpp.sendInitPresence()
                logger.debug("initAndConnectXMPP: {} sent init presence.".format(self.nick))
                print("[{}] Jabber Connected.".format(datetime.now().strftime('%y-%m-%d %H:%M:%S')))
                logger.debug("initAndConnectXMPP: {} Connected!".format(self.nick))
                break
            except AttributeError as exc:
                logger.exception(exc)
                if max_recursion <= recursed:
                    raise RuntimeError("Recursion limit reached.")
                return self.initAndConnectXMPP(recursed+1)
            except xmpp.protocol.ConnectionTimeout:
                logger.debug("initAndConnectXMPP: connection timeout on try#{}".format(tries+1))
                continue

    def onDisconnect(self):
        logger.debug("{} XMPP Client Disconnected.".format(self.nick))
        print("[{}] {} Client Disconnected from server.".format(datetime.now().strftime('%y-%m-%d %H:%M:%S'), self.nick))

    def start(self):
        conn_res = self.xmpp.connect()
        if not conn_res:
            print("can not connect to server.")
        self.xmpp.auth(user=self.JID.getNode(), password=self.password, resource=self.JID.getResource())
        self.handlerRegisterer([('message', self.on_message)])
        self.xmpp.RegisterDisconnectHandler(self.onDisconnect)
        self.xmpp.sendInitPresence()
        logger.debug("{} XMPP client connected.".format(self.nick))
        print("[{}] {} Connected To Jabber.".format(datetime.now().strftime('%y-%m-%d %H:%M:%S'), self.nick))
        self.keepConnectionAlive(pooling_rate=240)

    def send_message(self, mto, mbody, mtyp=None, msubject=None, mfrom=None):
        msg = xmpp.protocol.Message(to=mto, body=mbody, typ=mtyp, subject=msubject, frm=mfrom)
        return self.xmpp.send(msg)

    def on_message(self, session: xmpp.dispatcher.Dispatcher, msg: xmpp.Message):
        """
        You Should Override This.
        """
        if msg.getType() in ('chat', 'normal'):
            # Direct way
            msg['body'] = msg.getBody()
            reply = msg.buildReply("Hello there {msg[from]}. Thanks for sending: {msg[body]}".format(msg=msg))
            self.xmpp.send(reply)


@dataclass
class JabberCredentials:
    jid: str
    password: str
    
    @classmethod
    def from_dict(cls, dct):
        return cls(dct['jid'], dct['password'])


class JabberShard(JabberClient):
    def __init__(self, credentials: JabberCredentials, masterServer: 'JabberServer', **kwargs):
        super().__init__(jid=credentials.jid, password=credentials.password)
        self.masterServer = masterServer
        self.run=self.start
    
    def send_presence(self):
        self.xmpp.sendPresence(jid='', requestRoster=1)
    
    def on_message(self, session, msg):
        return self.masterServer.on_message(msg, jid=self.jid)


class JabberServer(BaseServer):
    SERVER_NAME='jabber'
    CREDENTIAL_CLS=JabberCredentials
    KEEP_ALIVE_SLEEP_DURATION = 10
    CONFIG: 'Config'
    
    def __init__(self, transaction_queue, credential_list:List[JabberCredentials]):
        super().__init__(transaction_queue, credential_list)
        self.shards={credential.jid : JabberShard(credential, self) for credential in credential_list}
        self.shards_threads: Dict[str, threading.Thread] = {}
    
    @classmethod
    def configure(cls, config: 'Config'):
        cls.CONFIG = config
        cls.KEEP_ALIVE_SLEEP_DURATION = config.get('keep_alive_sleep_duration', cls.KEEP_ALIVE_SLEEP_DURATION)
    
    @property
    def shards_identifiers(self) -> List[str]:
        return list(self.shards.keys())
    
    def add_contact(self, shard_identifier: str, user_identifier: str):
        try:
            shard_roster = self.shards[shard_identifier].xmpp.getRoster()
            if shard_roster.getItem(user_identifier) is None and shard_roster.getItem(user_identifier).get('subscription', 'none') is None:
                shard_roster.Subscribe(user_identifier)
            else:
                shard_roster.Authorize(user_identifier)
            return True
        except:
            return False
    
    def remove_contact(self, shard_identifier: str, user_identifier: str):
        try:
            shard_roster = self.shards[shard_identifier].xmpp.getRoster()
            shard_roster.delItem(user_identifier)
            return True
        except:
            return False
    
    def run(self):
        self.shards_threads = {jid:threading.Thread(target=shard.run, daemon=True) for jid,shard in self.shards.items()}
        [t.start() for t in self.shards_threads.values()]
        print("Started Jabber Clients.")
        logger.info("Started Jabber Shards.")
        while True:
            time.sleep(self.__class__.KEEP_ALIVE_SLEEP_DURATION)
            if self.stop:
                logger.info("Server stopped.")
                return
    
    def reply(self, message, interaction_data):
        self.shards[interaction_data['server_jid']].xmpp.send(interaction_data['message'].buildReply(message))
    
    def send_presence(self):
        [shard.send_presence() for shard in self.shards.values()]
    
    def on_message(self, message:xmpp.protocol.Message, jid):
        message['body'] = message.getBody() # required, idk why the library doesn't put this 'body' key.
        
        user_obj = message.getFrom()
        user_identifier = "{}@{}".format(user_obj.getNode(), user_obj.getDomain())
        
        if message['type'] in ('chat', 'normal'):
            request = Request(self, message['body'], user_identifier, {'server_jid':jid, 'message':message})
            self.transaction_queue.put(request)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Simple Jabber Server.')
    parser.add_argument("-j", "--jid", dest="jid",
                        help="JID to use")
    parser.add_argument("-p", "--password", dest="password",
                        help="password to use")
    args = parser.parse_args()

    xmpp_client = JabberClient(args.jid, args.password)

    xmpp_client.start()

