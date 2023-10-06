from api_template.base.database import *


class Transaction(Model):
    __TABLE_NAME__ = "transactions"
    id = Field(int, primary_key=True, auto_increment=True, unique=True, not_null=True)
    number = Field(str, not_null=True)
    product_spec = Field(str, not_null=True)
    refID = Field(str, not_null=True)
    time = Field(datetime, not_null=True)
    description = Field(str)
    error = Field(str)
    automator = Field(str, not_null=True, default='')
    execution_duration = Field(int, not_null=True, default=-1)
    
    _repr_format = "<%(classname)s id=%(id)d number='%(number)s' product_spec='%(product_spec)s' refID='%(refID)s' success=%(success)s>"
    
    @property
    def success(self):
        return (self.time is not None and self.refID is not None and self.error is None)


class User(Model):
    __TABLE_NAME__ = "users"
    id = Field(int, primary_key=True, auto_increment=True, unique=True, not_null=True)
    server = Field(str, not_null=True)
    identifier = Field(str, not_null=True)
    
    _repr_format = "<%(classname)s id=%(id)d id=%(id)s server='%(server)s' identifier='%(identifier)s'>"


class SynapsisDB(MultiThreadedSQLiteDB):
    TABLES = [Transaction, User]
