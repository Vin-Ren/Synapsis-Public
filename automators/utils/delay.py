import random
import time

from automators.utils.logger import Logging

logger = Logging.get_logger(__name__)


def getDenominator(float):
    denominator = 10
    while True:
        if float*denominator == int(float*denominator):
            return denominator
        else:
            denominator *= 10

class Delay:
    ROUNDING_MAX_DECIMAL_PLACES = 6

    @classmethod
    def floatRounder(cls, _float):
        return round(_float, cls.ROUNDING_MAX_DECIMAL_PLACES)

    @classmethod
    def getRandomDelay(cls, rangeStart:float, rangeEnd:float):
        denominator = max([getDenominator(rangeStart), getDenominator(rangeEnd)])
        rangeStart, rangeEnd = int(rangeStart*denominator), int(rangeEnd*denominator)
        randomDelay = (random.randrange(rangeStart, rangeEnd))/denominator
        return randomDelay

    @classmethod
    def sleep(cls, delay:float):
        delay = cls.floatRounder(delay)
        time.sleep(delay)

    @classmethod
    def randomSleep(cls, delay: float, randomRange=0.5):
        noise = cls.getRandomDelay(-randomRange, randomRange)
        final_delay = cls.floatRounder(delay+noise)
        logger.debug("randomSleep: baseDelay={} randomRange={} delay={}".format(delay, randomRange, final_delay))
        return cls.sleep(final_delay)

    @classmethod
    def random(cls, rangeStart: float, rangeEnd: float):
        randomDelay = cls.getRandomDelay(rangeStart=rangeStart, rangeEnd=rangeEnd)
        randomDelay = cls.floatRounder(randomDelay)
        return cls.sleep(randomDelay)
