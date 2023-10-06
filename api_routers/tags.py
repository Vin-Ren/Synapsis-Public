
from enum import Enum


class TAGS(Enum):
    DATABASE = 'Database'
    SERVER = 'Server'
    DEVICE = 'Device'
    MIDDLEWARE = 'Middleware'
    CONFIGURATION = 'Configuration'
    TRANSLATOR = 'Translator'
    PRODUCT = 'Product'
    UTILITIES = 'Utilities'
    DANGEROUS = 'Dangerous'

tags = TAGS
