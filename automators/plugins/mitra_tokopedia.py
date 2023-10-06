from datetime import datetime
from typing import List, Optional, Union

from lxml import etree
from ppadb import keycode

from automators.data_structs import Config, Product, ProductList
from automators.xpath import XPathMap
from automators.plugins.base import AutomatorPlugin
from automators.request import Request
from automators.result import Result
from automators.ui.element import Element
from automators.utils.delay import Delay
from automators.utils.ext.match import MatchAll
from automators.utils.ext.product import PriceRE
from automators.utils.helper import retry
from automators.utils.translator import Translator
from automators.utils.logger import Logging
from automators.utils.exception import MaxTriesReachedError


logger = Logging.get_logger(__name__)


class MitraTokopediaXPathCollection:
    SPLASH_SCREEN_VIEW = "//node[@resource-id='com.tokopedia.kelontongapp:id/layout_splash']"
    DASHBOARD_BOTTOM_NAVIGATION_ITEM = "//node[@text='unf-bottomnav-item']"
    DASHBOARD_BOTTOM_NAVIGATION_HOME_MENU = "//node[@resource-id='tabHomeBeranda']"
    GOPAY_COINS = "//node[@resource-id='gopay-coins']"
    GOPAY_BALANCE = "//node[@resource-id='gopay-coins']/node[@index='1']"
    # PAKET_DATA_MENU_SELECTOR = "//node[node[@text='Produk Digital']]/node[@index='2']/node[@index='1']"
    
    NUMBER_INPUT_PAD = "//node[@resource-id='android:id/inputArea']"
    NUMBER_INPUT_PAD_ENTER = "//node[@resource-id='com.google.android.inputmethod.latin:id/key_pos_ime_action']"
    
    NUMBER_INPUT_BOX = "//node[@class='android.widget.EditText']"
    EMPTY_NUMBER_INPUT_BOX = "//node[@class='android.widget.EditText' and @text='']"
    
    PRODUCTS_SCROLLABLE = "//node[@class='android.widget.RelativeLayout']//node[@resource-id='content']"
    
    PRODUCT = PRODUCTS_SCROLLABLE+"/node"
    PRODUCT_NAME = "./node[@index='0']"
    PRODUCT_DESCRIPTION = "./node[@index='2']"
    PRODUCT_PRICE = "./node[@index='1']"
    
    PRODUCT_SPECIAL_INFO = "./node[@index='5']"
    PRODUCT_PROMO_TEXT = "./node[@index='5']/node[@text='Promo']"
    PRODUCT_NEW_TEXT = "./node[@index='5']/node[@text='Baru']"
    PRODUCT_OUT_OF_STOCK = "./node[@index='5']/node[@text='Habis']"
    
    PRODUCT_NAME_PROMO = "./node[@index='0']"
    PRODUCT_DESCRIPTION_PROMO = "./node[@index='4']"
    PRODUCT_PRICE_PROMO = "./node[@index='1']"
    PRODUCT_ORIGINAL_PRICE_PROMO = "./node[@index='3']"
    
    PROMO_BUTTON = "//node[node/node[@text='Gunakan kode promo' or @text='Punya kode promo atau kupon?']]"
    # PROMO_BUTTON = "//node[node/node[@text='Gunakan kode promo']]"
    # PROMO_BUTTON = "//node[node/node[@text='Punya kode promo atau kupon?']]"

    SELECT_PAYMENT_OPTION_BUTTON = "//node[@class='android.widget.Button' and @text='Pilih Pembayaran']"
    
    CONFIRMATION_TOTAL_PAYMENT_PARENT_NODE = "//node[node[@text='Total Tagihan']]"
    
    QUICKPAY_BUTTON = "//node[@resource-id='btn-quickpay-pay']"
    
    PIN_INPUT_BOX = "//node[@class='android.widget.EditText']"
    PIN_CONFIRM_BUTTON = "//node[@resource-id='PreAuth PIN']"
    
    ATUR_HARGA_JUAL = "//node[@resource-id='btnRevenueAction']"
    TRANSACTION_STATUS_TX_PARENT_NODE = "//node[node[@text='status-tx']]"
    TRANSACTION_RESULT_SERIAL_NUMBER = "//node[@resource-id='invoice-value-Serial Number']"
    TRANSACTION_RESULT_BACK_BUTTON = "//node[@resource-id='btnThankYouHomepage']"
    
    BACKSPACE_BUTTON = "//node[@resource-id='com.google.android.inputmethod.latin:id/key_pos_number_line3_4']"


