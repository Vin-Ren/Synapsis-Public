from types import NoneType


def recursive_auto_resolve(data):
    """A helper function to automatically resolve 'normal' styled data with custom classes to primitive classes."""
    if hasattr(data, 'encode_data'):
        return getattr(data, 'encode_data')()
    elif hasattr(data, 'dict'):
        return getattr(data, 'dict')
    elif hasattr(data, 'to_dict'):
        return getattr(data, 'to_dict')()
    
    if isinstance(data, dict):
        return {recursive_auto_resolve(k): recursive_auto_resolve(v) for k,v in data.items()}
    elif isinstance(data, (list, set, tuple)):
        return data.__class__([recursive_auto_resolve(e) for e in data])
    elif isinstance(data, (int, float, bool, str, bytes, bytearray, NoneType)):
        return data
    return {k: recursive_auto_resolve(v) for k,v in data.__dict__.items()}
