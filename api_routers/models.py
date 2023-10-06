from typing import Dict, List, Union
from pydantic import BaseModel

from automators.data_structs import ExecFlag


class GenericResponse(BaseModel):
    status: bool
    detail: str
    detail_extra: Union[dict, None]


class ConfigWrapper(BaseModel):
    config: Union[dict, list, set, tuple, int, float, bool, None]


class RequestModel(BaseModel):
    number: str
    product_spec: str
    automator: str


class TransactionModel(BaseModel):
    id: int
    number: str
    product_spec: str
    refID: str
    time: float
    description: Union[str, None]
    error: Union[str, None]
    automator: str
    execution_duration: int


class UserModel(BaseModel):
    id: int
    server: str
    identifier: str


class UserInModel(BaseModel):
    server: str
    identifier: str


class DeviceModel(BaseModel):
    serial: str
    current_app: dict
    battery_level: int
    running: bool = True
    current_request: Union[RequestModel, None]
    u2_installed: bool
    u2_info: Union[dict, None]


class ProductMatcherModel(BaseModel):
    name: str
    description: Union[str, None]
    price: str
    exec_flag: ExecFlag


class ProductModel(BaseModel):
    matchers: List[ProductMatcherModel]
    confirmation: Union[List[ProductMatcherModel], None]
    location_near_bottom: bool = False


ProductList = Dict[str, ProductModel]
