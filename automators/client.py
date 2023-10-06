
from functools import lru_cache

from ppadb.client import Client as ppadbClient
from automators.device import UnauthorizedError
from automators.device import Device


class Client(ppadbClient):
    def __init__(self, *args, device_cls=Device, **kwargs):
        super().__init__(*args, **kwargs)
        self.device_cls = device_cls

    @lru_cache(maxsize=10)
    def get_device(self, serial: str):
        return self.device_cls(self, serial)

    def devices(self, state=None):
        cmd = "host:devices"
        result = self._execute_cmd(cmd)
        assert(result is not None)
        
        devices = []
        
        for line in result.split('\n'):
            if not line:
                break
            tokens = line.split()
            if state and len(tokens) > 1 and tokens[1] != state:
                continue
            try:
                device = self.get_device(tokens[0])
                devices.append(device)
            except UnauthorizedError:
                print('Connection to {} is unauthorized.'.format(tokens[0]), end='\r')
        return devices
