
from datetime import datetime
import re
import sys
import time
from typing import List, Optional, Union
from lxml import etree
from ppadb import keycode

from automators.device import Device
from automators.request import Request
from automators.result import Result
from automators.ui.bounds import Bounds
from automators.ui.element import Element
from automators.utils.exception import MaxTriesReachedError, ReceiptNotFoundError
from automators.utils.ext.match import MatchAll
from automators.utils.ext.number import Number
from automators.utils.helper import retry
from automators.utils.decorators import after, before
from automators.xpath import BaseXPathCollection
from automators.data_structs import Config, Product, ProductList
from automators.xpath import XPathMap
from automators.plugins.base import AutomatorPlugin
from automators.utils.delay import Delay
from automators.utils.logger import Logging
from automators.utils.translator import Translator


logger = Logging.get_logger(__name__)


class LinkajaXPathCollection:
    SPLASH_SCREEN_APP_VERSION = "//node[@resource-id='com.telkom.mwallet:id/view_splash_version_textview']"

    PROMO_MESSAGE_OVERLAY = "//node[@resource-id='com.telkom.mwallet:id/com_appboy_inappmessage_modal_frame']"
    PROMO_MESSAGE_OVERLAY_CLOSE_BUTTON = "//node[@resource-id='com.telkom.mwallet:id/com_appboy_inappmessage_modal_close_button']"
    """XPath collection class for linkaja version 4.18.1 and higher."""
    TOOLBAR = "//node[@resource-id='com.telkom.mwallet:id/header_toolbar']"
    TOOLBAR_TEXT = TOOLBAR + "//node[@resource-id='com.telkom.mwallet:id/title_toolbar']"
    TOOLBAR_SUBTITLE = "//node[@resource-id='com.telkom.mwallet:id/subtitle_toolbar']"

    BALANCE_TEXTVIEW = "//node[@resource-id='com.telkom.mwallet:id/text_balance']"
    DASHBOARD_BOTTOM_NAVIGATION = "//node[@resource-id='com.telkom.mwallet:id/nav_view']"
    DASHBOARD_BOTTOM_NAVIGATION_HOME_MENU = DASHBOARD_BOTTOM_NAVIGATION + "//node[@resource-id='com.telkom.mwallet:id/menu_item_home']//node[@resource-id='com.telkom.mwallet:id/navigation_bar_item_large_label_view']"
    DASHBOARD_MENU_ITEM_ICON = "//node[@resource-id='com.telkom.mwallet:id/navigation_bar_item_icon_view']"
    DASHBOARD_PROFILE = "//node[@resource-id='com.telkom.mwallet:id/dashboard_profile_view']"
    USERNAME_TEXTVIEW = DASHBOARD_PROFILE + "//node[@resource-id='com.telkom.mwallet:id/txt_username']"
    DASHBOARD_REFRESH_SCROLLABLE = "//node[@resource-id='com.telkom.mwallet:id/swipe_refresh_layout']"

    NUMBER_INPUT_BOX = "node//node[@resource-id='com.telkom.mwallet:id/edit_field']"
    NUMBER_INPUT_CLEAR = "node//node[@resource-id='com.telkom.mwallet:id/clear_field']"
    NEXT_BUTTON = "node//node[@resource-id='com.telkom.mwallet:id/next_button' or @text='Lanjut']"

    PRODUCTS_SCROLLABLE = "//node[@resource-id='com.telkom.mwallet:id/view_collection_recyclerview']"
    PRODUCT = "node" + PRODUCTS_SCROLLABLE + "//node[@clickable='true']"
    PRODUCT_LOADING = "//node[@resource-id='com.telkom.mwallet:id/progress_status']"
    PRODUCT_TITLE = "//node[@resource-id='com.telkom.mwallet:id/view_denom_generic_title_textview' or @resource-id='com.telkom.mwallet:id/label_denom_pulsa_data_title']"
    PRODUCT_DESCRIPTION = "//node[@resource-id='com.telkom.mwallet:id/view_denom_generic_description_textview' or @resource-id='com.telkom.mwallet:id/label_denom_pulsa_data_description']"
    PRODUCT_PRICE = "//node[@resource-id='com.telkom.mwallet:id/view_denom_generic_price_textview' or @resource-id='com.telkom.mwallet:id/label_denom_pulsa_data_price']"

    CONFIRMATION_DETAILS = "//node[node[@resource-id='com.telkom.mwallet:id/form_key']]//node[@text='Telkomsel Data']"
    CONFIRMATION_NUMBER_DETAIL = CONFIRMATION_DETAILS + "/parent::node/following-sibling::node//node[@resource-id='com.telkom.mwallet:id/form_key']"
    
    BOTTOM_ERROR_MESSAGE = "//node[@resource-id='com.telkom.mwallet:id/message_snackbar']" 

    CONFIRM_BUTTON = "//node[@resource-id='com.telkom.mwallet:id/button_confirm']"

    BLOCKING_ILLUST_VIDEOVIEW = "//node[@resource-id='com.telkom.mwallet:id/view_support_blocking_imagevideo_container']"

    TRANSACTION_NOTE_CONTAINER = "//node[@resource-id='com.telkom.mwallet:id/dialog_transaction_note_container']"
    TRANSACTION_RECEIPT = TRANSACTION_NOTE_CONTAINER + BaseXPathCollection.SCROLL_VIEW

    TRANSACTION_DONE_LABEL = "//node[@resource-id='com.telkom.mwallet:id/view_transaction_note_action_done_label']"

    # Because there is an identical element(by xpath) in the view xml. Being more specific is never gonna hurt.
    REF_AND_DATE_PARENT_NODE_SELECTOR = "//node[@class='android.widget.LinearLayout' and node[@resource-id='com.telkom.mwallet:id/form_value'] and node[@resource-id='com.telkom.mwallet:id/form_key']]"
    TRANSACTION_REFERENCE_TEXTVIEW = REF_AND_DATE_PARENT_NODE_SELECTOR + "//node[@resource-id='com.telkom.mwallet:id/form_value']"
    TRANSACTION_DATE_TEXTVIEW = REF_AND_DATE_PARENT_NODE_SELECTOR + "//node[@resource-id='com.telkom.mwallet:id/form_key']"


