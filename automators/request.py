

class Request:
    """Request object to interface with inside automators."""
    def __init__(self, number, product_spec, automator='', device=''):
        self.number = number
        self.product_spec = product_spec
        self.automator = automator
        self.device = device

    @property
    def dict(self):
        return {'number': self.number, 'product_spec': self.product_spec, 'automator': self.automator, 'device': self.device}

    def __eq__(self, other: object):
        if isinstance(other, self.__class__):
            return ((self.number == other.number) and (self.product_spec == other.product_spec) and (self.automator == other.automator))
        return False
    
    def __repr__(self):
        return "<Request number='{}' product_spec='{}' automator='{}'>".format(self.number, self.product_spec, self.automator)
    
    def __str__(self):
        return "Request for number='{}' with product_spec='{}' and automator='{}'".format(self.number, self.product_spec, self.automator)
