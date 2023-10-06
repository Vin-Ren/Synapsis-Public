
from typing import List

from lxml import etree


class BaseMatch:
    _MATCHER = lambda a, b: True

    @classmethod
    def matcher_any(cls, obj, spec):
        for spec_name, spec_matcher in spec.items():
            if spec_name == 'exec_flag':
                continue
            if callable(spec_matcher):
                if spec_matcher(obj[spec_name]):
                    return True
            elif obj[spec_name] == spec_matcher:
                return True

    @classmethod
    def matcher_all(cls, obj, spec):
        for spec_name, spec_matcher in spec.items():
            if spec_name == 'exec_flag':
                continue
            if callable(spec_matcher):
                if not spec_matcher(obj[spec_name]):
                    return False
            elif obj[spec_name] != spec_matcher:
                return False
        return True

    @classmethod
    def match(cls, objects:list, spec:dict):
        matching = []
        for obj in objects:
            if cls._MATCHER(obj, spec):
                matching.append(obj)
        return matching

    @classmethod
    def matchElementByAttrib(cls, elements:List[etree.ElementBase], attrib:dict):
        matching = []
        for el in elements:
            if cls._MATCHER(el.attrib, attrib):
                matching.append(el)
        return matching


class MatchAny(BaseMatch):
    _MATCHER = BaseMatch.matcher_any


class MatchAll(BaseMatch):
    _MATCHER = BaseMatch.matcher_all