class LinkajaAutomator(AutomatorPlugin):
    PACKAGE = 'com.telkom.mwallet'
    LAUNCHER_ACTIVITY = 'com.linkaja.customer.MainActivity'
    RESULT_ACTIVITY = 'module.features.result.presentation.ui.activity.TransactionResultActivity'
    MAX_RECURSION=3
    
    XPATH: XPathMap = XPathMap.from_python_cls(LinkajaXPathCollection)
    
    def __init__(self, device: Device):
        super().__init__(device)
        self.watchers=[self.closeMTPWarning, self.closeNotResponding]
    
    @classmethod
    def configure(cls, config:Config):
        super().configure(config)
        cls.XPATH = XPathMap.from_file(config['xpath'])
        cls.PRODUCTS = ProductList.from_file(config['product_list'])
        cls.TRANSLATOR = Translator(**config['translator_config'])
        cls.APP_PIN: str = config['pin']
    
    def getToolbar(self):
        return self.device.getElementByXPath(self.xpath.TOOLBAR)

    def getToolbarText(self):
        toolbar_container = self.device.getElementByXPath(self.xpath.TOOLBAR_TEXT)
        if toolbar_container is not None:
            return toolbar_container.get('text')

    def getToolbarSubtitle(self):
        toolbar_subtitle = self.device.getElementByXPath(self.xpath.TOOLBAR_SUBTITLE)
        if toolbar_subtitle is not None:
            return toolbar_subtitle.get('text')

    def verifyMain(self):
        bottom_navbar = self.device.getElementByXPath(self.xpath.DASHBOARD_BOTTOM_NAVIGATION)
        if bottom_navbar is not None:
            return True
        return False

    def verifyHomeMenu(self):
        if self.verifyMain():
            username_element = self.device.getElementByXPath(self.xpath.USERNAME_TEXTVIEW)
            if username_element is not None:
                return True
        return False

    def getNodesByText(self, nodeText):
        matchingNodes = self.device.getElementsByXPath(self.xpath.FORMATTABLE_NODE_TEXT_SELECTOR.format(nodeText))
        logger.debug('getNodesByText:nodeText={} matchingNodesSize={}'.format(nodeText, len(matchingNodes)))
        return matchingNodes

    def getNodeByText(self, nodeText, nodeIndex=0):
        matchingNodes = self.getNodesByText(nodeText)
        if len(matchingNodes) > nodeIndex:
            return matchingNodes[0]

    def navigateToHome(self):
        maxTries, tries = 5, 0

        while tries < maxTries:
            self.device.refreshRoot()
            if self.verifyHomeMenu():
                return True
            self.device.input_keyevent(keycode.KEYCODE_BACK)
            tries += 1
        return False

    def navigateTo(self, nodeText):
        maxTries, tries = 5, 0

        while tries < maxTries:
            self.closePromoOverlay() # removed from watchers
            isMain = self.verifyMain()
            isHomeMenu = self.verifyHomeMenu()
            isLauncher = self.device.getElementByXPath(self.xpath.SPLASH_SCREEN_APP_VERSION) is not None
            isLinkajaActivity = self.device.getElementByXPath("//node[@package='{}']".format(self.PACKAGE)) is not None
            if isMain and not isHomeMenu:
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
            Delay.randomSleep(1)

            self.device.refreshRoot()

            if self.device.getElementByXPath(self.xpath.TOOLBAR_SUBTITLE) is not None:
                self.device.input_keyevent(keycode.KEYCODE_BACK)
                continue

            isRequestedMenu = self.checkMenuHeader(nodeText)
            if isRequestedMenu:
                logger.info('navigateTo:Try#{}:isRequestedMenu={}'.format(tries, isRequestedMenu))
                break

            if not isLinkajaActivity:
                self.device.wakeUp()
                self.device.setTopActivity(self.PACKAGE, self.LAUNCHER_ACTIVITY)

            if not isMain and not isLauncher and isLinkajaActivity:
                self.device.input_keyevent(keycode.KEYCODE_BACK)
            tries += 1

    def refreshDashboard(self, rootRefresh=False):
        self.device.waitForElementsByXPath(self.xpath.DASHBOARD_REFRESH_SCROLLABLE, timeout=5)
        scrollable = self.device.getElementByXPath(self.xpath.DASHBOARD_REFRESH_SCROLLABLE) or self.device.getElementByXPath(self.xpath.SCROLL_VIEW)
        if scrollable is not None:
            self.device.swipe(scrollable, fraction=4, direction='DOWN', duration=100)
        if rootRefresh:
            self.device.refreshRoot()

    def getBalance(self):
        balance_textview = self.device.getElementsByXPath(self.xpath.BALANCE_TEXTVIEW) # XPath of profile balance
        if len(balance_textview):
            return balance_textview[0].get('text')
    
    def checkSubstring(self, string: str, substrings: List[str], case_insensitive=False):
        if case_insensitive:
            substrings = [substring.lower() for substring in substrings]
            string = string.lower()

        logger.debug('checkSubstring: string={} substrings={} case_insensitive={}'.format(string, substrings, case_insensitive))
        for substring in substrings:
            if not string.__contains__(substring):
                return False
        return True

    def checkMenuHeader(self, nodeText, removeSymbols=True):
        if removeSymbols:
            nodeText = re.sub(r'[^\w]', ' ', nodeText)
        nodeTextSubstrings = nodeText.split(' ')

        menu_header_text = self.getToolbarText()
        if menu_header_text is not None:
            return self.checkSubstring(menu_header_text, nodeTextSubstrings)

    def switchTab(self, nodeText, noScrollableCheck=False):
        try:
            tries, maxTries = 0,3
            while tries < maxTries:
                if not noScrollableCheck:
                    self.device.waitForElementsByXPath(self.xpath.SCROLLABLE, timeout=5)
                tab_element = self.device.getElementByXPath(self.xpath.FORMATTABLE_NODE_TEXT_SELECTOR.format(nodeText))
                if tab_element is not None:
                    if tab_element.get('selected') == 'false':
                        self.device.tapByElement(tab_element)
                        logger.debug("switchTab: Switched to tab {}".format(nodeText))
                    else:
                        logger.debug("switchTab: Already on tab {}".format(nodeText))
                    return True
                tries += 1
        except Exception as exc:
            print("Unexpected error caught: {}".format(str(exc)))
            logger.exception(exc)

    def promoOverlayVisible(self):
        if self.device.getElementByXPath(self.xpath.PROMO_MESSAGE_OVERLAY) is not None:
            return True
        return False

    def closeMTPWarning(self, refreshRootAfterClosing=True):
        mtp_title = self.device.getElementByXPath("//node[@package='com.samsung.android.MtpApplication' and @resource-id='android:id/alertTitle' or @resource-id='android:en/alertTitle']")
        if mtp_title is not None:
            logger.debug("MTP warning is present, closing it.")
            close_button = self.device.getElementByXPath(self.xpath.FORMATTABLE_NODE_TEXT_SELECTOR.format('OK'))
            if close_button is not None:
                self.device.tapByElement(close_button)
            else:
                self.device.input_keyevent(keycode.KEYCODE_BACK)

            if refreshRootAfterClosing:
                logger.debug('Refreshed root.')
                self.device.refreshRoot()
            Delay.randomSleep(2)

    def closeNotResponding(self, refreshRootAfterClosing=True):
        close_button = self.device.getElementByXPath("//node[@package='android' and @resource-id='android:id/aerr_close']")
        if close_button is not None:
            logger.debug('An application is not responding, closing it.')
            self.device.tapByElement(close_button)
            if refreshRootAfterClosing:
                logger.debug('Setting top activity to linkaja and refreshed root.')
                self.device.setTopActivity(self.PACKAGE, self.LAUNCHER_ACTIVITY)
                self.device.refreshRoot()

    def closePromoOverlay(self, refreshRootAfterClosing=True):
        if self.promoOverlayVisible():
            logger.debug('Promo overlay is visible, closing it.')
            self.device.input_keyevent(keycode.KEYCODE_BACK)
            if refreshRootAfterClosing:
                logger.debug('Refrehsed root.')
                self.device.refreshRoot()

    def parse_input_coordinates(self, backspace=False, enter=False):
        elements = {}
        number_elements = self.root.xpath("node//node[@text!='']")
        if backspace:
            elements['backspace'] = self.root.xpath(self.xpath.BACKSPACE_KEY)[0]
        if enter:
            elements['enter'] = self.root.xpath(self.xpath.ENTER_KEY)[0]

        for el in number_elements:
            elements[el.get('text', 'INVALID_TEXT')] = el
        number_coordinates_pair = {name: Element.get_bounds(el) for name, el in elements.items()}
        return number_coordinates_pair

    def parseProductsFromXML(self, XML: etree.ElementBase):
        product_elements = XML.xpath(self.xpath.PRODUCT)
        products = []
        for element in product_elements:
            item_text_elements = Element.getElementsByXPath(element, "node" + self.xpath.TEXT_VIEW)
            if len(item_text_elements) >= 2:
                # Minimal length should be 2, required are the name and price of the product.
                product = {text_el.get('resource-id'): text_el.get('text') for text_el in item_text_elements}
                try:
                    item_name = product.get('com.telkom.mwallet:id/view_denom_generic_title_textview', product['com.telkom.mwallet:id/label_denom_pulsa_data_title'])
                    item_price = product.get('com.telkom.mwallet:id/view_denom_generic_price_textview', product['com.telkom.mwallet:id/label_denom_pulsa_data_price'])
                    item_desc = product.get('com.telkom.mwallet:id/view_denom_generic_description_textview', product.get('com.telkom.mwallet:id/label_denom_pulsa_data_description',None)) # expired is optional

                    product = {'name': item_name, 'description': item_desc, 'price': item_price,
                                'bounds': element.get('bounds'), 'coordinates': Element.get_bounds(element)}
                    products.append(product)
                except KeyError:
                    pass
        logger.info("productsFromXML: parsed {} product(s)".format(len(products)))
        return products

    @classmethod
    def parseRefID(cls, refIDText):
        if len(refIDText) > 0:
            return refIDText

    @classmethod
    def parseTimeInfo(cls, timeInfo):
        fmts = ['%d %b %Y, %H:%M WIT', '%d %b %Y, %H:%M:%S WIT']
        for fmt in fmts:
            try:
                datetime_obj = datetime.strptime(timeInfo, fmt)
                return datetime_obj
            except:
                continue

    def inputNumber(self, number: str):
        self.closePromoOverlay() # No longer as watcher

        number = Number.parser(number)

        input_box = self.device.getElementByXPath(self.xpath.NUMBER_INPUT_BOX)
        if input_box is None:
            if self.getToolbarSubtitle() is not None:
                self.device.input_keyevent(keycode.KEYCODE_BACK)
            Delay.randomSleep(1, 0.1)
            self.device.refreshRoot()
            input_box = self.device.getElementByXPath(self.xpath.NUMBER_INPUT_BOX)

        if input_box is None:
            raise RuntimeError('Input box is not found.')

        clear_button = self.device.getElementByXPath(self.xpath.NUMBER_INPUT_CLEAR)
        if clear_button is not None:
            self.device.tapByElement(clear_button)
            Delay.randomSleep(1)
        self.device.tapByElement(input_box)
        self.closePromoOverlay() # No longer as watcher
        Delay.randomSleep(1)
        logger.debug("inputNumber: Tapped input box and slept randomly.")

        self.device.input_text(number)
        next_button = self.device.getElementByXPath(self.xpath.NEXT_BUTTON)
        Delay.randomSleep(1)
        if next_button is not None:
            self.device.tapByElement(next_button)

        logger.info("inputNumber: Done input number={} and submitted".format(number))
    
    def productMatcher(self, products, product_spec: Union[List[dict], dict], matcher):
        if isinstance(product_spec, list):
            accumulated = [self.productMatcher(products, spec, matcher) for spec in product_spec]
            flattened_accumulated = [prod for prod_list in accumulated for prod in prod_list]
            return flattened_accumulated
        return matcher.match(products, product_spec)

    def getProduct(self, product_spec, reverse=False, matcher=MatchAll, fastest=False, parseProducts=False) -> Optional[Union[list, dict]]:
        parsedProducts = []
        input_product_spec = product_spec
        product_dict = self.PRODUCTS

        if parseProducts:
            val=__import__('secrets').token_hex(10)
            product_spec = Product([{'name':val}])
            logger.info("getProduct: parseProducts={}".format(parseProducts))
            logger.info("getProduct: Setting product_spec to an impossible value of {} for field name by using secrets.token_hex".format(val))
        else:
            product_spec = product_dict.get(product_spec, Product([{'name':input_product_spec}]))
        logger.info("getProduct: Searching With product_spec={} from input_product_spec={}, reverse={}, and matcher={}".format(product_spec, input_product_spec, reverse, matcher))

        self.device.waitForElementsByXPath(self.xpath.PRODUCTS_SCROLLABLE)
        scrollable_element = self.device.getElementByXPath(self.xpath.PRODUCTS_SCROLLABLE)
        if scrollable_element is None:
            self.device.wakeUp()
            self.device.waitForElementsByXPath(self.xpath.PRODUCTS_SCROLLABLE, timeout=10)
            scrollable_element = self.device.getElementByXPath(self.xpath.PRODUCTS_SCROLLABLE)
        
        if scrollable_element is None:
            raise RuntimeError("Product Scrollable is not found.")

        swipe_direction = 'UP'
        reverse_swipe_direction = 'DOWN'

        if product_spec.location_near_bottom:
            reverse = not reverse
            logger.debug(f"getProduct: swiped scrollable to bottom")
        else: # Else Swipe to the top
            # a kinda fix for ProductCodeCloserToBottom just returns match not found.
            self.root = etree.XML("<node></node>") #type:ignore
            logger.debug(f"getProduct: swiped scrollable to top")

        if reverse:
            swipe_direction, reverse_swipe_direction = reverse_swipe_direction, swipe_direction

        if (not fastest and not reverse) or reverse:
            self.device.multiSwipe(scrollable_element, direction=reverse_swipe_direction, fraction=3, durationEach=60, delayBetweenSwipes=0.04, swipeCount=5)
            Delay.randomSleep(0.5, 0.05)
            self.device.multiSwipe(scrollable_element, direction=reverse_swipe_direction, fraction=2, durationEach=60, delayBetweenSwipes=0.04, swipeCount=5)

        parse_product = self.parseProductsFromXML

        iter_count = 1
        while iter_count <= 30:
            logger.info("getProduct: Iter#{} of collecting UI XML".format(iter_count))
            self.device.refreshRoot()
            scrollable_element = self.device.getElementByXPath(self.xpath.PRODUCTS_SCROLLABLE)
            if scrollable_element is not None:
                if etree.tostring(self.root) == etree.tostring(self.device.lastRoot):
                    logger.debug("getProduct: No products matched.")
                    if parseProducts:
                        return parsedProducts
                    return None

                products = parse_product(self.root)
                if len(products) <= 0:
                    self.device.waitForElementsByXPath(self.xpath.PRODUCT, timeout=5)
                products = parse_product(self.root)
                if parseProducts:
                    parsedProducts.extend(products)
                
                if len(products) <= 0:
                    if len(self.device.getElementsByXPath(self.xpath.CONFIRM_BUTTON)) > 0:
                        logger.debug("getProduct: View doesn't seem to be correct. Trying to go back to product listing.")
                        self.device.input_keyevent(keycode.KEYCODE_BACK)
                        Delay.randomSleep(0.75, 0.05)
                        self.device.refreshRoot()

                        # Reswiple to deserved position if on the new version which puts you back on the top of the recycler view.
                        logger.debug("getProduct: Updating position on the product listing.")
                        scrollable_element = self.device.getElementByXPath(self.xpath.PRODUCTS_SCROLLABLE)
                        if scrollable_element is None:
                            self.device.wakeUp()
                            self.device.waitForElementsByXPath(self.xpath.PRODUCTS_SCROLLABLE, timeout=10)
                            scrollable_element = self.device.getElementByXPath(self.xpath.PRODUCTS_SCROLLABLE)
                        if scrollable_element is None:
                            raise RuntimeError("Product Scrollable is not found.")
                        self.device.multiSwipe(scrollable_element, direction=reverse_swipe_direction, fraction=3, durationEach=60, delayBetweenSwipes=0.03, swipeCount=5)
                        Delay.randomSleep(0.5, 0.05)
                        self.device.multiSwipe(scrollable_element, direction=reverse_swipe_direction, fraction=2, durationEach=60, delayBetweenSwipes=0.03, swipeCount=5)
                        Delay.randomSleep(0.75, 0.05)
                        continue

                logger.debug("getProduct: parsed products: {}".format(products))
                matched_products = self.productMatcher(products, product_spec.matchers, matcher)
                if matched_products:
                    logger.info("getProduct: Matched Product: {}".format(matched_products[0]))
                    return matched_products[0]

                self.device.swipe(scrollable_element, fraction=3, duration=225, direction=swipe_direction, rootRefresh=False)
                Delay.randomSleep(0.85, 0.05)

                logger.debug("getProduct: swiped scrollable to the next batch of products & sleep for .5s")
            iter_count += 1
        logger.debug("getProduct: Iteration count limiter triggered! Iteration Limit={}".format(iter_count-1))
        if parseProducts:
            return parsedProducts
        return None

    def loadConfirmationPage(self, waitForNumber=False):
        try:
            if self.device.u2_installed:
                self.device.waitForElementsByXPath(self.xpath.CONFIRMATION_NUMBER_DETAIL, timeout=7.5)
            else:
                self.device.waitForElementsByXPath(self.xpath.CONFIRMATION_NUMBER_DETAIL, timeout=10)
        except TimeoutError:
            pass

        elements = {}

        # Read https://stackoverflow.com/questions/17040254/how-to-select-a-node-using-xpath-if-sibling-node-has-a-specific-value
        # For following-sibling notation

        # Parsing the number element
        number_element_container=self.device.getElementByXPath(self.xpath.CONFIRMATION_NUMBER_DETAIL)
        if number_element_container is not None:
            number_element = Element.getElementByXPath(number_element_container, self.xpath.CONFIRMATION_NUMBER_DETAIL)
            if number_element is not None:
                elements['number'] = number_element

        # Parsing details
        details = self.device.getElementsByXPath(self.xpath.BILL_DETAILS)
        if details is not None:
            elements['details'] = details

        # Parsing Confirm Button
        confirm_button = self.device.getElementByXPath(self.xpath.CONFIRM_BUTTON)
        if confirm_button is not None:
            elements['confirm_button'] = confirm_button

        if waitForNumber:
            if elements.get('number') is None:
                return self.loadConfirmationPage(waitForNumber=waitForNumber)

        logger.info("loadConfirmationPage: parsed elements={}".format(elements))
        return elements

    def serverIsBusy(self, check_toolbar=True, check_bottom_error_message=True):
        self.device.refreshRoot()
        logger.debug("check_server_busy_error: Fetched root. check_toolbar={} check_bottom_error_message={}".format(check_toolbar, check_bottom_error_message))

        bottom_err_msg, toolbar_text, tb_sub='','',''
        res = [0,0] # Switch to mark the checks results. 0 means its all okay, while 1 means there's an error.

        if check_bottom_error_message:
            bottom_err_msg = self.device.getElementByXPath(self.xpath.BOTTOM_ERROR_MESSAGE)
            if bottom_err_msg is not None:
                res[0] = 1

        if check_toolbar:
            toolbar_text = self.getToolbarText()
            if toolbar_text is not None:
                tb_sub = self.getToolbarSubtitle()
                if tb_sub is not None:
                    res[1] = 1
        if res[0]:
            logger.info("check_server_busy_error: Server busy (bottom_err_msg={})".format(bottom_err_msg))
        if res[1]:
            logger.info("check_server_busy_error: Server busy (Toolbar_check: toolbar_text={} toolbar_sub={})".format(toolbar_text, tb_sub))
        return False if max(res) == 0 else True # not busy if nothing is detected.

    def serverIsNotBusy(self, *args, **kwargs):
        return not self.serverIsBusy(*args, **kwargs)

    def enterPin(self, pin: str):
        Delay.randomSleep(0.75, 0.025)
        self.device.refreshRoot()

        if self.device.u2_installed:
            self.device.waitForElementsByXPath(self.xpath.BACKSPACE_KEY, timeout=5)

        input_coordinates = self.parse_input_coordinates(self.root)
        logger.debug("enterPin: refreshed root and parsed input coordinates.")

        coords = []

        for digit in str(pin):
            digit_coordinates = input_coordinates[str(digit)]
            coords.append(Bounds.get_center(digit_coordinates)) # type: ignore
        self.device.multiTap(coords)

        logger.info("enterPin: Done input pin")

    def waitUntilTransactionFinish(self, timeout=60, raiseTimeoutError=True):
        def contains_any(_s, substrings=[]):
            for substr in substrings:
                if _s.__contains__(substr):
                    return True
            return False
        start = time.time()
        try:
            self.device.waitForElementsNotExistsByXPath(self.xpath.BLOCKING_ILLUST_VIDEOVIEW, timeout=timeout)
            logger.info("waitUntilTransactionFinish: Transaction Finished in {} s".format(round(time.time()-start, 3)))
        except TimeoutError as exc:
            exception = sys.exc_info()
            isLinkajaActivity = self.device.getElementByXPath("//node[@package='{}']".format(self.PACKAGE)) is not None
            if isLinkajaActivity:
                xml_str = etree.tostring(self.root).lower()
                if isinstance(xml_str, bytes):
                    logger.debug('Decoded xml_str from <bytes> to <str>')
                    xml_str = xml_str.decode('utf-8')
                if contains_any(xml_str, ['gagal','fail']):
                    logger.info("waitUntilTransactionFinish: TimeoutError: {}. With Transaction Status=Failed.".format(exception[1].args[0])) #type:ignore
                    return
            logger.exception(exc)
            logger.info("waitUntilTransactionFinish: TimeoutError: {}".format(exception[1].args[0])) #type:ignore
            if raiseTimeoutError:
                raise

    def loadResultPage(self):
        result = {}

        logger.debug("parse_result_page: XML UI collected.")

        def translate_verbal_month(dtString):
            table = {'peb':'feb', 'agt':'aug', 'okt':'oct', 'nop':'nov', 'des':'dec'}
            for old, new in table.items():
                dtString = dtString.replace(old, new)
            return dtString

        try:
            self.device.waitForElementsByXPath(self.xpath.TRANSACTION_RECEIPT, timeout=10)
        except TimeoutError:
            xml_str = etree.tostring(self.root)
            logger.debug("Fetching xml_str of view.")
            if isinstance(xml_str, bytes):
                logger.debug('Decoded xml_str from <bytes> to <str>')
                xml_str = xml_str.decode('utf-8')
            if xml_str.__contains__("Gagal"):
                logger.debug("xml_str contains 'Gagal'. Transaction has failed.")
                raise ReceiptNotFoundError("Transaction failed and receipt not found")
        receipt_element = self.device.getElementByXPath(self.xpath.SCROLL_VIEW)
        if receipt_element is None:
            self.device.getElementByXPath(self.xpath.SCROLLABLE)
        transaction_done = None

        if receipt_element is None:
            transaction_done = self.device.getElementByXPath(self.xpath.TRANSACTION_DONE_LABEL)
            if transaction_done:
                receipt_element = self.device.getElementByXPath(self.xpath.SCROLLABLE)
        
        if receipt_element is None:
            result.update({'refID': '?', 'time': datetime.now()})
            return result

        if receipt_element is not None or transaction_done is not None: # Element exclusive for success result
            self.device.wakeUp()
            result.update({'refID': '?', 'time': datetime.now()})
            self.device.swipe(receipt_element, direction='UP', duration=150)
            Delay.randomSleep(.3, .1)
            self.device.multiSwipe(receipt_element, fraction=6, direction='UP', durationEach=75, swipeCount=4, rootRefresh=False)
            Delay.randomSleep(.5, 0.1)
            logger.debug("loadResultPage: Swiped to transaction notes and sleep for .8s")

            tries, maxTries = 0, 3
            while tries < maxTries:
                self.device.refreshRoot()

                refID_el = self.device.getElementByXPath(self.xpath.TRANSACTION_REFERENCE_TEXTVIEW)

                if refID_el is not None:
                    result['refID'] = self.parseRefID(refID_el.get('text'))

                timeInfo_el = self.device.getElementByXPath(self.xpath.TRANSACTION_DATE_TEXTVIEW)

                if timeInfo_el  is not None:
                    result['time'] = self.parseTimeInfo(translate_verbal_month(timeInfo_el.get('text').lower()))

                if refID_el is not None:
                    break
                tries += 1

            logger.debug("loadResultPage: parsed result={}".format(result))
            return result
        raise ReceiptNotFoundError("Transaction receipt is not found")

    def activateWatchers(self):
        self.device.refreshWatchers=[self.closeMTPWarning, self.closeNotResponding]
    
    def deactivateWatchers(self):
        self.device.refreshWatchers=[]

    @before(activateWatchers, isMethod=True)
    @after(deactivateWatchers, isMethod=True)
    def processRequest(self, request: Request, recursion=0):
        # Default result
        result = Result.from_request(request)
        result.update(refID=None, time=datetime.now())
        number=request.number
        product_spec=request.product_spec
        
        if recursion != 0:
            logger.debug("processRequest: Called with recursion level {}".format(recursion))
        if recursion >= self.MAX_RECURSION:
            result.error=self.t('max_recursion_error')
            return result

        self.device.processing_request = True
        self.device.wakeUp()
        if recursion:
            self.device.stopApp(self.PACKAGE)
            Delay.randomSleep(2)
            self.device.setTopActivity(self.PACKAGE, self.LAUNCHER_ACTIVITY, force=True)
        else:
            self.device.setTopActivity(self.PACKAGE, self.LAUNCHER_ACTIVITY)

        Delay.randomSleep(2)

        try:
            self.navigateTo('Pulsa/Data')
            if self.getToolbarSubtitle() is not None and not len(self.device.getElementsByXPath(self.xpath.PRODUCTS_SCROLLABLE)):
                self.device.input_keyevent(keycode.KEYCODE_BACK)
            self.inputNumber(number=number)
        except Exception as exc:
            logger.exception(exc)
            self.device.setTopActivity(self.PACKAGE, self.LAUNCHER_ACTIVITY, force=True)
            return self.processRequest(request, recursion=recursion+1)

        try:
            self.device.waitForElementsByXPath(self.xpath.PRODUCT, timeout=15)
            if self.device.u2_installed:
                Delay.randomSleep(1.75)
            else:
                Delay.randomSleep(1)
        except TimeoutError:
            return self.processRequest(request, recursion=recursion+1)

        try:
            retry(self.switchTab, args=('Data',))
        except Exception as exc:
            print("Unexpected error caught: {}".format(str(exc)))
            logger.exception(exc)

        
        try:
            self.device.waitForElementsNotExistsByXPath(self.xpath.PRODUCT_LOADING, timeout=15)
        except TimeoutError:
            retry(self.switchTab, args=('Pulsa',), kwargs={'noScrollableCheck': True})
            retry(self.switchTab, args=('Paket Data',), kwargs={'noScrollableCheck': True})
            Delay.randomSleep(1)

        if not len(self.device.getElementsByXPath(self.xpath.SCROLLABLE)):
            retry(self.switchTab, args=('Pulsa',), kwargs={'noScrollableCheck': True})
            retry(self.switchTab, args=('Paket Data',))
            # reswitch if it shows nothing.

        product = self.getProduct(product_spec=product_spec, matcher=MatchAll, fastest=True if recursion==0 else False)


        if product is None:
            if not len(self.device.getElementsByXPath(self.xpath.PRODUCT)):
                return self.processRequest(request, recursion=recursion+1)

            # retry getting product once more with reverse direction.
            try:
                retry(self.switchTab, args=('Pulsa',), kwargs={'noScrollableCheck': True})
                retry(self.switchTab, args=('Paket Data',))
                Delay.randomSleep(1)
                product = self.getProduct(product_spec=product_spec, reverse=True, matcher=MatchAll)
            except MaxTriesReachedError as exc:
                logger.debug("processRequest: MaxTriesReachedError triggered when retrying getProduct.")
            if product is None:
                logger.info("processRequest: Product {} is not found".format(product_spec))
                result.error=self.t('product_not_found')
                return result

        assert(isinstance(product, dict)) # make typechecking happy
        # returned to the top of the products list.
        self.device.tapByElement(product)
        if self.serverIsBusy(check_toolbar=False):
            if self.device.u2_installed:
                self.device.tapByElement(product)
                if self.serverIsBusy(check_toolbar=False):
                    logger.info("processRequest: Server Busy Error")
                    result.error=self.t('server_busy_error')
                    return result
            else:
                logger.info("processRequest: Server Busy Error")
                result.error=self.t('server_busy_error')
                return result

        Delay.randomSleep(0.45, 0.05)


        confirmPageElements = self.loadConfirmationPage()

        if not len(confirmPageElements) > 1:
            confirmPageElements = self.loadConfirmationPage()
            if not len(confirmPageElements) > 1:
                logger.info("processRequest: Server Busy Error")
                result.error=self.t('server_busy_error')
                return result

        if len(confirmPageElements) > 1:
            logger.debug('Confirming product before payment...')
            product = self.PRODUCTS.get(product_spec, Product([{'name':product_spec}])).matchers[0]
            # Confirm its the same product
            xml_str = etree.tostring(self.root)
            if isinstance(xml_str, bytes):
                logger.debug('Decoded xml_str from <bytes> to <str>')
                xml_str = xml_str.decode('utf-8')


            correct_price = xml_str.__contains__(product.get('price')) or xml_str.__contains__(product.get('price').replace(' ', '').strip()) #type:ignore
            correct_num = xml_str.__contains__(Number.parser(number))
            correct_data = correct_price and correct_num

            logger.debug('Confirmation Page: Price={} ({}) Num={} ({})'.format(
                product.get('price'), ('Matched' if correct_price else 'Not Matched'),
                Number.parser(number), ('Matched' if correct_num else 'Not Matched')))

            if not (correct_data):
                logger.warning('Please leave the device on its own.')
                logger.info('Price or number is wrong. Retrying.')
                return self.processRequest(request, recursion=recursion+1)

            # Tap the confirm button
            try:
                self.device.tapByElement(confirmPageElements['confirm_button'])
            except KeyError:
                logger.info("processRequest: Server Busy Error\n")
                result.error=self.t('server_busy_error')
                return result
            except Exception as exc:
                print("Unexpected error caught: {}".format(str(exc)))
                logger.exception(exc)

            try:
                self.enterPin(self.app_pin)
            except TimeoutError:
                try:
                    self.enterPin(self.app_pin)
                except TimeoutError:
                    logger.info("processRequest: Balance is not sufficient\n")
                    result.update({'time':datetime.now(), 'description':self.t('balance_insufficient')})
                    return result
            
            self.device.processing_request = False # used for the server to decide whether to put the request back to the queue or not.

            try:
                if self.device.waitForElementsByXPath([self.xpath.BLOCKING_ILLUST_VIDEOVIEW,self.xpath.TRANSACTION_RECEIPT], timeout=15):
                    self.waitUntilTransactionFinish(timeout=45)

                if self.PACKAGE not in str(self.device.get_current_app()):
                    result.update({'refID':'?', 'time':datetime.now(), 'description':'App unexpectedly closed when waiting for transaction to finish. Status defaults to success with unknown refID.'})
                    return result

                # not refreshing root because in waitUntilTransactionFinish, it constantly refresh root till its on result page.
                try:
                    resPage = self.loadResultPage()
                except ReceiptNotFoundError:
                    try:
                        resPage = self.loadResultPage()
                    except:
                        raise
                result.update(resPage)
                #if result.get('time') is None and result.get('refID') is not None:
                if result.time is None:
                    result.time = datetime.now()
                logger.info("processRequest: Transaction for {number} and {product_spec} Finished Successfully.".format(number=number, product_spec=product_spec))
            except TimeoutError:
                # result.update({'refID':None,'description': 'Transaction Timed Out'}) # Defaults to fail
                result.update({'refID':'?','description': self.t('transaction_timed_out')}) # Defaults to Success
                logger.info("processRequest: Transaction for {number} and {product_spec} Timed Out.".format(number=number, product_spec=product_spec))
            except ReceiptNotFoundError:
                result.update({'description': self.t('receipt_not_found')})
                logger.info("processRequest: Transaction for {number} and {product_spec} Failed (Receipt is not found).".format(number=number, product_spec=product_spec))
            except RuntimeError as exc:
                result.update({'refID':'?','description': self.t('disconnected_to_device')}) # Defaults to Success
                logger.info("processRequest: Transaction for {number} and {product_spec} defaulted to success due to device being disconnected.".format(number=number, product_spec=product_spec))
            except Exception as exc:
                print("Unexpected error caught: {}".format(str(exc)))
                logger.exception(exc)
                result.update({'refID':'?', 'description':self.t('unexpected_exception')})
                logger.info("processRequest: Transaction for {number} and {product_spec} Failed with Unknown Exception.".format(number=number, product_spec=product_spec))

            self.device.input_keyevent(keycode.KEYCODE_BACK)

            try:
                if self.device.u2_installed:
                    self.device.waitForElementsByXPath(self.xpath.BALANCE_TEXTVIEW, timeout=10)
                Delay.randomSleep(1)
                self.device.refreshRoot()

                self.refreshDashboard()
                if self.device.u2_installed:
                    self.device.waitForElementsByXPath(self.xpath.BALANCE_TEXTVIEW, timeout=10)
                else:
                    Delay.randomSleep(1)
                    self.device.refreshRoot()
                balance = self.getBalance()
                result.update({'balance':balance}) if balance is not None else None
            except TimeoutError:
                pass
            except Exception as exc:
                print("Unexpected error caught: {}".format(str(exc)))
                logger.exception(exc)

            self.device.input_keyevent('KEYCODE_SLEEP')
            return result
