from typing import Dict, List, Literal
import io

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi_class.decorators import get, post, put

from automators.device_manager import DeviceManager, RequestableDevice

from .base import BaseAPIRouter
from .models import GenericResponse, RequestModel, DeviceModel
from .utils import recursive_auto_resolve
from .tags import tags


class DeviceRouter(BaseAPIRouter):
    ROUTE_PREFIX = '/devices'
    TAGS = [tags.DEVICE]
    def __init__(self, api, app):
        super().__init__(api, app)
        self.device_manager: 'DeviceManager' = self.app.device_manager
    
    def get_device_or_raise_error(self, device_serial: str) -> RequestableDevice:
        device = self.device_manager.get_device(device_serial)
        if device is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such device is found.")
        return device
    
    @get("/list", summary="Lists all connected devices", description="Lists all connected devices")
    def get_devices(self):
        return [device.serial for device in self.device_manager.devices]
    
    @get("/list_processing", summary="Lists all connected devices currently processing a request with the request", description="Lists all connected devices currently processing a request. Returns a dict object {device:request}.", response_model=Dict[str, RequestModel])
    def get_processing(self):
        return {d.serial:d.current_request.dict for d in self.device_manager.devices if d.current_request is not None}
    
    @get("/current_requests", summary="Lists all requests currently being processed", description="Lists all requests currently being processed", response_model=List[RequestModel])
    def get_current_requests(self):
        return [req.dict for req in self.device_manager.current_requests]
    
    @put("/adb", summary="Executes a command to adb", description="Executes a command to adb", response_model=GenericResponse, tags=[tags.DANGEROUS])
    def execute_adb_command(self, command: str):
        result = self.device_manager.adb_command(*command.split(' '))
        if result.returncode == 0:
            return {'status': True, 'detail': "Successfully executed given adb command.", 'detail_extra': result.__dict__}
        return {'status': False, 'detail': "Failed to execute given adb command.", 'detail_extra': result.__dict__}
    
    @get("/{device}", summary="Gets information about given device", description="Gets information about given device", response_model=DeviceModel)
    def get_device_info(self, device: str, detailed: bool = False):
        device_obj = self.get_device_or_raise_error(device)
        return recursive_auto_resolve(device_obj.get_info(detailed=detailed))
    
    @get("/{device}/screencap", summary="Gets the screen capture of the device in png", description="Gets the screen capture of the device in png")
    def get_device_screencap(self, device: str):
        device_obj = self.get_device_or_raise_error(device)
        return StreamingResponse(io.BytesIO(device_obj.screencap()), media_type="image/png")
    
    @get("/{device}/hierarchy", summary="Gets the UI Hierarchy of the device", description="Gets the UI Hierarchy of the device")
    def get_device_ui_hierarchy(self, device:str, compressed: bool = False):
        device_obj = self.get_device_or_raise_error(device)
        return StreamingResponse(io.StringIO(device_obj.getUI(compressed=compressed, return_str=True)), media_type="text/xml")
    
    @post("/{device}/shell", summary="Executes shell in device, like adb shell", description="Executes shell in device, like adb shell", tags=[tags.DANGEROUS])
    def device_shell(self, device: str, command: str):
        device_obj = self.get_device_or_raise_error(device)
        return {'output': device_obj.shell(command)}
    
    @put("/{device}/toggle_stop", summary="Toggles the device stop flag", description="Toggles the device stop flag", response_model=DeviceModel)
    def stop_device(self, device: str):
        device_obj = self.get_device_or_raise_error(device)
        data = {'running': device_obj.stop}
        if not device_obj.stop:
            data.update(device_obj.get_info())
        device_obj.stop^=True
        if not device_obj.stop:
            data.update(device_obj.get_info())
        return recursive_auto_resolve(data)
    
    @put("/{device}/uiautomator2", summary="Modify the uiautomator2 of given device with an action", description="Modify the uiautomator2 of given device with an action", response_model=GenericResponse, tags=[tags.DANGEROUS])
    def modify_device_u2(self, device: str, action: Literal['install', 'uninstall', 'start', 'stop']):
        device_obj = self.get_device_or_raise_error(device)
        detail = {}
        if action == 'install':
            device_obj.u2_install()
            detail['u2_installed'] = device_obj.refresh_u2_installed()
        elif action == 'uninstall':
            device_obj.u2_uninstall()
            detail['u2_installed'] = device_obj.refresh_u2_installed()
        elif action == 'start':
            device_obj.u2_start()
        elif action == 'stop':
            device_obj.u2_stop()
        else:
            return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action does not exist.")
        return {'status': True, 'detail': "'{}' Action completed successfully.".format(action), 'detail_extra': detail}
