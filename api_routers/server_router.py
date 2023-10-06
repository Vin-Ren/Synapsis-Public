from typing import Dict, Union

from fastapi import HTTPException, status
from fastapi_class.decorators import get, post

from database import SynapsisDB, User
from server.server_manager import ServerManager

from .base import BaseAPIRouter
from .models import UserModel, GenericResponse
from .tags import tags


class ServerRouter(BaseAPIRouter):
    ROUTE_PREFIX = '/servers'
    TAGS = [tags.SERVER]
    def __init__(self, api, app):
        super().__init__(api, app)
        self.server_manager: 'ServerManager' = self.app.server_manager
        self.database_manager: 'SynapsisDB' = self.app.database_manager
    
    def raise_if_not_found(self, server: str):
        if server not in self.server_manager.servers:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such server is found.")
    
    @get('/list', summary="Lists the servers", description="Lists the servers")
    def get_server_list(self):
        return list(self.server_manager.servers.keys())
    
    @get('/list_shards_ids', summary="Lists all the servers shards id", description="Lists all the servers shards id")
    def get_all_server_shards_ids(self):
        return self.server_manager.server_shards
    
    @get('/{server}/list', summary="Lists all the shards ids for the server", description="Lists all the shards ids for the server")
    def get_server_shards_ids(self, server: str):
        self.raise_if_not_found(server)
        return self.server_manager.servers[server].shards_identifiers
    
    @post('/{server}/restart', summary="Restarts given server", description="Restarts given server", response_model=GenericResponse)
    def restart_server(self, server: str):
        self.raise_if_not_found(server)
        self.server_manager.restart_server(server)
        return {'status': True, 'detail': 'trying to restart server={}'.format(server)}
    
    @post('/{server}/add_contact', summary="Adds user to contact list of shard", description="id is used as a shorthand for identifier", response_model=GenericResponse)
    def add_contact(self, server: str, shard_id: str, user_id: str):
        self.raise_if_not_found(server)
        if self.server_manager.add_contact(server, shard_id, user_id):
            return {'status': True, 'detail': "'{}' is added as a contact of '{}'.".format(user_id, shard_id)}
        return {'status': False, 'detail': "'{}' is not added as a contact of '{}'.".format(user_id, shard_id)}
    
    @post('/{server}/remove_contact', summary="Removes user from contact list of shard", description="id is used as a shorthand for identifier", response_model=GenericResponse)
    def remove_contact(self, server: str, shard_id: str, user_id: str):
        self.raise_if_not_found(server)
        if self.server_manager.remove_contact(server, shard_id, user_id):
            return {'status': True, 'detail': "'{}' is removed from '{}'s contact list.".format(user_id, shard_id)}
        return {'status': False, 'detail': "'{}' is not removed from '{}'s contact list.".format(user_id, shard_id)}
    
    @post('/{server}/register_user', summary="Adds user to contact list of shard and registers them to the database", description="id is used as a shorthand for identifier", response_model=GenericResponse)
    def register_user(self, server: str, shard_id: str, user_id: str):
        self.raise_if_not_found(server)
        if self.server_manager.add_contact(server, shard_id, user_id):
            self.database_manager.insert(User(server=server, identifier=user_id))
            users = list(User.get(User.server==server, User.identifier==user_id))
            data = {'status': True, 'detail': "Registered user '{}' and added as a contact of '{}'".format(user_id, shard_id)}
            if len(users)>0:
                data.update({'detail_extra': {'user': users[0].to_dict()}})
            return data
        return {'status': False, 'detail': "Failed to register user '{}'.".format(user_id)}
    
    @post('/{server}/unregister_user', summary="Removes user from all contact list of server and unregisters them from the database", description="id is used as a shorthand for identifier", response_model=GenericResponse)
    def unregister_user(self, server: str, user_id: str):
        self.raise_if_not_found(server)
        server_obj = self.server_manager.servers[server]
        if all([server_obj.remove_contact(shard_id, user_id) for shard_id in server_obj.shards_identifiers]):
            User.delete(User.server==server, User.identifier==user_id)
            return {'status': True, 'detail': "Unregistered user '{}' and removed from all shard's contact list.".format(user_id)}
        return {'status': False, 'detail': "Failed to unregistered user '{}' and removed from all shard's contact list.".format(user_id)}
