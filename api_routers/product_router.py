
from typing import Dict, TYPE_CHECKING

from fastapi import File, HTTPException, status
from fastapi_class.decorators import get, post, put

from .base import BaseAPIRouter
from .models import ProductList, GenericResponse
from .tags import tags


if TYPE_CHECKING:
    from automators.plugins.base import BasePlugin


class ProductRouter(BaseAPIRouter):
    ROUTE_PREFIX = '/products'
    TAGS = [tags.PRODUCT]
    def __init__(self, api, app):
        super().__init__(api, app)
        self.device_manager = self.app.device_manager
        self.automators: Dict[str, BasePlugin] = self.app.device_manager.DEVICE_CLS.PLUGINS
        self.products = {name: automator.PRODUCTS for name, automator in self.automators.items()}
    
    def get_automator_or_raise_error(self, automator_name: str):
        automator = self.automators.get(automator_name)
        if automator is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automator '{}' is not found.".format(automator))
        return automator
    
    def get_products_or_raise_error(self, automator_name: str):
        return self.get_automator_or_raise_error(automator_name).PRODUCTS
    
    @get("/automators", summary="Lists automators", description="Lists automators")
    def list_automators(self):
        return {'automators': list(self.automators.keys())}
    
    @get("/{automator}/list", summary="Lists all product in given automator", description="Lists all product in given automator", response_model=ProductList)
    def list_products(self, automator: str):
        product_list = self.get_products_or_raise_error(automator)
        return product_list.encode_data()
    
    @post("/{automator}/reload", summary="Reload product list from file (using configure)", description="Reload product list from file (using configure)", response_model=GenericResponse)
    def reload_products(self, automator: str):
        automator_obj = self.get_automator_or_raise_error(automator)
        automator_obj.configure(automator_obj.CONFIG)
        return {'status': True, 'detail': "Product list reloaded from file."}
    
    @put("/{automator}/update", summary="Updates the product list entry in memory", description="Updates the product list entry in memory, is not saved to file.", response_model=GenericResponse, tags=[tags.DANGEROUS])
    def update_products(self, automator: str, product_list: ProductList):
        try:
            data = {name: {**prod.dict()} for name, prod in product_list.items()}
            new_product_list = self.products[automator].__class__.decode_data(data)
        except NameError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more exec_flag is not correct.")
        
        product_list = self.get_products_or_raise_error(automator)
        product_list.update(new_product_list)
        return {'status': True, 'detail': "Updated product list of '{}' automator.".format(automator)}
    
    @put("/{automator}/save", summary="Saves the product list entry in memory to file", description="Saves the product list entry in memory to file", response_model=GenericResponse, tags=[tags.DANGEROUS])
    def save_products(self, automator: str):
        automator_obj = self.get_automator_or_raise_error(automator)
        product_list = self.get_products_or_raise_error(automator)
        product_list_file = automator_obj.CONFIG.get('product_list', 'product_list.json')
        product_list.to_file(product_list_file)
        return {'status': True, 'detail': "Saved product list of automator '{}' to file.".format(automator)}
    
    @post("/{automator}/file", summary="Upload a new product list file", description="Upload a new product list file.", response_model=GenericResponse, tags=[tags.DANGEROUS])
    def upload_product_list_file(self, automator: str, file: bytes = File(b'')):
        automator_obj = self.get_automator_or_raise_error(automator)
        product_list_file = automator_obj.CONFIG.get('product_list', 'product_list.json')
        try:
            with open(product_list_file, 'wb') as fl:
                fl.write(file)
            return {'status': True, 'detail': "Product list file saved."}
        except Exception as exc:
            return {'status': False, 'detail': 'Exception<{}{}> caught when trying to write to file.'.format(exc.__class__, exc.args)}
