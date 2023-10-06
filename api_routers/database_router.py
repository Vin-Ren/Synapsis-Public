from typing import List

from fastapi_class.decorators import get, post, delete

from api_template.base.database.models.base import Model
from database import SynapsisDB, Transaction, User

from .base import BaseAPIRouter
from .models import GenericResponse, UserInModel, UserModel, TransactionModel
from .tags import tags


class DatabaseRouter(BaseAPIRouter):
    ROUTE_PREFIX = '/database'
    TAGS = [tags.DATABASE]
    def __init__(self, api, app):
        super().__init__(api, app)
        self.db_manager: 'SynapsisDB' = self.app.database_manager
    
    def to_dict(self, obj: Model):
        if isinstance(obj, Transaction):
            dct = obj.to_dict()
            dct['time'] = obj.time.timestamp() #type:ignore # it is there, just not detectable
            return dct
        elif isinstance(obj, User):
            return obj.to_dict()
    
    @post('/query', summary="Executes query", description="Executes query. Returns data from fetchall (Really Unsafe).", tags=[tags.DANGEROUS])
    def execute_query(self, query: str):
        self.db_manager.execute(query)
        return {'data': list(self.db_manager.cursor.fetchall())}
    
    @post('/query/select', summary="Executes a select query and returns all result", description="Executes a select query and returns all result.", response_model=List[dict], tags=[tags.DANGEROUS])
    def query_select(self, query: str):
        return list(self.db_manager.select(query))
    
    @post('/query/delete', summary="Executes a delete query", description="Executes a delete query.", response_model=GenericResponse, tags=[tags.DANGEROUS])
    def query_delete(self, query: str):
        try:
            self.db_manager.execute(query)
            return {'status': True, 'detail': "Delete query executed."}
        except Exception:
            return {'status': False, 'detail': "Failed to execute query."}
    
    @post('/commit', summary="Commits changes to the database", description="Commits changes to the database, like conn.commit()", response_model=GenericResponse, tags=[tags.DANGEROUS])
    def database_commit(self):
        try:
            self.db_manager.commit()
            return {'status': True, 'detail': 'Committed changes to db.'}
        except:
            return {'status': False, 'detail': 'Failed to commit changes to db.'}
    
    @get('/transactions', summary="Gets all transaction", description="Gets all transaction", response_model=List[TransactionModel])
    def get_transactions_all(self):
        return [self.to_dict(t) for t in Transaction.get_all()]
    
    @get('/transactions/recent', summary="Gets recent transaction", description="Gets recent transaction", response_model=List[TransactionModel])
    def get_transactions_recent(self, limit: int = 100, offset: int = 0):
        limit = min(limit, 1000)
        return [self.to_dict(t) for t in Transaction.get(orderby=Transaction.id.DESC, limit=(limit, offset))]
    
    @delete('/transactions/{id}', summary="Deletes transaction entry", description="Deletes transaction entry with given id", response_model=GenericResponse, tags=[tags.DANGEROUS])
    def delete_transaction(self, id: int):
        try:
            transactions = list(Transaction.get(Transaction.id==id, limit=1))
            if len(transactions) <= 0:
                return {'status': False, 'detail': "No transaction found with id={}.".format(id)}
            Transaction.delete(Transaction.id==id)
            return {'status': True, 'detail': "Removed transaction.", 'detail_extra': {'transaction': transactions[0]}}
        except Exception:
            return {'status': False, 'detail': "Cannot remove transaction."}
    
    @get('/users', summary="Gets all users", description="Gets all users", response_model=List[UserModel])
    def get_users_all(self, limit: int = 10, offset: int = 0):
        limit = min(limit, 100)
        return [self.to_dict(u) for u in User.get(limit=(limit, offset))]
    
    @get('/users/get', summary="Gets all users with given criteria", description="Gets all users with given criteria", response_model=List[UserModel])
    def get_users(self, server: str, limit: int = 10, offset: int = 0):
        limit = min(limit, 100)
        return [self.to_dict(u) for u in User.get(User.server==server, limit=(limit, offset))]
    
    @post('/users/create', summary="Creates a user entry", description="Creates a user entry", response_model=GenericResponse)
    def create_user(self, user: UserInModel):
        try:
            if len(list(User.get(User.server==user.server, User.identifier==user.identifier))) > 0:
                return {'status': False, 'detail': "User already exists."}
            self.db_manager.insert(User(user.dict()))
            users = list(User.get(User.server==user.server, User.identifier==user.identifier))
            data = {'status': True, 'detail':'Created a user entry'}
            if len(users) > 0:
                data.update({'detail_extra': {'user': users[0].to_dict()}})
            return data
        except Exception:
            return {'status': False, 'detail': "User creation failed."}
    
    @delete('/users/{id}', summary="Deletes user entry", description="Deletes user entry with given id", response_model=GenericResponse, tags=[tags.DANGEROUS])
    def delete_user(self, id: int):
        try:
            users = list(User.get(User.id==id, limit=1))
            if len(users) <= 0:
                return {'status': False, 'detail': "No user found with id={}.".format(id)}
            User.delete(User.id==id)
            return {'status': True, 'detail': "Removed user.", 'detail_extra': {'user': users[0]}}
        except Exception:
            return {'status': False, 'detail': "Cannot remove user."}