class MitraTokopediaAutomator(AutomatorPlugin):
    PACKAGE = 'com.tokopedia.kelontongapp'
    LAUNCHER_ACTIVITY = '.main.view.KelontongMainActivity' # Sometimes the activity must be prefixed with '.' to work.
    MAX_RECURSION = 3
    SKIP_OUT_OF_STOCK = False
    
    XPATH: XPathMap = XPathMap.from_python_cls(MitraTokopediaXPathCollection)
    
    @classmethod
    def configure(cls, config:Config):
        super().configure(config)
        cls.XPATH = XPathMap.from_file(config['xpath'])
        cls.PRODUCTS = ProductList.from_file(config['product_list'])
        cls.TRANSLATOR = Translator(**config['translator_config'])
        cls.APP_PIN: str = config['pin']
        cls.SKIP_OUT_OF_STOCK = config['skip_out_of_stock']
    
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
        if node is None:
            return
        self.device.tapByElement(node)

    def verifyMain(self):
        bottom_nav = self.device.getElementByXPath(self.xpath.DASHBOARD_BOTTOM_NAVIGATION_ITEM)
        if bottom_nav is not None:
            return True
        return False

    def verifyHomeMenu(self):
        if self.verifyMain():
            gopay_coins = self.device.getElementByXPath(self.xpath.GOPAY_COINS)
            if gopay_coins is not None:
                return True
        return False
    
    def navigateToHome(self):
        maxTries, tries = 7, 0

        while tries < maxTries:
            self.device.refreshRoot()
            if self.verifyHomeMenu():
                return True
            self.device.input_keyevent(keycode.KEYCODE_BACK)
            Delay.randomSleep(1.5, 0.25)
            tries += 1
        return False
    
    def navigateTo(self, nodeText, menuText, recursion=0):
        maxTries, tries = 6, 0
        logger.debug("navigateTo: called with nodeText='{}' menuText='{}' recursion={}".format(nodeText, menuText, recursion))
        if recursion >= 3:
            logger.debug("navigateTo: Failed to reach destination in 3 recursions, returning. ")
            return

        while tries < maxTries:
            tries += 1
            Delay.randomSleep(1.7, 0.25)
            self.device.refreshRoot()
            
            isRequestedMenu = self.device.getElementByXPath(self.xpath.FORMATTABLE_NODE_TEXT_SELECTOR.format(menuText))
            # logger.info(f"{isRequestedMenu=}")
            if isRequestedMenu is not None:
                logger.debug('navigateTo:Try#{}:isRequestedMenu={}'.format(tries, isRequestedMenu))
                return
            
            isHomeMenu = self.verifyHomeMenu()
            # logger.info(f"{isHomeMenu=}")
            if isHomeMenu: # in the correct location and section, next is to navigate to the submenu.
                node_element = self.getNodeByText(nodeText)
                if node_element is None:
                    scrollable = self.device.getElementByXPath(self.xpath.SCROLLABLE)
                    logger.debug('navigateTo:Try#{}:Node element is None and Scrollable found.'.format(tries))
                    if scrollable is not None:
                        self.device.swipe(scrollable, direction='DOWN')
                else:
                    self.device.tapByElement(node_element, rootRefresh=False)
                    logger.debug('navigateTo:Try#{}:Tapped node element and refreshed root.'.format(tries))
                    Delay.randomSleep(1.5, 0.2)
                continue
            
            isMain = self.verifyMain()
            # logger.info(f"{isMain=}")
            if isMain: # In "Main" location, but not the right section
                logger.debug("navigateTo:Try#{}:isMain={} isHomeMenu={} Switching to home menu.".format(tries, isMain, isHomeMenu))
                self.device.tapByXPath(self.xpath.DASHBOARD_BOTTOM_NAVIGATION_HOME_MENU)
                Delay.randomSleep(1.5, 0.2)
                continue
            
            isLauncher = self.device.getElementByXPath(self.xpath.SPLASH_SCREEN_VIEW) is not None
            # logger.info(f"{isLauncher=}")
            if isLauncher: # current pos: launcher
                Delay.randomSleep(2, 0.2)
                continue
            
            isMitraTKPDActivity = self.device.getElementByXPath("//node[@package='{}']".format(self.PACKAGE)) is not None
            # logger.info(f"{isMitraTKPDActivity=}")
            if isMitraTKPDActivity: # current pos: somewhere in the app, not in main and launcher
                self.device.input_keyevent(keycode.KEYCODE_BACK)
                Delay.randomSleep(1.5, 0.2)
                continue
            
            # outside the app.
            self.device.wakeUp()
            self.device.setTopActivity(self.PACKAGE, self.LAUNCHER_ACTIVITY)
        self.device.setTopActivity(self.PACKAGE, self.LAUNCHER_ACTIVITY, force=True)
        return self.navigateTo(nodeText, menuText, recursion=recursion+1)

    def inputNumber(self, number: str):
        self.device.waitForElementsByXPath(self.xpath.NUMBER_INPUT_BOX, timeout=9)
        input_box = self.device.getElementByXPath(self.xpath.NUMBER_INPUT_BOX)
        if input_box is None:
            raise RuntimeError("inputNumber: Input box could not be found.")
        
        self.device.tapByElement(input_box)
        inputed_number_len = len(input_box.get('text', ''))
        if inputed_number_len > 0:
            logger.debug("inputNumber: Removing numbers in the input box.")
            try:
                self.device.waitForElementsByXPath(self.xpath.BACKSPACE_BUTTON, timeout=5)
            except TimeoutError:
                return False
            backspace_button = self.device.getElementByXPath(self.xpath.BACKSPACE_BUTTON)
            if backspace_button is None:
                return False
            backspace_coordinates = Element.get_center_from_element(backspace_button)
            self.device.multiTap([backspace_coordinates]*inputed_number_len)
            Delay.randomSleep(1, 0.3)
            logger.debug("inputNumber: numbers removed.")
        
        Delay.randomSleep(1, 0.2)
        
        logger.debug('inputNumber: Tapped input box and slept randomly.')
        self.device.refreshRoot()
        self.device.input_text(number)
        if self.device.getElementByXPath(self.xpath.NUMBER_INPUT_PAD) is not None:
            self.device.tapByXPath(self.xpath.NUMBER_INPUT_PAD_ENTER)
            Delay.randomSleep(1)
        logger.debug('inputNumber: Done inputing number={}.'.format(number))
        return True

    def parseProducts(self, root):
        product_elements = Element.getElementsByXPath(root, self.xpath.PRODUCT)
        products = []
        for element in product_elements:
            try:
                
                if Element.getElementByXPath(element, self.xpath.PRODUCT_SPECIAL_INFO) is not None:
                    product = {'name': Element.getElementByXPath(element, self.xpath.PRODUCT_NAME_PROMO).get('text'),
                               'description': Element.getElementByXPath(element, self.xpath.PRODUCT_DESCRIPTION_PROMO).get('text'),
                               'price': Element.getElementByXPath(element, self.xpath.PRODUCT_PRICE_PROMO).get('text'),
                               'original_price': Element.getElementByXPath(element, self.xpath.PRODUCT_ORIGINAL_PRICE_PROMO).get('text'),
                               'special_info': Element.getElementByXPath(element, self.xpath.PRODUCT_SPECIAL_INFO).get('text')}
                    if self.__class__.SKIP_OUT_OF_STOCK:
                        if product.get('special_info','') == 'Habis':
                            continue
                else:
                    product = {'name': Element.getElementByXPath(element, self.xpath.PRODUCT_NAME).get('text'),
                               'description': Element.getElementByXPath(element, self.xpath.PRODUCT_DESCRIPTION).get('text'),
                               'price': Element.getElementByXPath(element, self.xpath.PRODUCT_PRICE).get('text')}
                if len(product.get('name', '')) <= 0:
                    continue
                product.update({'bounds': element.get('bounds'), 'coordinates': Element.get_bounds(element)})
                products.append(product)
            except (KeyError, AttributeError):
                pass
        logger.info("parseProducts: parsed {} product(s).".format(len(products)))
        if len(products) <= 0:
            if not any([len(el.getchildren()) > 0 for el in product_elements]):
                logger.debug("parseProducts: View does not have required nodes for product parsing, raising runtime error.".format(len(products)))
                raise RuntimeError("View does not have required nodes for product parsing.")
        return products
    
    def productMatcher(self, products, product_spec: Union[List[dict], dict], matcher):
        if isinstance(product_spec, list):
            accumulated = [self.productMatcher(products, spec, matcher) for spec in product_spec]
            flattened_accumulated = [prod for prod_list in accumulated for prod in prod_list]
            # print(accumulated, flattened_accumulated)
            return flattened_accumulated
        return matcher.match(products, product_spec)
    
    def getProduct(self, product_spec, matcher=MatchAll, reverse=False, fastest=True, parseProducts=False, skip_preswipe=False) -> Optional[Union[dict, List[dict]]]:
        
        input_product_spec=product_spec.upper()
        product_spec = self.PRODUCTS.get(product_spec.upper(), Product([{'name':'INVALID_PRODUCT_SPEC'}]))
        
        parsed_products = []
        
        if parseProducts:
            product_spec = Product([{'name':'INVALID_PRODUCT_SPEC'}])
            logger.info("getProduct: parseProducts={}".format(parseProducts))
            logger.info("getProduct: Setting product_spec to an impossible value.".format(product_spec))
        logger.info("getProduct: Searching With product_spec={} from input_product_spec={}, and matcher={}".format(product_spec, input_product_spec, matcher))
        
        scrollable_element = self.device.getElementByXPath(self.xpath.PRODUCTS_SCROLLABLE)
        if scrollable_element is None:
            self.device.wakeUp()
            self.device.waitForElementsByXPath(self.xpath.PRODUCTS_SCROLLABLE, timeout=10)
            scrollable_element = self.device.getElementByXPath(self.xpath.PRODUCTS_SCROLLABLE)
        
        if scrollable_element is None:
            raise RuntimeError("getProduct: scrollable is not found.")
        
        if product_spec.location_near_bottom:
            reverse = not reverse
            logger.debug(f"getProduct: swiped scrollable to bottom")
        
        if not skip_preswipe and (not fastest or reverse):
            self.device.multiSwipe(scrollable_element, 5, direction=('DOWN' if not reverse else 'UP'), durationEach=200, swipeCount=7)
        
        swipe_direction = 'UP' if not reverse else 'DOWN'

        iter_count, max_iteration = 0, 20
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
            matched_products = self.productMatcher(products, product_spec.matchers, matcher)
            if len(matched_products):
                logger.debug("getProduct: matched product={}".format(matched_products[0]))
                return matched_products[0]
            
            self.device.swipe(scrollable_element, 4, direction=swipe_direction, duration=350)
            Delay.randomSleep(0.85, 0.07)
            iter_count+=1
            logger.debug("getProduct: swiped scrollable to the next batch of products & sleep for .5s")    
        
        logger.debug("getProduct: Iteration count limiter triggered! Iteration Limit={}".format(iter_count))
        if parseProducts:
            return parsed_products
        return None
    
    def mitratkpd_enterPin(self, pin: str):
        self.device.waitForElementsByXPath(self.xpath.PIN_INPUT_BOX)
        self.device.tapByXPath(self.xpath.PIN_INPUT_BOX)
        Delay.randomSleep(1, 0.025)
        self.device.input_text(pin)
        
        self.device.input_keyevent('ENTER')
        logger.info("mitratkpd_enterPin: Done input pin")

    def mitratkpd_parseResult(self):
        res = {}
        Delay.randomSleep(1, 0.3)
        try:
            if self.device.waitForElementsByXPath(self.xpath.TRANSACTION_RESULT_SERIAL_NUMBER, timeout=10):
                el = self.device.getElementByXPath(self.xpath.TRANSACTION_RESULT_SERIAL_NUMBER)
                res['refID'] = None
                if el is not None:
                    res['refID'] = el.get('text', None)
        except TimeoutError:
            pass
        
        xml_str = etree.tostring(self.device.root)
        if isinstance(xml_str, bytes):
            logger.debug('Decoded xml_str from <bytes> to <str>')
            xml_str = xml_str.decode('utf-8')
        if xml_str.__contains__('Transaksi Gagal'):
            res['description'] = 'Transaction failed'
        logger.debug("mitratkpd_parseResult: parsed {}".format(res))
        return res

    def processRequest(self, request: Request, recursion=0):
        result = Result.from_request(request)
        result.update(refID=None, time=datetime.now())
        number=request.number
        product_spec=request.product_spec
        
        if recursion > 0:
            logger.debug("processRequest: called with recursion level={}".format(recursion))
        if recursion >= self.MAX_RECURSION:
            result.update({'refID': None, 'time': datetime.now(), 'description':self.t('max_recursion_error')})
            return result
        
        self.device.processing_request = True # used for the server to decide whether to put the request back to the queue or not.
        self.device.wakeUp()
        
        if recursion:
            self.device.stopApp(self.PACKAGE)
            Delay.randomSleep(2)
            self.device.setTopActivity(self.PACKAGE, self.LAUNCHER_ACTIVITY, force=True)
        else:
            self.device.setTopActivity(self.PACKAGE, self.LAUNCHER_ACTIVITY)
        
        
        # num_header="No. Tujuan"
        num_header="Masukkan Nomor HP"
        
        self.navigateTo("Paket Data", num_header)
        
        
        try:
            self.device.waitForElementsByXPath(self.xpath.FORMATTABLE_NODE_TEXT_SELECTOR.format(num_header), timeout=10)
        except TimeoutError:
            try:
                self.navigateTo("Paket Data", num_header)
                self.device.waitForElementsByXPath(self.xpath.FORMATTABLE_NODE_TEXT_SELECTOR.format(num_header), timeout=5)
            except TimeoutError:
                return self.processRequest(request, recursion=recursion+1)
        
        try:
            try:
                self.inputNumber(number)
            except (TimeoutError):
                self.navigateTo("Paket Data", num_header)
                self.device.waitForElementsByXPath(self.xpath.FORMATTABLE_NODE_TEXT_SELECTOR.format(num_header), timeout=5)
                self.inputNumber(number)
        except (TimeoutError):
            return self.processRequest(request, recursion=recursion+1)
        
        Delay.randomSleep(1, 0.2)
        self.device.refreshRoot()
        
        try:
            self.device.waitForElementsNotExistsByXPath(self.xpath.NUMBER_INPUT_PAD, timeout=7)
        except TimeoutError:
            self.device.input_keyevent(keycode.KEYCODE_BACK)
        
        try:
            self.device.waitForElementsByXPath(self.xpath.FORMATTABLE_NODE_TEXT_SELECTOR.format(number), timeout=7)
        except TimeoutError:
            pass
        
        input_box = self.device.getElementByXPath(self.xpath.NUMBER_INPUT_BOX)
        if input_box is None or not input_box.get('text').__contains__(number):
            return self.processRequest(request, recursion=recursion+1)
        
        try:
            product = self.getProduct(product_spec)
            
            if product is None:
                product = self.getProduct(product_spec, reverse=True)
                if product is None:
                    logger.error("processRequest: Product {} is not found".format(product_spec))
                    result.error=self.t('product_not_found')
                    return result
        except RuntimeError:
            logger.debug("processRequest: Product not found, retrying.")
            return self.processRequest(request, recursion=recursion+1)
        
        if product.get('special_info', '').__contains__('Habis'): #type:ignore
            result.description=self.t('product_out_of_stock')
            return result
        
        Delay.randomSleep(0.5, 0.2)
        self.device.refreshRoot()
        
        try:
            logger.debug("processRequest: Reconfirming product...")
            product = self.getProduct(product_spec, skip_preswipe=True)
            if product is not None:
                assert(isinstance(product, dict))
                product['coordinates'] = self.device.getClickableRegion(product, self.device.getElementByXPath(self.xpath.PROMO_BUTTON))
                try:
                    self.device.tapByElement(product)
                except AssertionError:
                    scrollable_element = self.device.getElementByXPath(self.xpath.PRODUCTS_SCROLLABLE)
                    
                    assert(isinstance(scrollable_element, etree.ElementBase))
                    self.device.swipe(scrollable_element, 3, direction='UP', duration=500)
                    product = self.getProduct(product_spec, skip_preswipe=True)
                    
                    assert(isinstance(product, dict))
                    product['coordinates'] = self.device.getClickableRegion(product, self.device.getElementByXPath(self.xpath.PROMO_BUTTON))
                    self.device.tapByElement(product)
            else:
                raise RuntimeError()
        except (RuntimeError, AssertionError):
            logger.debug("processRequest: Product not found, retrying.")
            return self.processRequest(request, recursion=recursion+1)
        
        
        Delay.randomSleep(1.5)
        
        try:
            retry(lambda: self.device.tapByXPath(self.xpath.SELECT_PAYMENT_OPTION_BUTTON), 
                    successValidator=lambda _: self.device.waitForElementsByXPath(self.xpath.QUICKPAY_BUTTON, timeout=5, raiseErr=False),
                    logInfo="Trying to select payment option")
        except MaxTriesReachedError:
            logger.debug("processRequest: Payment Option not found, retrying.")
            return self.processRequest(request, recursion=recursion+1)
        
        try:
            self.device.waitForElementsByXPath(self.xpath.QUICKPAY_BUTTON, timeout=15)
        except TimeoutError:
            xml_str = etree.tostring(self.device.root)
            if isinstance(xml_str, bytes):
                logger.debug('Decoded xml_str from <bytes> to <str>')
                xml_str = xml_str.decode('utf-8')
            if xml_str.__contains__('GoPay'):
                result.error=self.t('product_out_of_stock')
            else:
                result.error=self.t('gopay_credit_insufficient')
            return result
            
        # xml_str = etree.tostring(self.device.root)
        xml_str = etree.tostring(self.device.getElementByXPath(self.xpath.CONFIRMATION_TOTAL_PAYMENT_PARENT_NODE))
        if isinstance(xml_str, bytes):
            logger.debug('Decoded xml_str from <bytes> to <str>')
            xml_str = xml_str.decode('utf-8')
        
        # to support callables and exact match
        if not len(MatchAll.match([{'price':PriceRE.search(xml_str).group()}], {'price': product.get('price')})) > 0: # type:ignore
            logger.debug("processRequest: Different price listed in the confirmation view with the product. Retrying.")
            return self.processRequest(request, recursion=recursion+1)
        logger.debug("processRequest: Checked price. Product price={} is {} in xml_str.".format(product.get('price'), 'found' if (xml_str.__contains__(product.get('price'))) else 'not found')) # type:ignore
        
        self.device.tapByXPath(self.xpath.QUICKPAY_BUTTON)
        
        self.mitratkpd_enterPin(self.app_pin)
        self.device.processing_request = False
        
        
        try:
            self.device.waitForElementsByXPath(self.xpath.ATUR_HARGA_JUAL, timeout=15)
            self.device.waitForElementsByXPath(self.xpath.SCROLLABLE, timeout=5)
            scrollable=self.device.getElementByXPath(self.xpath.SCROLLABLE)
            assert(scrollable is not None)
            self.device.swipe(scrollable, direction='UP')
            res = self.mitratkpd_parseResult()
            result.update({'time':datetime.now()})
            result.update(res)
            if result.refID is None:
                raise TimeoutError()
            logger.debug("processRequest: Transaction Finished. Result={}".format(result))
        except TimeoutError:
            result.update({'refID': '?', 'time':datetime.now(), 'description': 'Timed out when waiting for transaction result.'})
            element = self.device.getElementByXPath(self.xpath.SCROLL_VIEW)
            if element is not None:
                if etree.tostring(element).__contains__('Gagal'):
                    result.update({'refID': None, 'time':datetime.now(), 'description': 'Transaction failed.'})
        
        self.navigateToHome()
        
        try:
            if self.device.waitForElementsByXPath(self.xpath.GOPAY_COINS, timeout=10):
                balance_el = self.device.getElementByXPath(self.xpath.GOPAY_BALANCE)
                assert(balance_el is not None)
                balance = balance_el.get('text')
                result.update({'balance':balance}) if balance is not None else None
        except TimeoutError:
            pass
        
        return result
