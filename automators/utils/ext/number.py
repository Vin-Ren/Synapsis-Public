

from automators.utils.logger import Logging

logger = Logging.get_logger(__name__)


class Number:
    DEFAULT_PREFIX = '8'

    @classmethod
    def parser(cls, number: str):
        length = len(number)
        logger.debug('Number.parser:number={} length={}'.format(number, length))

        if number.startswith('08') and 13 > length > 10:
            return number[1:]
        elif number.startswith('+62') and 15 > length > 12:
            return number[3:]
        elif number.startswith('62') and 15 > length > 12:
            return number[2:]
        return number

    @classmethod
    def converter(cls, number: str, prefix=None, sep=None):
        prefix = prefix or cls.DEFAULT_PREFIX
        standard = cls.parser(number) # standard prefix = 8
        if sep:
            standard = list(standard)
            standard.insert(3, sep)
            standard.insert(8, sep)
            standard = ''.join(standard)
        significant_numerics = standard[1:]
        logger.debug('Number.converter:number={} prefix={}'.format(number, prefix))
        return prefix + significant_numerics

    @classmethod
    def toStd(cls, number):
        cls.converter(number)