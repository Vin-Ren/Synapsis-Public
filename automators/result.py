
from automators.request import Request
from automators.utils.ext.number import Number


class Result:
    __slots__ = ['number', 'product_spec', 'refID', 'time', 'description', 'error', 'automator', 'execution_duration', 'request', 'send_reply', 'extra']
    def __init__(self, number, product_spec, refID=None, time=None, description=None, error=None, automator=None, execution_duration=-1, request=None, send_reply=True, **kwargs):
        self.number = number
        self.product_spec = product_spec
        self.refID = refID
        self.time = time
        self.error = error
        self.description = description
        self.automator = automator
        self.execution_duration = execution_duration
        self.request = request
        self.send_reply = send_reply
        self.extra = kwargs

    @classmethod
    def from_request(cls, request: Request):
        return cls(request.number, request.product_spec, automator=request.automator, request=request)

    def update(self, dct={}, **kwargs):
        for k,v in {**dct,**kwargs}.items():
            if k in self.__class__.__slots__:
                setattr(self, k, v)
            else:
                self.extra.update({k:v})

    @property
    def isError(self):
        return self.error is not None

    @property
    def success(self):
        if self.time is not None and self.refID is not None and self.error is None:
            return True
        return False

    @property
    def status(self):
        return "Success" if self.success else "Failed"

    @property
    def dict(self):
        return {'number': self.number, 'product_spec': self.product_spec, 'automator': self.automator, 'refID':self.refID, 'time': self.time, 'description': self.description, 'error': self.error, 'execution_duration': self.execution_duration}

    def __str__(self):
        return "Transaction Result for number {} with product spec {}, Finished with status {}".format(Number.parser(self.number), self.product_spec, self.status)

    def detailed(self):
        return "{_str}. refID: {refID}. transactionTime: {time} ExecutedWith={exctr} Description: {desc}. Error: {err}.".format(_str=self.__str__(),
                                                                                                                                refID=self.refID,
                                                                                                                                time=self.time,
                                                                                                                                exctr=self.automator,
                                                                                                                                desc=self.description,
                                                                                                                                err=self.error)
