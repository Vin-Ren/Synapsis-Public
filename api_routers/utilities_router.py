import os

from fastapi import HTTPException, status
from fastapi.responses import FileResponse
from fastapi_class.decorators import get

from .base import BaseAPIRouter
from .tags import tags


class UtilitiesRouter(BaseAPIRouter):
    ROUTE_PREFIX = '/utilities'
    TAGS = [tags.UTILITIES]
    def __init__(self, api, app):
        super().__init__(api, app)
    
    @property
    def logging_config(self):
        return self.app.CONFIG.get('logging', {})
    
    @get("/log", summary="Gets log content", description="Gets log content. if backup_no is 0, gets current backup.", tags=[tags.DANGEROUS])
    def get_log_content(self, backup_no: int = 0):
        logging_conf = self.app.CONFIG['logging']
        filename = logging_conf.get('filename', 'logs.log')
        backup_no = max(min(backup_no, logging_conf.get('backupCount', 1)), 0)
        if backup_no > 0:
            filename = '.'.join([filename, str(backup_no)])
        if os.path.isfile(filename):
            return FileResponse(filename, media_type='text/x-log')
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Could not find specified log file.")
