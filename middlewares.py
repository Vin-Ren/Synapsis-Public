
from datetime import datetime
from queue import Queue, Empty
import logging

from automators.data_structs import Config
from automators.device_manager import DeviceManager
from server.request import Request as ServerRequest

from database import SynapsisDB, Transaction, User
from data_structs import CallbackableQueue, InteractibleRequest, InteractibleResult
from translator import Translator

logger = logging.getLogger(__name__)


def parse_request(message):
    message=message.upper()
    mess = [x[::-1] for x in message[::-1].split('.',2)[::-1]] # [::-1] to reverse a list or string, to preserve a product_spec with a '.' in it.
    keys = ['product_spec', 'number', 'pin'] # Format='<prod>[.number][.pin]'
    return dict(zip(keys, mess))


def time_formatter(time:int):
    if time<0:
        return "ERR"
    hours, time = divmod(time, 60*60)
    minutes, seconds = divmod(time, 60)
    comps = []
    if hours>0:
        comps.append('{}h'.format(hours))
    if minutes>0:
        comps.append('{}m'.format(minutes))
    if seconds>0:
        comps.append('{}s'.format(seconds))
    return " ".join(comps)


def _print(*args, **kwargs):
    print("[{}]".format(datetime.now().replace(microsecond=0).isoformat()),*args, **kwargs)


class RequestMiddleware:
    AUTOMATOR_PREFIX_MAPPING = {'L':'linkaja', 'D':'digipos', 'M':'mitra_tokopedia'}
    AUTOMATOR_REVERSE_PREFIX_MAPPING = {v:k for k,v in AUTOMATOR_PREFIX_MAPPING.items()}
    TRANSLATOR: Translator = Translator()
    CONFIG: Config
    
    def __init__(self, device_manager: DeviceManager, in_queue: Queue[ServerRequest], out_queue: CallbackableQueue):
        self.device_manager = device_manager
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.out_queue.get_callback = self.request_out_callback
    
    @classmethod
    def configure(cls, config: Config):
        cls.CONFIG = config
        cls.AUTOMATOR_PREFIX_MAPPING = {k.upper():v.lower() for k,v in config.get('automator_prefix_mapping', cls.AUTOMATOR_PREFIX_MAPPING).items()}
        cls.AUTOMATOR_REVERSE_PREFIX_MAPPING = {v:k for k,v in cls.AUTOMATOR_PREFIX_MAPPING.items()}
        cls.TRANSLATOR = Translator(**config['translator_config'])
    
    @property
    def t(self):
        return self.__class__.TRANSLATOR
    
    def request_out_callback(self, request: InteractibleRequest):
        status_str = "Handling request for [{}] {}".format(request.server_request.user_identifier, str(request))
        logger.info(status_str)
        _print(status_str)
        request.server_request.reply(self.t('transaction_is_being_processed').format(message_content=request.server_request.request))
    
    def select_automator(self, product_spec: str):
        return self.__class__.AUTOMATOR_PREFIX_MAPPING.get(product_spec.upper(), '')
    
    def make_automator_request(self, req: ServerRequest):
        data = parse_request(req.request)
        data['automator'] = self.__class__.AUTOMATOR_PREFIX_MAPPING.get(data['product_spec'][0], '')
        if data['automator'] != '':
            data['product_spec'] = data['product_spec'][1:]
        data['server_request'] = req
        return InteractibleRequest(**data)
    
    def get_full_product_spec(self, req: InteractibleRequest):
        return '{}{}'.format(self.__class__.AUTOMATOR_REVERSE_PREFIX_MAPPING.get(req.automator, ''), req.product_spec)
    
    def get_message_content_from_transaction(self, transaction: Transaction):
        req_obj = InteractibleRequest(**transaction.to_dict())
        req_obj.product_spec=self.get_full_product_spec(req_obj)
        return self.t('message_content').format(req=req_obj)
    
    def check_user(self, req: ServerRequest):
        res = list(User.get(User.server == req.server.SERVER_NAME.lower(), User.identifier == req.user_identifier))
        return res if len(res) >= 1 else None
    
    def check_duplicate(self, req: InteractibleRequest):
        curr_time = datetime.now()
        if req in self.out_queue.queue:
            return ('in_queue', None)
        elif req in self.device_manager.current_requests:
            return ('in_process', None)
        ts = [t for t in Transaction.get(Transaction.time>datetime(curr_time.year, curr_time.month, curr_time.day), Transaction.number==req.number, Transaction.product_spec==req.product_spec, Transaction.automator==req.automator) if t.success]
        if len(ts)>0:
            return ('in_cached_result', ts[-1])
        return ('no_duplicates', None)
    
    def run(self):
        while True:
            try:
                request = self.in_queue.get(True)
                if request.request.count('.') < 2: # invalid format
                    continue
                new_request = self.make_automator_request(request)
                if not new_request.number.isdigit(): # invalid format
                    continue
                new_req_copy = InteractibleRequest(**new_request.dict) # solely for message_content
                new_req_copy.product_spec = self.get_full_product_spec(new_req_copy)
                request.request = self.t('message_content').format(req=new_req_copy)
                del new_req_copy
                status_str = "Received request from [{}]: {}".format(request.user_identifier, str(new_request))
                logger.info(status_str)
                _print(status_str)
            except TypeError:
                continue
            
            usr_chk_res = self.check_user(request)
            if usr_chk_res is None:
                s = "User [{}] is not registered. Sending an appropriate reply.".format(request.user_identifier)
                logger.info(s)
                _print(s)
                request.reply(self.t('user_not_registered'))
                continue
            
            dup_res, transaction = self.check_duplicate(new_request)
            if dup_res == 'in_queue':
                request.reply(self.t('transaction_enqueued').format(message_content=request.request))
                status_str = "Resending reply for request for [{}] {}.".format(request.user_identifier, str(new_request))
            elif dup_res == 'in_process':
                request.reply(self.t('transaction_is_being_processed').format(message_content=request.request))
                status_str = "Resending status for request for [{}] {}.".format(request.user_identifier, str(new_request))
            elif dup_res == 'in_cached_result':
                assert(isinstance(transaction, Transaction))
                previous_reply = self.t('transaction_success' if transaction.refID != '?' else 'transaction_success_no_ref_id')
                previous_reply = previous_reply.format(message_content=self.get_message_content_from_transaction(transaction), res=transaction)
                status_str = "Resending reply for request for [{}] {}.".format(request.user_identifier, str(new_request))
                request.reply(self.t('transaction_had_been_processed').format(message_content=request.request, datetime=transaction.time, reply=previous_reply))
            else:
                status_str = "Enqueued request for [{}] {}".format(request.user_identifier, str(new_request))
                request.reply(self.t('transaction_enqueued').format(message_content=request.request))
                self.out_queue.put(new_request)
            logger.info(status_str)
            _print(status_str)


