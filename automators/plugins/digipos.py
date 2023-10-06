from datetime import datetime
import secrets
from typing import List, Optional, Union

from lxml import etree
from ppadb import keycode

from automators.data_structs import Config, Product, ProductList
from automators.xpath import XPathMap
from automators.plugins.base import AutomatorPlugin
from automators.request import Request
from automators.result import Result
from automators.ui.bounds import Bounds
from automators.ui.element import Element
from automators.utils.delay import Delay
from automators.utils.ext.match import MatchAll
from automators.utils.ext.number import Number
from automators.utils.exception import MaxTriesReachedError
from automators.utils.helper import retry
from automators.utils.logger import Logging
from automators.utils.translator import Translator


logger = Logging.get_logger(__name__)


class DigiposXPathCollection:
    USERNAME_TEXTVIEW = "//node[@resource-id='com.telkomsel.digiposaja:id/name']"
    SPLASH_SCREEN_APP_VERSION = "//node[@resource-id='com.telkomsel.digiposaja:id/textViewVersion']"
    DASHBOARD_BOTTOM_NAVIGATION = "//node[@resource-id='com.telkomsel.digiposaja:id/navigation']"
    DASHBOARD_BOTTOM_NAVIGATION_HOME_MENU = DASHBOARD_BOTTOM_NAVIGATION+"//node[@resource-id='com.telkomsel.digiposaja:id/navigation_home']"
    DASHBOARD_BOTTOM_NAVIGATION_HOME_MENU_ICON = DASHBOARD_BOTTOM_NAVIGATION_HOME_MENU+"//node[@resource-id='com.telkomsel.digiposaja:id/icon']"
    
    NUMBER_INPUT_BOX = "//node[@resource-id='com.telkomsel.digiposaja:id/no_telepon_pelanggan' and @class='android.widget.EditText']"
    NUMBER_INPUT_VIEW_TEXT = "//node[@resource-id='com.telkomsel.digiposaja:id/no_tlp_pelanggan']"
    CONFIRM_NUMBER_BUTTON = "//node[@resource-id='com.telkomsel.digiposaja:id/button_submit']"
    
    CONFIRM_NUMBER_PACKAGE_SELECTION = "//node[@resource-id='com.telkomsel.digiposaja:id/noHpValue']"

    LOADING_OVERLAY = "//node[@resource-id='com.telkomsel.digiposaja:id/md_content']"
    PROGRESS_BAR = "//node[@class='android.widget.ProgressBar']"
    
    PRODUCTS_SCROLLABLE = "//node[@resource-id='com.telkomsel.digiposaja:id/recyclerViewListCategory']"
    PRODUCT = PRODUCTS_SCROLLABLE+"//node[@class='android.view.ViewGroup' and @clickable='true']"
    # Ref: https://stackoverflow.com/a/4785929
    # put a dot in front to make it relative, so it won't evaluate the whole document. 
    # a slash '/' would evaluate on the whole document.
    PRODUCT_NAME = ".//node[@resource-id='com.telkomsel.digiposaja:id/nama_produk']"
    PRODUCT_DESCRIPTION = ".//node[@resource-id='com.telkomsel.digiposaja:id/deskripsi_produk']"
    PRODUCT_PRICE = ".//node[@resource-id='com.telkomsel.digiposaja:id/price_real']"
    
    CONFIRM_PURCHASE_NUMBER = "//node[@resource-id='com.telkomsel.digiposaja:id/no_telepon_pelanggan']"
    CONFIRM_PURCHASE_PRODUCT = "//node[@resource-id='com.telkomsel.digiposaja:id/order_name']"
    CONFIRM_PURCHASE_PRICE = "//node[@resource-id='com.telkomsel.digiposaja:id/order_total']"
    
    CONFIRM_PURCHASE_BUTTON = "//node[@resource-id='com.telkomsel.digiposaja:id/btn_bayar']"
    
    PIN_INPUT_TEXT_DELETE = "//node[@resource-id='com.telkomsel.digiposaja:id/text_delete']"
    
    DIALOG_TITLE_TEXT = "//node[@resource-id='com.telkomsel.digiposaja:id/dialog_title_txt']"
    DIALOG_SUBTITLE_TEXT = "//node[@resource-id='com.telkomsel.digiposaja:id/dialog_subtitle_txt']"
    
    BUTTON = "//node[@resource-id='com.telkomsel.digiposaja:id/btn']"
    CANCEL_BUTTON = "//node[@resource-id='com.telkomsel.digiposaja:id/cancel_btn']"
    YES_BUTTON = "//node[@resource-id='com.telkomsel.digiposaja:id/yes_btn']"


