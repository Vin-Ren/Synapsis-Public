from typing import Union, Dict
from lxml import etree

from automators.ui.bounds import Bounds
from automators.utils.ext.match import MatchAll
from automators.utils.logger import Logging

logger = Logging.get_logger(__name__)


class Element:
    @classmethod
    def get_bounds(cls, element: Union[etree.ElementBase, Dict[str,str]]):
        bounds = element.get('bounds', ((-1,-1),(-1,-1)))
        return Bounds.get(bounds)

    @classmethod
    def get_center_from_element(cls, element:etree.ElementBase):
        (x1, y1), (x2, y2) = cls.get_bounds(element)

        middleX = int(round((x1+x2)/2))
        middleY = int(round((y1+y2)/2))
        return (middleX, middleY)

    @classmethod
    def getElementsByXPath(cls, root, xpath):
        elements = root.xpath(xpath)
        return elements

    @classmethod
    def getElementByXPath(cls, root, xpath, elementIndex=0):
        elements = cls.getElementsByXPath(root, xpath)
        if len(elements) > elementIndex:
            return elements[elementIndex]

    @classmethod
    def getElementsByAttribute(cls, root: etree.ElementBase, attributes:dict):
        elements = [el.attrib for el in root.iterdescendants()]
        matching = MatchAll.match(elements, attributes)
        return matching

    @classmethod
    def getElementByAttribute(cls, root: etree.ElementBase, attributes:dict, elementIndex=0):
        matching = cls.getElementsByAttribute(root, attributes)
        if len(matching) > elementIndex:
            return matching[elementIndex]