class ResultMiddleware:
    TRANSLATOR: Translator = Translator()
    CONFIG: Config
    
    def __init__(self, database_manager: SynapsisDB, in_queue: Queue[InteractibleResult]):
        self.database_manager = database_manager
        self.in_queue = in_queue
    
    @classmethod
    def configure(cls, config: Config):
        cls.CONFIG = config
        cls.TRANSLATOR = Translator(**config['translator_config'])
    
    @property
    def t(self):
        return self.__class__.TRANSLATOR

    def run(self):
        while True:
            try:
                result = self.in_queue.get(True)
            except Empty:
                continue
            
            self.database_manager.insert(Transaction(result.dict))
            
            reply_str = ''
            if result.success and result.refID != '?':
                reply_str = self.t('transaction_success')
            elif result.success:
                reply_str = self.t('transaction_success_no_ref_id')
            else:
                reply_str = self.t('transaction_failed')
            reply_str = reply_str.format(message_content=result.request.server_request.request, res=result, reason=result.error or result.description)
            
            if result.extra.get('balance') is not None:
                reply_str+= ". " + self.t('balance_suffix').format(balance=result.extra.get('balance'))
            
            if result.send_reply:
                result.request.reply(reply_str) #type:ignore
                status_str = "Sent result for [{}] {} ({}) ({})".format(result.request.server_request.user_identifier, str(result.request), "SUCCESS" if result.success else "FAILED", time_formatter(result.execution_duration))
            else:
                status_str = "Processed request for [{}] {} ({}) ({})".format(result.request.server_request.user_identifier, str(result.request), "SUCCESS" if result.success else "FAILED", time_formatter(result.execution_duration))
            logger.info(status_str)
            _print(status_str)