class DigiposAutomator(AutomatorPlugin):
    PACKAGE = 'com.telkomsel.digiposaja'
    LAUNCHER_ACTIVITY = 'id.co.dansmultipro.digipos.outletrevamp.activity.welcome.SplashScreenActivity'
    MAX_RECURSION = 3
    
    XPATH: XPathMap = XPathMap.from_python_cls(DigiposXPathCollection)
    
    @classmethod
    def configure(cls, config:Config):
        super().configure(config)
        cls.XPATH = XPathMap.from_file(config['xpath'])
        cls.PRODUCTS = ProductList.from_file(config['product_list'])
        cls.TRANSLATOR = Translator(**config['translator_config'])
        cls.APP_PIN: str = config['pin']
    
    def getNodesByText(self, nodeText):
        matchingNodes = self.device.getElementsByXPath(self.xpath.FORMATTABLE_NODE_TEXT_SELECTOR.format(nodeText))
        logger.debug('getNodesByText:nodeText={} matchingNodesSize={}'.format(nodeText, len(matchingNodes)))
        return matchingNodes

    def getNodeByText(self, nodeText, nodeIndex=0):
        matchingNodes = self.getNodesByText(nodeText)
        if len(matchingNodes) > nodeIndex:
            return matchingNodes[0]
    
    def tapNodeByText(self, node_text):
        node = self.device.getElementByXPath(self.xpath.FORMATTABLE_NODE_TEXT_SELECTOR.format(node_text))
        if node is not None:
            self.device.tapByElement(node)
    
    def verifyMain(self):
        bottom_navbar = self.device.getElementByXPath(self.xpath.DASHBOARD_BOTTOM_NAVIGATION)
        if bottom_navbar is not None:
            return True
        return False

    def verifyHomeMenu(self):
        if self.verifyMain():
            home_menu_icon = self.device.getElementByXPath(self.xpath.DASHBOARD_BOTTOM_NAVIGATION_HOME_MENU)
            if home_menu_icon is not None:
                return home_menu_icon.get('selected') == 'true'
            # username_element = self.device.getElementByXPath(self.xpath.USERNAME_TEXTVIEW)
            # if username_element is not None:
            #     return True
        return False
    
    def navigateToHome(self):
        maxTries, tries = 7, 0
        isMainMenu = False

        while tries < maxTries:
            self.device.refreshRoot()
            if self.verifyHomeMenu():
                return True
            self.device.input_keyevent(keycode.KEYCODE_BACK)
            Delay.randomSleep(1.3)
            tries += 1
        return False
    
    def closeExitDialog(self):
        dialog_subtitle = self.device.getElementByXPath(self.xpath.DIALOG_SUBTITLE_TEXT)
        if dialog_subtitle is not None and dialog_subtitle.get('text','').__contains__('keluar aplikasi'):
            if self.device.getElementByXPath(self.xpath.CANCEL_BUTTON) is not None:
                self.device.tapByXPath(self.xpath.CANCEL_BUTTON)
    
    def navigateTo(self, nodeText, menuText, initialRootRefresh=True):
        maxTries, tries = 7, 0
        
        if initialRootRefresh:
            self.device.refreshRoot()

        while tries < maxTries:
            isMain = self.verifyMain()
            isHomeMenu = self.verifyHomeMenu()
            isDialogPresent = self.device.getElementByXPath(self.xpath.DIALOG_SUBTITLE_TEXT) is not None
            isExitDialog = self.device.getElementByXPath(self.xpath.CANCEL_BUTTON) is not None
            isLauncher = self.device.getElementByXPath(self.xpath.SPLASH_SCREEN_APP_VERSION) is not None
            isDigiposActivity = self.device.getElementByXPath("//node[@package='{}']".format(self.PACKAGE)) is not None
            
            if isMain and not isHomeMenu:
                logger.debug("navigateTo:Try#{}:isMain={} isHomeMenu={} Switching to home menu.".format(tries, isMain, isHomeMenu))
                self.device.tapByXPath(self.xpath.DASHBOARD_BOTTOM_NAVIGATION_HOME_MENU)
            if isHomeMenu:
                node_element = self.getNodeByText(nodeText)
                if node_element is None:
                    scrollable = self.device.getElementByXPath(self.xpath.SCROLLABLE)
                    logger.debug('navigateTo:Try#{}:Node element is None and Scrollable found.'.format(tries))
                    if scrollable is not None:
                        self.device.swipe(scrollable, direction='DOWN')
                if node_element is not None:
                    self.device.tapByElement(node_element, rootRefresh=False)
                    logger.debug('navigateTo:Try#{}:Tapped node element and refreshed root.'.format(tries))
            
            if isDialogPresent:
                if isExitDialog:
                    dialog_subtitle = self.device.getElementByXPath(self.xpath.DIALOG_SUBTITLE_TEXT)
                    if dialog_subtitle is not None and dialog_subtitle.get('text','').__contains__('keluar aplikasi'):
                        self.device.tapByXPath(self.xpath.CANCEL_BUTTON)
                        logger.debug("navigateTo:Try#{}:Tapped cancel button on exit dialog.".format(tries))
                else:
                    self.device.tapByXPath(self.xpath.BUTTON)
                    logger.debug("navigateTo:Try#{}:Tapped button on normal dialog.".format(tries))
                    
            Delay.randomSleep(1.3, 0.25)
            self.device.refreshRoot()

            isRequestedMenu = self.device.getElementByXPath(self.xpath.FORMATTABLE_NODE_TEXT_SELECTOR.format(menuText))
            if isRequestedMenu is not None:
                logger.info('navigateTo:Try#{}:isRequestedMenu={}'.format(tries, isRequestedMenu))
                break

            if not isDigiposActivity:
                self.device.wakeUp()
                self.device.setTopActivity(self.PACKAGE, self.LAUNCHER_ACTIVITY)

            if not isMain and not isLauncher and not isExitDialog and isDigiposActivity:
                self.device.input_keyevent(keycode.KEYCODE_BACK)
                Delay.randomSleep(1, 0.25)
                self.device.refreshRoot()
            tries += 1
    
    def inputNumber(self, number: str):
        input_box = self.device.getElementByXPath(self.xpath.NUMBER_INPUT_BOX)
        if input_box is None:
            raise RuntimeError("inputNumber: input box not found.")
        self.device.tapByElement(input_box)
        Delay.randomSleep(1)
        logger.debug('inputNumber: Tapped input box and slept randomly.')
        self.device.input_text(number)
        self.device.input_keyevent(keycode.KEYCODE_BACK)
        Delay.randomSleep(1)
        self.device.refreshRoot()
        self.device.tapByXPath(self.xpath.CONFIRM_NUMBER_BUTTON)
        logger.debug('inputNumber: Done inputing number={} and submitted.'.format(number))
    
    def selectPackage(self, packageName):
        if self.device.getElementByXPath(self.xpath.FORMATTABLE_NODE_TEXT_SELECTOR.format(packageName)) is None:
            if not self.device.waitForElementsByXPath(self.xpath.SCROLL_VIEW, timeout=10, raiseErr=False):
                return False
            nd = self.device.getElementByXPath(self.xpath.SCROLL_VIEW)
            if nd is None:
                raise RuntimeError("selectPackage: scrollable is not found.")
            self.device.swipe(nd, direction='UP', rootRefresh=True)
            logger.debug("selectPackage: Swiped Up")
        self.device.tapByXPath(self.xpath.FORMATTABLE_NODE_TEXT_SELECTOR.format(packageName))
        logger.debug("selectPackage: Tapped package with name={}".format(packageName))
    
    def parseProducts(self, root):
        product_elements = Element.getElementsByXPath(root, self.xpath.PRODUCT)
        products = []
        for element in product_elements:
            try:
                item_name = Element.getElementByXPath(element, self.xpath.PRODUCT_NAME).get('text')
                item_desc = Element.getElementByXPath(element, self.xpath.PRODUCT_DESCRIPTION).get('text')
                item_price = Element.getElementByXPath(element, self.xpath.PRODUCT_PRICE).get('text')
                product = {'name': item_name, 'description': item_desc, 'price': item_price,
                        'bounds': element.get('bounds'), 'coordinates': Element.get_bounds(element)}
                products.append(product)
            except (KeyError, AttributeError):
                pass
        logger.info("parseProducts: parsed {} product(s).".format(len(products)))
        return products
    
    def productMatcher(self, products, product_spec: Union[List[dict], dict], matcher):
        if isinstance(product_spec, list):
            accumulated = [self.productMatcher(products, spec, matcher) for spec in product_spec]
            flattened_accumulated = [prod for prod_list in accumulated for prod in prod_list]
            # print(accumulated, flattened_accumulated)
            return flattened_accumulated
        return matcher.match(products, product_spec)
    
    def getProduct(self, product_spec, matcher=MatchAll, parseProducts=False) -> Optional[Union[dict, list]]:
        
        matchable_product_spec = self.PRODUCTS.get(product_spec.upper(), Product(matchers=[{'name':'INVALID'}]))
        
        parsed_products = []
        
        if parseProducts:
            matchable_product_spec = Product(matchers=[{'name':__import__('secrets').token_hex(10)}])
            logger.info("getProduct: parseProducts={}".format(parseProducts))
            logger.info("getProduct: Setting product_spec to an impossible value of {} for field name by using secrets.token_hex".format(matchable_product_spec))
        logger.info("getProduct: Searching With matchable_product_spec={} from product_spec={}, and matcher={}".format(matchable_product_spec, product_spec, matcher))
        
        scrollable_element = self.device.getElementByXPath(self.xpath.PRODUCTS_SCROLLABLE)
        if scrollable_element is None:
            self.device.wakeUp()
            self.device.waitForElementsByXPath(self.xpath.PRODUCTS_SCROLLABLE, timeout=10, raiseErr=False)
            scrollable_element = self.device.getElementByXPath(self.xpath.PRODUCTS_SCROLLABLE)
        
        if scrollable_element is None:
            raise RuntimeError("Scrollable is not found.")
        
        swipe_direction = 'UP'
        iter_count, max_iteration = 0, 15
        while iter_count < max_iteration:
            logger.info("getProduct: Iter#{} of collecting UI XML".format(iter_count))
            self.device.refreshRoot()
            if etree.tostring(self.device.root) == etree.tostring(self.device.lastRoot) and iter_count > 1:
                logger.debug("getProduct: No products matched.")
                if parseProducts:
                    return parsed_products
                return None
            
            products = self.parseProducts(self.device.root)
            parsed_products.extend(products)
            logger.debug("getProduct: parsed products: {}".format(products))
            matched_products = self.productMatcher(products, matchable_product_spec.matchers, matcher)
            if len(matched_products):
                return matched_products[0]
            
            self.device.swipe(scrollable_element, 4, direction=swipe_direction, duration=275)
            Delay.randomSleep(0.85, 0.07)
            iter_count+=1
            logger.debug("getProduct: swiped scrollable to the next batch of products & sleep for .5s")    
        
        logger.debug("getProduct: Iteration count limiter triggered! Iteration Limit={}".format(iter_count))
        if parseProducts:
            return parsed_products
        return None
    
    def getConfirmationData(self):
        self.device.refreshRoot()
        product_name = self.device.getElementByXPath(self.xpath.CONFIRM_PURCHASE_PRODUCT)
        price = self.device.getElementByXPath(self.xpath.CONFIRM_PURCHASE_PRICE)
        number = self.device.getElementByXPath(self.xpath.CONFIRM_PURCHASE_NUMBER)
        logger.info('getConfirmationData: Product={name=%s,price=%s} Number=%s' % (product_name, price, number))
        return {'name':product_name, 'price':price, 'number':number}
    
    def confirmPurchase(self):
        self.device.waitForElementsByXPath(self.xpath.CONFIRM_PURCHASE_BUTTON, timeout=5, raiseErr=False)
        element = self.device.getElementByXPath(self.xpath.CONFIRM_PURCHASE_BUTTON)
        if element is None:
            raise RuntimeError("Confirm purchase button is not found.")
        self.device.tapByElement(element)
        logger.debug("confirmPurchase: tapped purchase element.")
    
    def get_pin_input_coordinates(self):
        elements = {}
        number_elements = self.device.root.xpath("node//node[@text!='']")
        for el in number_elements:
            elements[el.get('text', 'INVALID_TEXT')] = el
        number_coordinates_pair = {name: Element.get_bounds(el) for name, el in elements.items()}
        return number_coordinates_pair
    
    def enterPin(self, pin: str):
        Delay.randomSleep(0.75, 0.025)
        self.device.refreshRoot()

        if self.device.u2_installed:
            self.device.waitForElementsByXPath(self.xpath.PIN_INPUT_TEXT_DELETE, timeout=5)

        input_coordinates = self.get_pin_input_coordinates()
        logger.debug("enterPin: refreshed root and parsed input coordinates.")

        coords = []

        for digit in str(pin):
            digit_coordinates = input_coordinates[str(digit)]
            coords.append(Bounds.get_center(digit_coordinates))
        self.device.multiTap(coords)

        logger.info("enterPin: Done input pin")

    def processRequest(self, request:Request, recursion=0):
        result = Result.from_request(request)
        result.update(refID=None, time=datetime.now())
        number = request.number
        product_spec=request.product_spec
        
        if recursion > 0:
            logger.debug("processRequest: called with recursion level={}".format(recursion))
        if recursion >= self.MAX_RECURSION:
            result.update({'refID': None, 'time': datetime.now(), 'description':self.t('max_recursion_error')})
            return result
        
        LOADING_OVERLAY_TIMEOUT = 15
        
        self.device.processing_request = True # used for the server to decide whether to put the request back to the queue or not.
        self.device.wakeUp()
        
        if recursion:
            try:
                self.device.stopApp(self.PACKAGE)
                Delay.randomSleep(2)
                self.device.setTopActivity(self.PACKAGE, self.LAUNCHER_ACTIVITY, force=True)
            except MaxTriesReachedError:
                pass
        else:
            self.device.setTopActivity(self.PACKAGE, self.LAUNCHER_ACTIVITY)
        
        # Delay.randomSleep(1)
        retry(self.device.waitForElementsNotExistsByXPath, args=(self.xpath.SPLASH_SCREEN_APP_VERSION,), kwargs=dict(timeout=10), 
                   successValidator=lambda *_:self.device.waitForElementsNotExistsByXPath(self.xpath.SPLASH_SCREEN_APP_VERSION, timeout=10) is True)
        logger.debug('processRequest: Splash screen passed')
        self.navigateTo('Telepon & SMS', 'Masukkan nomor telepon pelanggan', initialRootRefresh=False)

        Delay.randomSleep(1.5)
        try:
            self.inputNumber(number)
        except AttributeError:
            self.navigateTo('Telepon & SMS', 'Masukkan nomor telepon pelanggan', initialRootRefresh=False)
            Delay.randomSleep(1.5)
            self.inputNumber(number)
        
        try:
            self.device.waitForElementsNotExistsByXPath(self.xpath.DIALOG_SUBTITLE_TEXT, timeout=5)
            dialog_subtitle = self.device.getElementByXPath(self.xpath.DIALOG_SUBTITLE_TEXT)
            if dialog_subtitle is not None:
                dialog_subtitle_text = dialog_subtitle.get('text')
                if dialog_subtitle_text == 'Gagal mengambil profile pelanggan':
                    self.device.tapByXPath(self.xpath.BUTTON)
                    self.navigateToHome()
                    result.error = self.t('invalid_number')
                    return result
                if dialog_subtitle_text == 'Msisdn yang dimasukkan tidak sesuai.':
                    self.navigateToHome()
                    result.error = self.t('invalid_number')
                    return result
        except TimeoutError:
            pass
        
        Delay.randomSleep(1, 0.2)
        self.device.waitForElementsNotExistsByXPath(self.xpath.LOADING_OVERLAY, timeout=LOADING_OVERLAY_TIMEOUT)
        
        self.selectPackage('Paket Reguler')
        
        self.device.waitForElementsNotExistsByXPath(self.xpath.LOADING_OVERLAY, timeout=LOADING_OVERLAY_TIMEOUT)
        
        dialog_subtitle = self.device.getElementByXPath(self.xpath.DIALOG_SUBTITLE_TEXT)
        if dialog_subtitle is not None:
            # Dialog box after choosing offers
            dialog_subtitle_text = dialog_subtitle.get('text')
            if dialog_subtitle_text == 'Proses recharge tidak valid, pastikan no RS dan no pelanggan dalam keadaan aktif':
                self.device.tapByXPath(self.xpath.BUTTON)
                self.navigateToHome()
                result.error = self.t('expired_number')
                return result
            if dialog_subtitle_text == '30RV-0002 - Denom ini tidak tersedia saat ini, silakan pilih produk lain':
                self.navigateToHome()
                result.error = self.t('denom_unavailable')
                return result
        
        if self.device.getElementByXPath(self.xpath.FORMATTABLE_NODE_TEXT_SELECTOR.format('Terjadi kesalahan pada sistem')) is not None:
            # something something error :/
            self.device.tapByXPath(self.xpath.BUTTON)
        try:
            product = self.getProduct(product_spec, MatchAll)
            if product is None:
                logger.error("processRequest: Product {} is not found".format(product_spec))
                result.error=self.t('product_not_found')
                return result
        except TimeoutError:
            return self.processRequest(request, recursion=recursion+1)
        
        assert(isinstance(product, dict))
        
        self.device.tapByElement(product)
        
        Delay.randomSleep(1)
        try:
            self.device.waitForElementsNotExistsByXPath(self.xpath.LOADING_OVERLAY, timeout=LOADING_OVERLAY_TIMEOUT)
        except TimeoutError:
            return self.processRequest(request, recursion=recursion+1)

        # Product confirmation
        confirmation_data = self.PRODUCTS.get(product_spec, Product([{'name':product_spec}])).confirmation
        confirmedProduct = self.getConfirmationData()
        correct_product=False
        if any([all(MatchAll.match([confirmedProduct], confirmer)) for confirmer in confirmation_data]):
            correct_product = True
        correct_num = confirmedProduct.get('number', {}).get('text', '').__contains__(Number.converter(number, sep='-')) #type:ignore
        correct_data = correct_product and correct_num

        logger.debug("ConfirmationPage: Product={name=%s, price=%s} (%s) Number=%s (%s)" % (
            confirmedProduct.get('name').get('text'), confirmedProduct.get('price').get('text'), ('Matched' if correct_product else 'Not Matched'), #type:ignore
            confirmedProduct.get('number').get('text'), ('Matched' if correct_num else 'Not Matched'))) #type:ignore
        if not (correct_data):
            logger.warning('Please leave the device on its own.')
            logger.info('Product or number is wrong. Retrying.')
            return self.processRequest(request, recursion=recursion+1)
        
        self.confirmPurchase()
        
        self.device.waitForElementsNotExistsByXPath(self.xpath.LOADING_OVERLAY, timeout=LOADING_OVERLAY_TIMEOUT)
        
        try:
            self.enterPin(self.app_pin)
        except TimeoutError:
            logger.info('Pin input box missing. Retrying.')
            return self.processRequest(request, recursion=recursion+1)
        
        self.device.processing_request = False
        
        self.navigateToHome()
        result.update(refID="RANDOM:"+secrets.token_hex(12), time=datetime.now(), send_reply=False)
        return result
