'''
Date: 2021-05-10 10:45:15
LastEditors: yuxuan.liu@uisee.com
LastEditTime: 2021-08-02 17:47:51
FilePath: /data/dptool/app/mod_loger/__init__.py
Description: 
'''
import logging
# Setup a log formatter
formatter = logging.Formatter(
    "%(asctime)12s - file: '%(filename)12s' - func: '%(funcName)15s' - [line:%(lineno)4d] - %(levelname).4s : %(message)s")
# Setup a log file handler and set level/formater
# logFile = logging.FileHandler("./log/runtime.log")
# logFile.setFormatter(formatter)


# Setup a log console handler and set level/formater
logConsole = logging.StreamHandler()
logConsole.setFormatter(formatter)
# Setup a logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# logger.addHandler(logFile)
logger.addHandler(logConsole)

"""
Logger example:
    logger.debug('DEBUG')
    logger.info('INFO')
    logger.warning('WARN')
    logger.error('ERRO')
    logger.critical('CRIT')
"""

class TaskLoger:
    def __init__(self, fileLocation,loginUser) -> None:
        self.formatter = logging.Formatter(
            "%(asctime)12s - file: '%(filename)12s' - func: '%(funcName)15s' - [line:%(lineno)4d] - "+"[user: %s]" % loginUser+ " - %(levelname).4s : %(message)s")
        self.logFile = logging.FileHandler(filename=fileLocation)
        self.logFile.setFormatter(self.formatter)

    def enableLogFile(self):
        logger.addHandler(self.logFile)

    def disableLogFile(self):
        logger.removeHandler(self.logFile)
