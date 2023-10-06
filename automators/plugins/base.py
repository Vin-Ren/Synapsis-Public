
from automators.device import Device
from automators.data_structs import Config, ProductList
from automators.xpath import XPathMap
from automators.request import Request
from automators.result import Result
from automators.utils.translator import Translator


class AutomatorPlugin:
    CONFIG: Config
    PACKAGE: str # Required package to run.
    XPATH: XPathMap
    PRODUCTS: ProductList
    TRANSLATOR: Translator
    APP_PIN: str
    
    def __init__(self, device: Device):
        self.device=device
        self.state=None
        self.watchers=[] # should only have the watchers of currect active automator
    
    @classmethod
    def configure(cls, config: Config):
        """Configure the class variables. Must call super().configure(config)"""
        cls.CONFIG = config
    
    @property
    def xpath(self):
        return self.__class__.XPATH
    
    @property
    def products(self):
        return self.__class__.PRODUCTS

    @property
    def translator(self):
        return self.__class__.TRANSLATOR
    
    @property
    def t(self):
        return self.__class__.TRANSLATOR
    
    @property
    def app_pin(self):
        return self.__class__.APP_PIN
    
    def processRequest(self, request: Request):
        return Result(request.number, request.product_spec)


BasePlugin = AutomatorPlugin
