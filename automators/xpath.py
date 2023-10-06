
from typing import Union
from automators.data_structs import InterfaceableDictLike


class BaseXPathCollection(object):
    SCROLLABLE = "//node[@scrollable='true']"
    TEXT_VIEW = "//node[@class='android.widget.TextView']"
    SCROLL_VIEW = "//node[@class='android.widget.ScrollView']"
    VIEW_GROUP = "//node[@class='android.view.ViewGroup']"

    FORMATTABLE_NODE_TEXT_SELECTOR = "//node[@text='{}']"


class _XPathMap(InterfaceableDictLike):
    def __repr__(self):
        return '<{} with {} XPath(s)>'.format(self.__class__.__name__, self.__len__())


class XPathMap(_XPathMap):
    BASE_XPATH: Union[_XPathMap, 'XPathMap'] = _XPathMap.from_python_cls(BaseXPathCollection) # Base XPathMap to inherit xpaths from
    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            return self.BASE_XPATH.get(key)
