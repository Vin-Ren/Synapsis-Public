
class DeviceError(Exception):
    pass

class UnauthorizedError(DeviceError):
    pass

class DeviceRuntimeError(DeviceError, RuntimeError):
    pass

class MaxTriesReachedError(DeviceRuntimeError):
    pass

class MaxCyclesReached(DeviceRuntimeError, TimeoutError):
    pass

class ReceiptNotFoundError(DeviceRuntimeError):
    pass

class DeviceScreenOffError(DeviceRuntimeError):
    pass

class ApplicationNotResponding(DeviceRuntimeError):
    pass
