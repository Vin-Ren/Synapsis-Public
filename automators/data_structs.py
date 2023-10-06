from dataclasses import dataclass, field
from enum import IntFlag
import json
from typing import List
import yaml

from automators.utils.ext.product import Macros as MatcherMacros


class ObjectifiedDict(dict):
    def __setattr__(self, name, value):
        return super().__setitem__(name, value)
    
    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return super().__getattribute__('__getitem__')(name)
    
    def __repr__(self):
        return '<{} object with {} field(s)>'.format(self.__class__.__name__, self.__len__())
    
    def update(self, other):
        for k,v in other.items():
            self.__setitem__(k,v)


class InterfaceableDictLike(ObjectifiedDict):
    """A subclass of ObjectifiedDict, which enables the use of encode_data and decode_data for interfacing with any kind of databases."""
    def encode_data(self):
        """Makes your data into a pickle-able dict. Override according to your uses."""
        return dict(self)
    
    @classmethod
    def decode_data(cls, data: dict):
        """Parses the encoded data. Override according to your uses."""
        return cls(data)
    
    # JSON
    def to_json(self, filename: str, **kw):
        """Writes a json string representation of the object into a file."""
        with open(str(filename), 'w') as f: json.dump(self.encode_data(), f, indent=4, **kw)
    def to_json_str(self, **kw):
        """Returns a json string representation of the object."""
        return json.dumps(self.encode_data(), **kw)
    @classmethod
    def from_json_str(cls, s: str, **kw):
        """Parses a json string and create its corresponding object."""
        return cls.decode_data(json.loads(s, **kw) or {})
    @classmethod
    def from_json(cls, filename: str, **kw):
        """Parses a json file and create its corresponding object."""
        with open(str(filename), 'r') as f: return cls.decode_data(json.load(f, **kw) or {})
    
    # YAML
    def to_yaml(self, filename: str, **kw):
        """Writes a yaml string representation of the object into a file."""
        kw['sort_keys']=kw.get('sort_keys', False) # defaults to True, we want to preserve the order
        with open(str(filename), 'w') as f: yaml.dump(self.encode_data(), f, **kw)
    def to_yaml_str(self, **kw):
        """Returns a yaml string representation of the object."""
        return yaml.dump(self.encode_data(), **kw)
    @classmethod
    def from_yaml_str(cls, s: str, **kw):
        """Parses a yaml string and create its corresponding object."""
        return cls.decode_data(yaml.load(s, yaml.Loader, **kw) or {})
    @classmethod
    def from_yaml(cls, filename: str, **kw):
        """Parses a yaml file and create its corresponding object."""
        with open(str(filename), 'r') as f: return cls.decode_data(yaml.load(f, yaml.Loader, **kw) or {})
    
    @classmethod
    def from_python_cls(cls, src_cls: type):
        """Parses a class with a dict-like approach and create its corresponding object."""
        return cls({k:v for k,v in src_cls.__dict__.items() if not k.startswith('__')})
    
    @classmethod
    def from_file(cls, filename: str):
        """Checks format from filename, then load file."""
        if filename[-5:] == '.json':
            return cls.from_json(filename)
        elif (filename[-5:] == '.yaml' or filename[-4:] == '.yml'):
            return cls.from_yaml(filename)
        else:
            raise NotImplementedError("File extension is not supported.")
    
    def to_file(self, filename: str):
        """Checks format from filename, then save to file."""
        if filename[-5:] == '.json':
            return self.to_json(filename)
        elif (filename[-5:] == '.yaml' or filename[-4:] == '.yml'):
            return self.to_yaml(filename)
        else:
            raise NotImplementedError("File extension is not supported.")


class Config(InterfaceableDictLike):
    @classmethod
    def recursive_decode(cls, data):
        if isinstance(data, dict):
            return cls({k:cls.recursive_decode(v) for k,v in data.items()})
        elif isinstance(data, (list, tuple, set)):
            return data.__class__([cls.recursive_decode(e) for e in data])
        return data # Should only be primitive types right here.
    
    def recursive_encode(self):
        def auto_encode(obj):
            if hasattr(obj, 'encode_data'):
                return obj.encode_data()
            elif isinstance(obj, dict):
                return {k: auto_encode(v) for k,v in obj.items()}
            elif isinstance(obj, (list, tuple, set)):
                return [auto_encode(child) for child in obj]
            return obj # primitive types
        return {k: auto_encode(v) for k,v in self.items()}
    
    @classmethod
    def decode_data(cls, data: dict):
        return cls.recursive_decode(data)
    
    def encode_data(self):
        return self.recursive_encode()


