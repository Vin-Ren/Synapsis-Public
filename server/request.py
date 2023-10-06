from server.base import BaseServer


class Request:
    """Request object to interface with by server, request preprocessor, and app."""
    def __init__(self, server: BaseServer, request, user_identifier, interaction_data, **kw):
        """
        server must be an instance of BaseServer or its subclasses
        request is the bare data for the request, e.g: a request string only not a message object.
        interaction_data is the data for controlling how to reply and stuff
        """
        self.server=server
        self.request=request
        self.user_identifier=user_identifier
        self.interaction_data=interaction_data

    def reply(self, message):
        self.server.reply(message, self.interaction_data)

    def __repr__(self):
        return "<{} object request='{}'>".format(self.__class__.__name__, self.request)

    def __str__(self):
        return "Request '{}'".format(self.request)
