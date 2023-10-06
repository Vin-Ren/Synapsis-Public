
import re
import time
from functools import lru_cache
from typing import Callable, Dict, List, Tuple, Union
from lxml import etree

from ppadb.device import Device as ppadbDevice
from adbutils import device as AdbUtilsDevice
import uiautomator2 as u2
import atexit

import logging
logging.getLogger('urllib3').setLevel(logging.INFO)
logging.getLogger('uiautomator2').setLevel(logging.INFO)

from automators.utils.helper import retry
from automators.utils.logger import Logging
from automators.utils.delay import Delay
from automators.ui.bounds import Bounds
from automators.ui.element import Element
from automators.utils.exception import UnauthorizedError

logger = Logging.get_logger(__name__)


class Device(ppadbDevice):
    MAX_TRIES = 5
    UI_PARSER = etree.XMLParser(encoding='UTF-8')
    
    CURRENT_FOCUS_REGEX = re.compile(r'mCurrentFocus=Window{.*\s+(?P<package>[^\s]+)/(?P<activity>[^\s]+)\}')

    def __init__(self, client, serial):
        super().__init__(client, serial)
        self.root: etree.ElementBase = etree.XML("<node></node>") #type:ignore
        self.lastRoot: etree.ElementBase = etree.XML("<node text='LastRoot'></node>") #type:ignore
        self.refreshWatchers: List[Callable] = [] # list of functions to be called after refreshRoot is called
        
        self.u2_device = u2.Device(serial)
        self.u2_installed = self.check_u2_installed()
        if self.u2_installed and not self.u2_device.uiautomator.running():
            self.u2_device.uiautomator.start()
        
        self.processing_request = False
        self.state=''
        
        atexit.register(self.stop_uiautomator2)
        
        try:
            _ = self.ppadb_shell("echo test_conn")
        except RuntimeError as exc:
            if len(exc.args):
                if exc.args[0].__contains__('unauthorized'):
                    raise UnauthorizedError('Connection to device {} is not authorized.'.format(serial))
        except Exception as exc:
            logger.exception(exc)
    
    def check_u2_installed(self):
        return self.get_u2_initer().check_install()
    
    def refresh_u2_installed(self):
        self.u2_installed = self.check_u2_installed()
        return self.u2_installed
    
    @lru_cache(maxsize=1)
    def get_u2_initer(self):
        device = AdbUtilsDevice(self.serial)
        return u2.Initer(device)
    
    def u2_install(self):
        logger.info("Installing uiautomator2 on device '{}'".format(self.serial))
        self.get_u2_initer().install()
        self.refresh_u2_installed()
    
    def u2_uninstall(self):
        logger.info("Uninstalling uiautomator2 on device '{}'".format(self.serial))
        self.get_u2_initer().uninstall()
        self.refresh_u2_installed()
    
    def u2_start(self):
        if self.u2_installed:
            self.u2_device.uiautomator.start()
    
    def u2_stop(self):
        if self.u2_installed:
            self.u2_device.uiautomator.stop()
    
    def input_keyevent(self, keyevent):
        keyevent = str(keyevent)
        if self.u2_installed:
            return self.u2_device.keyevent(keyevent)
        super().input_keyevent(keyevent)
    
    def ppadb_shell(self, *args, **kwargs):
        return super().shell(*args, **kwargs)
    
    def shell(self, _cmd, *args, **kwargs):
        if self.u2_installed:
            return self.u2_device.shell(_cmd).output
        return self.ppadb_shell(_cmd, *args, **kwargs) or ' '

    def get_current_app(self):
        RGX = self.CURRENT_FOCUS_REGEX
        
        match = RGX.search(self.shell('dumpsys window windows | grep Focus'))
        if match:
            return match.groupdict()
        
        # From: https://github.com/appium/appium/issues/13420
        match = RGX.search(self.shell("dumpsys window displays | grep -E 'mCurrentFocus|mFocusedApp'"))
        if match:
            return match.groupdict()
        
        # From: https://stackoverflow.com/questions/13193592/adb-android-getting-the-name-of-the-current-activity
        match = RGX.search(self.shell("dumpsys activity activities | grep -E 'mCurrentFocus|mFocusedApp'"))
        if match:
            return match.groupdict()
        return {}

    def stop_uiautomator2(self):
        if self.u2_installed:
            try:
                # to check whether it is still connected, checking uiautomator2 directly would cause some unwanted reconnecting
                if self.ppadb_shell("echo __c") == '__c':
                    if self.u2_device.uiautomator.running():
                        self.u2_device.uiautomator.stop()
            except RuntimeError:
                pass

    def wakeUp(self):
        """
        Override if your device has different wakeup procedure.
        This defaults to input key event(KEYCODE_WAKEUP) or simply just turning on the screen.
        if you have multiple devices connected with different wakeup procedure at the same time,
        consider implementing if device.serial conditions for each different procedure.

        Recommended: turn your lock screen type to None, for no override.
        """
        if self.u2_installed:
            return self.u2_device.screen_on()
        self.input_keyevent("KEYCODE_WAKEUP")

    def sleep(self):
        if self.u2_installed:
            return self.u2_device.screen_off()
        self.input_keyevent("KEYCODE_SLEEP")

    def get_info(self, detailed=False):
        data = {}
        data['serial'] = self.get_serial_no()
        data['current_app'] = self.get_current_app()
        data['battery_level'] = self.get_battery_level()
        data['u2_installed'] = self.u2_installed
        if self.u2_installed and detailed:
            data['u2_info'] = self.u2_device.device_info
        return data

    def startApp(self, packageName, activityName, category='api.android.intent.LAUNCHER', action='api.android.category.MAIN'):
        if self.u2_installed:
            return self.u2_device.app_start(packageName, activityName)

        args = ["am", "start"]
        if category is not None:
            args += ['-c', category]
        if action is not None:
            args += ['-a', action]
        args += ['-n', "{package}/{activity}".format(package=packageName, activity=activityName)]
        # print(' '.join(args))
        logger.debug('Starting package:{} activity:{}'.format(packageName, activityName))
        return self.shell(" ".join(args))

    def stopApp(self, packageName):
        if self.u2_installed:
            return self.u2_device.app_stop(packageName)

        args = ["am", "force-stop", packageName]
        logger.debug("stopping package:{}".format(packageName))
        return self.shell(" ".join(args))

    def setTopActivity(self, packageName, launcherActivity, force=False):
        if packageName != self.get_current_app().get('package', '') or force:
            logger.debug('Setting top activity as {}'.format(packageName))
            self.stopApp(packageName=packageName)
            self.startApp(packageName=packageName, activityName=launcherActivity)
            retry(self.refreshRoot, successValidator=lambda _:(Delay.randomSleep(1, 0.2), packageName == self.get_current_app().get('package', ''))[1])

    def getUI(self, compressed=False, return_str=False):
        args = ['uiautomator', 'dump']
        if compressed:
            args.append('--compressed')
        args.append('/dev/tty')

        tries = 0
        while tries < self.MAX_TRIES:
            try:
                if self.u2_installed:
                    resp = self.u2_device.dump_hierarchy()
                else:
                    resp = self.shell(' '.join(args))
                if resp == 'ERROR: null root node returned by UiTestAutomationBridge.\r\n':
                    self.wakeUp()
                    continue
                UIHierarchy = resp.strip('UI hierchary dumped to: /dev/tty\r\n')
                if return_str:
                    return UIHierarchy
                self.root = etree.fromstring(UIHierarchy.encode('utf-8'), parser=etree.XMLParser(encoding='UTF-8'))
                break
            except etree.XMLSyntaxError:
                pass
            except RuntimeError as exc:
                exc_args = '|'.join(exc.args)
                if exc_args.__contains__('is offline'):
                    pass
            tries += 1
        return self.root

    def refreshRoot(self):
        self.lastRoot = self.root
        self.getUI()
        if len(self.refreshWatchers) > 0:
            logger.debug("Calling all active watchers: {}".format(self.refreshWatchers))
            [watcher() for watcher in self.refreshWatchers]

    def getElementsByXPath(self, xpath):
        return Element.getElementsByXPath(self.root, xpath)

    def getElementByXPath(self, xpath, elementIndex=0):
        return Element.getElementByXPath(self.root, xpath, elementIndex=elementIndex)

    def getElementsByAttribute(self, attributes:dict):
        return Element.getElementsByAttribute(self.root, attributes=attributes)

    def getElementByAttribute(self, attributes:dict, elementIndex=0):
        return Element.getElementByAttribute(self.root, attributes=attributes, elementIndex=elementIndex)

    # Inputs
    def tap(self, coordinate: Tuple[int, int], rootRefresh=False):
        """Tap using input command."""
        logger.debug("tap: coordinate={}".format(coordinate))
        if self.u2_installed:
            self.u2_device.click(*coordinate)
        else:
            self.input_tap(*coordinate)

        if rootRefresh:
            self.refreshRoot()

    def multiTap(self, coordinates: List[Tuple[int, int]], eachTapDuration=0.05, delayBetweenTaps=0.025):
        logger.debug("multiTap: coordinates={} eachTapDuration={} delayBetweenTaps={}".format(coordinates, eachTapDuration, delayBetweenTaps))
        for coordinate in coordinates:
            self.tap(coordinate, rootRefresh=False)
    
    def tapByElement(self, element: Union[etree.ElementBase, Dict[str,str]], autoPosition=True, rootRefresh=False):
        logger.debug("tapByElement: element={} autoPosition={} rootRefresh={}".format(element, autoPosition, rootRefresh))
        if not 'coordinates' in element:
            bounds = Element.get_bounds(element)
            if autoPosition:
                coord = Bounds.get_center(bounds)
                return self.tap(coord, rootRefresh=rootRefresh)
            return self.tap(bounds[0], rootRefresh=rootRefresh)
        else:
            coord = Bounds.get_center(element['coordinates'])
            return self.tap(coord, rootRefresh=rootRefresh)

    def tapByXPath(self, xpath, autoPosition=True, rootRefresh=False):
        matches = self.getElementsByXPath(xpath)
        if len(matches):
            for match in matches:
                self.tapByElement(match, autoPosition=autoPosition, rootRefresh=rootRefresh)

    @classmethod
    def make_swipe_kwargs(cls, element: etree.ElementBase, fraction: int, direction: str, duration: int = 0):
        '''make kwargs for ppadb.device.Device.input_swipe to swipe across the element with the given fraction, direction, and duration.

        :param element: element to be swiped
        :param fraction: fraction-2/fraction part of the element. controls the area of the swiping.
        Example: fraction=4 and direction=DOWN then swipes from 1/4->3/4 of the element's y-axis.
        :type fraction: int
        :param direction: direction to swipe to. Valid directions=[UP,RIGHT,DOWN,LEFT]
        :type direction: str
        :param duration: duration of the swipe in milliseconds(ms)
        :type duration: int
        '''

        element_bounds = Element.get_bounds(element) # 2D array => ((x1,y1),(x2,y2))

        element_bounds = Bounds.shift(element_bounds, shift=-1)

        direction = direction.upper()
        if direction in ['UP', 'DOWN']:
            not_swiped_axes = [(0, 0), (1, 0)] # x1, x2 # 2D array coordinates
            swiped_axes = [(0, 1), (1, 1)] # y1, y2 # Will be switched at the end between start and end if direction UP/DOWN
            not_swiped_kwargs = ['start_x', 'end_x']
            swiped_kwargs = ['start_y', 'end_y']
        elif direction in ['RIGHT', 'LEFT']:
            not_swiped_axes = [(0, 1), (1, 1)] # y1, y2
            swiped_axes = [(0, 0), (1, 0)] # x1, x2
            not_swiped_kwargs = ['start_y', 'end_y']
            swiped_kwargs = ['start_x', 'end_x']
        else:
            raise ValueError(f"Direction should be in [UP, RIGHT, DOWN, LEFT], gets {direction}")

        bounds = {}
        bounds['not_swiped_start'] = element_bounds[not_swiped_axes[0][0]][not_swiped_axes[0][1]]
        bounds['not_swiped_end'] = element_bounds[not_swiped_axes[1][0]][not_swiped_axes[1][1]]
        bounds['swiped_start'] = element_bounds[swiped_axes[0][0]][swiped_axes[0][1]]
        bounds['swiped_end'] = element_bounds[swiped_axes[1][0]][swiped_axes[1][1]]

        new_bounds = {}
        new_bounds['not_swiped_start'] = bounds['not_swiped_start']+((bounds['not_swiped_end'] - bounds['not_swiped_start'])) # Just middle point
        new_bounds['swiped_start'] = bounds['swiped_start']+((bounds['swiped_end'] - bounds['swiped_start'])/fraction * (fraction-1)) # (fraction-1)/fraction point between axis bounds
        new_bounds['not_swiped_end'] = new_bounds['not_swiped_start'] # Just take same point as start
        new_bounds['swiped_end'] = bounds['swiped_start']+((bounds['swiped_end'] - bounds['swiped_start'])/fraction) # 1/fraction point between axis bounds

        # Now the new_bounds are compactible with either UP or LEFT
        # Time to reverse for DOWN and RIGHT
        if direction in ['DOWN', 'RIGHT']:
            new_bounds['swiped_start'], new_bounds['swiped_end'] = new_bounds['swiped_end'], new_bounds['swiped_start']

        # Returns actual kwargs key
        kwargs = {}
        kwargs[not_swiped_kwargs[0]] = new_bounds['not_swiped_start']
        kwargs[not_swiped_kwargs[1]] = new_bounds['not_swiped_end']
        kwargs[swiped_kwargs[0]] = new_bounds['swiped_start']
        kwargs[swiped_kwargs[1]] = new_bounds['swiped_end']

        if duration:
            kwargs['duration'] = duration

        return kwargs

    def swipe(self, element: etree.ElementBase, fraction: int = 4, direction: str = 'None', duration: int = 260, rootRefresh=False):
        '''swipes across the element with the given fraction, direction, and duration.

        :param element: element to be swiped
        :param fraction: fraction-2/fraction part of the element. controls the area of the swiping.
        Example: fraction=4 and direction=DOWN then swipes from 1/4->3/4 of the element's y-axis.
        :type fraction: int
        :param direction: direction to swipe to. Valid directions=[UP,RIGHT,DOWN,LEFT]
        :type direction: str
        :param duration: duration of the swipe in milliseconds(ms)
        :type duration: int
        :param rootRefresh: whether to refresh root or not.
        :type rootRefresh: bool
        '''

        logger.debug("swipe: swiped with element={} fraction={} direction={} duration={} rootRefresh={}".format(element, fraction, direction, duration, rootRefresh))

        kwargs = self.make_swipe_kwargs(element, fraction=fraction, direction=direction, duration=duration)

        # if self.u2_installed:
        # 	conv = lambda kw, pair:{k if k not in pair.keys() else pair.get(k):v for k,v in kw.items()}
        # 	kwargs = conv(kwargs, {'start_x':'fx', 'start_y':'fy', 'end_x':'tx', 'end_y':'ty'})
        # 	print(kwargs)
        # 	args = 
        # 	kwargs['duration'] = kwargs.pop('duration')/1000
        # 	self.u2_device.swipe(**kwargs)
        # else:
        # 	self.input_swipe(**kwargs)
        self.input_swipe(**kwargs)

        if self.u2_installed:
            Delay.randomSleep(0.5, 0.05)

        if rootRefresh:
            self.refreshRoot()

    def multiSwipe(self, element: etree.ElementBase, fraction=4, direction='UP', durationEach=75, swipeCount=1, delayBetweenSwipes=0.05, rootRefresh=False):
        logger.debug("multiSwipe: swiped with element={} fraction={} direction={} durationEach={} rootRefresh={}".format(element, fraction, direction, durationEach, rootRefresh))
        for i in range(swipeCount):
            self.swipe(element, direction=direction, duration=durationEach, rootRefresh=False)
            Delay.randomSleep(delayBetweenSwipes, 0.005)
        if rootRefresh:
            self.refreshRoot()

    # Waiters
    def waitForElementsByXPath(self, elementsXPath: Union[str, List[str], Tuple[str]], minimumElementCount: int = 1, timeout: Union[int, float] = 60, intervals: float = 0, raiseErr: bool = True):

        if isinstance(elementsXPath, str):
            xpath_list = [elementsXPath]
        elif isinstance(elementsXPath, (tuple, list)):
            xpath_list = list(elementsXPath)

        wait_time_start = time.time()

        logger.debug('waitForElementsExistsByXPath: elementsXPath={} minimumElementCount={} timeout={}'.format(elementsXPath, minimumElementCount, timeout))
        while True:
            if timeout>=0:
                if (time.time() - wait_time_start) >= timeout:
                    if raiseErr:
                        raise TimeoutError("Not enough element is found in the given {}s timeout.".format(timeout))
                    else:
                        return False
            self.refreshRoot()
            time.sleep(intervals)
            element_list = []
            [element_list.extend(self.getElementsByXPath(xpath)) for xpath in xpath_list]
            if len(element_list) >= minimumElementCount:
                logger.debug("waitForElementsExistsByXPath: Condition is satisfied.")
                return True
            if timeout>=0:
                if (time.time() - wait_time_start) >= timeout:
                    logger.debug("waitForElementsExistsByXPath: Condition is not satisfied.")
                    if raiseErr:
                        raise TimeoutError("Not enough element is found in the given {}s timeout.".format(timeout))
                    else:
                        return False

    def waitForElementsNotExistsByXPath(self, elementsXPath: Union[str, List[str], Tuple[str]], maximumElementCount: int = 0, timeout: Union[int, float] = 60, intervals: float = 0, raiseErr: bool = True):

        if isinstance(elementsXPath, str):
            xpath_list = [elementsXPath]
        elif isinstance(elementsXPath, (tuple, list)):
            xpath_list = list(elementsXPath)

        wait_time_start = time.time()

        logger.debug('waitForElementsNotExistsByXPath: elementsXPath={} maximumElementCount={} timeout={}'.format(elementsXPath, maximumElementCount, timeout))
        while True:
            self.refreshRoot()
            time.sleep(intervals)
            element_list = []
            [element_list.extend(self.getElementsByXPath(xpath)) for xpath in xpath_list]
            if len(element_list) <= maximumElementCount:
                logger.debug("waitForElementsNotExistsByXPath: Condition is satisfied.")
                return True
            if timeout>=0:
                if (time.time() - wait_time_start) >= timeout:
                    logger.debug("waitForElementsNotExistsByXPath: Condition is not satisfied.")
                    if raiseErr:
                        raise TimeoutError("Too much element is left in the given {}s timeout.".format(timeout))
                    else:
                        return False
    
    def getClickableRegion(self, element, obstructive_element):
        """Gets clickable region of given element, unobstructed of given obstructive_element."""
        bounds = Element.get_bounds(element)
        obstructive_bounds = Element.get_bounds(obstructive_element)
        
        logger.debug("getClickableRegion: Getting clickable region of element={} with obstructive element={}".format(bounds, obstructive_bounds))
        
        top_left_blocked, bottom_right_blocked = False, False
        
        if obstructive_bounds[0][0] <= bounds[0][0] <= obstructive_bounds[1][0]: # x of top_left of element in between x of obstructive bounds
            if obstructive_bounds[0][1] <= bounds[0][1] <= obstructive_bounds[1][1]: # y of top_left of element in between y of obstructive bounds
                top_left_blocked = True
        
        if obstructive_bounds[0][0] <= bounds[1][0] <= obstructive_bounds[1][0]: # x of bottom_right of element in between x of obstructive bounds
            if obstructive_bounds[0][1] <= bounds[1][1] <= obstructive_bounds[1][1]: # y of bottom_right of element in between y of obstructive bounds
                bottom_right_blocked = True
        
        res = bounds
        
        if top_left_blocked and bottom_right_blocked:
            res = ((-1, -1),(-1, -1))
        elif top_left_blocked:
            res = (obstructive_bounds[1], bounds[1])
        elif bottom_right_blocked:
            res = (bounds[0], obstructive_bounds[0])
        
        logger.debug("getClickableRegion: top_left_blocked={} bottom_right_blocked={}. original={} cleared={}".format(top_left_blocked, bottom_right_blocked, bounds, res))
        return res
    
    def getUIString(self, compressed=False):
        if self.u2_installed:
            return self.u2_device.dump_hierarchy(compressed=compressed)
        try:
            return self.shell("uiautomator dump /dev/tty").strip('UI hierchary dumped to: /dev/tty\r\n')
        except:
            self.wakeUp()
            return self.shell("uiautomator dump /dev/tty").strip('UI hierchary dumped to: /dev/tty\r\n')

    def saveCurrentView(self, viewXML=False, screencap=False, xml_filename='recent.xml', screencap_filename='screenshot.png'):
        if viewXML:
            self.shell("uiautomator dump")
            self.pull("/sdcard/window_dump.xml", xml_filename)

        if screencap:
            result = self.screencap()
            with open(screencap_filename, "wb") as fp:
                fp.write(result)