class ConfigBuilder(dict):
    """
    Builds the structure of the required config object. Pass an instance of this class like passing a normal config object. 
    Please do not use this in a production environment, it will mess things up.
    This works by returning and saving a new child instance of 'ConfigBuilder' for every access to the instance, recursively doing this results in a tree-like structure being created.
    To be used, all usages of config must have a default value.
    Also if this is used, make sure there are no errors, which is usually impossible if any kind of filename or kwargs are stored in the config.
    """
    def __init__(self, default_dct={}, empty_flname='__empty.yaml'):
        self.data: dict[str, 'ConfigBuilder'] = {}
        self.empty_flname=empty_flname
        self.update(default_dct)
    
    def __str__(self):
        return self.empty_flname
    
    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.__str__()[key]
        self.data[key] = self.data.get(key, self.__class__(dict(self), self.empty_flname)) # for multiple gets to the same key
        return self.data[key]
        
    def get(self, key, default=None):
        return self.__getitem__(key)
    
    def build_config_dict(self, dict_cls=dict):
        if self.data.__len__() > 0:
            return dict_cls({key:value.build_config_dict(dict_cls) for key, value in self.data.items()})
        return None


class ExecFlag(IntFlag):
    """A Flagging system that determines whether an 'exec' function is needed to resolve a matcher's comparator(s)."""
    NAME=0b1
    DESCRIPTION=0b10
    PRICE=0b100
    @classmethod
    def get_flag(cls, matcher:dict):
        flag = 0
        for bit in cls: # checks for name, description, and price value, if it is callable then set the flag to true.
            flag |= bit * bool(callable(matcher.get((bit.name or '').lower())))
        return cls(flag)


@dataclass(init=True, slots=True)
class Product:
    matchers: List[dict]
    confirmation: List[dict] = field(default_factory=list)
    location_near_bottom: bool = False
    
    @classmethod
    def from_dict(cls, d:dict, namespace:dict):
        d=d.copy()
        transform=lambda s:[exec('_'*25+'='+s, namespace), namespace['_'*25]][1]
        for matcher in d['matchers'] + d.get('confirmation', []):
            flag = ExecFlag(matcher.get('exec_flag',0))
            if ExecFlag.NAME in flag:
                matcher['name']=transform(matcher['name'])
            if ExecFlag.DESCRIPTION in flag:
                matcher['description']=transform(matcher['description'])
            if ExecFlag.PRICE in flag:
                matcher['price']=transform(matcher['price'])
        try:
            namespace.pop('_'*25)
        except KeyError:
            pass
        return cls(**d)


def matchers_to_string(matchers:List[dict]):
    return [{**{k:v if not callable(v) else repr(v) for k,v in matcher.items()}, 'exec_flag':ExecFlag.get_flag(matcher).value} for matcher in matchers]

#TEMPORARY FUNCTION TO MIGRATE
def convertProductSpec(ProductSpec):
    raw = ObjectifiedDict(ProductSpec.__dict__)
    data={}
    for name, matchers in raw['Products'].items():
        data[name] = {'matchers':matchers_to_string(matchers)}
        if name in raw.get('ProductsConfirmation', {}):
            data[name].update({'confirmation': matchers_to_string(raw['ProductsConfirmation'][name])})
    
    for name in raw.get('ProductCodeCloserToBottom', []):
        data[name].update({'location_near_bottom':True})
    # obj = ProductList(data)
    return data

class ProductList(InterfaceableDictLike):
    """Container for Products."""
    def __repr__(self):
        return '<{} with {} Product(s)>'.format(self.__class__.__name__, self.__len__())
    
    def encode_data(self):
        data={}
        for name, prod in self.items():
            data[name]={'matchers':matchers_to_string(prod.matchers), 'confirmation': matchers_to_string(prod.confirmation), 'location_near_bottom':prod.location_near_bottom}
        return data
    
    @classmethod
    def decode_data(cls, data:dict):
        return cls({name: Product.from_dict(prod, namespace=InterfaceableDictLike.from_python_cls(MatcherMacros)) for name, prod in data.items()})
    
    # Python Objects
    @classmethod
    def from_product_spec(cls, product_spec_cls):
        return cls.from_json_str(json.dumps(convertProductSpec(product_spec_cls)))
