import logging
from logging.handlers import RotatingFileHandler
import pickle
from datetime import datetime
from pathlib import Path
from collections import OrderedDict
from typing import List, Union

from automators.result import Result
from automators.utils.logger import Logging as linkajaLogging


TIME_INDICATOR_FORMAT = '%b_%Y'


def loggerHandler(filename='./logs.log', maxMB: float = 10, backupCount=5): # will be renamed to setupLogger
    logging.getLogger('urllib3').setLevel(logging.INFO)
    logging.getLogger('uiautomator2').setLevel(logging.INFO)
    linkajaLogging.enable()
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    handler = RotatingFileHandler(filename=filename, encoding='utf-8', mode='a', maxBytes=int(maxMB*(1024*1024)), backupCount=backupCount)
    FMT = logging.Formatter(fmt='[%(asctime)s,%(msecs)d %(levelname)s %(threadName)s:%(name)s:%(filename)s:%(lineno)d] %(message)s',
                            datefmt='%d-%m-%Y:%H:%M:%S')
    handler.setFormatter(FMT)
    logger.addHandler(handler)


def addPickle(result: Union[Result, List[Result]], filename: str = 'Hist.pick', monthlyHistory=True, monthlyHistoryFilenameFormat='{name}_{time_indicator}.{ext}'):
    '''
    Accepts a result object or a list of result objects and dumps it into given filename or monthlyHistory formatted filename(s).
    '''
    resultLists = {}
    name,ext = '.'.join(filename.split('.')[:-1]), filename.split('.')[-1]

    if result is None:
        return

    if isinstance(result, Result):
        results = [result]
    elif isinstance(result, list):
        isAllResults = all([isinstance(obj, Result) for obj in result])
        if not isAllResults:
            return print("Given list has element(s) other than Result object.")
        results = result
    else:
        return print("Given object of class <{}> is not valid.".format(result.__class__.__name__))

    if monthlyHistory:
        for result in results:
            time_indicator = result.time.strftime(TIME_INDICATOR_FORMAT)
            filename = monthlyHistoryFilenameFormat.format(name=name, ext=ext, time_indicator=time_indicator)
            resultLists[filename] = resultLists.get(filename, []) + [result]

        for filename, resultList in resultLists.items():
            data = []
            try:
                with open(filename, 'rb') as f:
                    data.extend(pickle.load(f))
            except (FileNotFoundError):
                print('Creating pickle file {}...'.format(filename))

            data.extend(resultList)

            with open(filename, 'wb') as f:
                pickle.dump(data, f)
    else:
        data = []
        try:
            with open(filename, 'rb') as f:
                data.extend(pickle.load(f))
        except (FileNotFoundError):
            print('Creating pickle file {}...'.format(filename))

        data.extend(results)

        with open(filename, 'wb') as f:
            pickle.dump(data, f)


def addPickles(*args, **kwargs):
    '''
    Extension for <addPickle> function for multiple results to avoid confusion.
    '''
    return addPickle(*args, **kwargs)


def dumpObject(obj, filename: str = 'dump.pick'):
    with open(filename, 'wb') as f:
        pickle.dump(obj, f)


def readPickle(filename: str = 'Hist.pick', getdata=False, monthlyHistory=True, FilenameSearcherFormatter='{name}_{time_indicator}.{ext}'):
    filesData = {}
    name,ext = '.'.join(filename.split('.')[:-1]), filename.split('.')[-1]
    FilenameSearcher = FilenameSearcherFormatter.format(name=name, ext=ext, time_indicator='*')
    if monthlyHistory:
        files = [name.__str__() for name in list(Path().glob(FilenameSearcher))]
    else:
        files = [filename]

    if len(files) <= 0:
        print('Pickle file not found.')
        return

    try:
        for filename in files:
            with open(filename, 'rb') as f:
                filesData[filename] = pickle.load(f)
    except FileNotFoundError:
        print('Pickle file not found.')
        return

    if monthlyHistory:
        filesData = OrderedDict({k:v for k,v in sorted(filesData.items(), key=lambda x: datetime.strptime(x[0], FilenameSearcherFormatter.format(name=name, ext=ext, time_indicator=TIME_INDICATOR_FORMAT)))})

    if getdata:
        return filesData

    for fileindex, (pfile, data) in enumerate(filesData.items()):
        head = "##{} File:{}".format(fileindex, pfile)
        transactions = '\n'.join(["Transaction#{}\n{}".format(i, res.detailed()) for i, res in enumerate(data)])
        footer = "\n\n\n"
        print('\n'.join([head,transactions,footer]))
