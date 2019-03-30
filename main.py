#!/usr/bin/python

import threading
import sys
import time
import logging
import logging.handlers
import configparser
import signal
import multiprocessing

from cam import CamThread
from pir import PirThread
from hue import HueClass
from hue import HueTimer
from bot import TelegramBot

logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
handler = logging.handlers.RotatingFileHandler('logs/motion.log', maxBytes=1024*1024, backupCount=5)
handler.setFormatter(logFormatter)
logger = logging.getLogger('Logger')
logger.setLevel(logging.INFO)
logger.addHandler(handler)
logger.info('Start main')

logger.info('Load config')
config = configparser.ConfigParser()
config.read('motion-sensor.ini')

pool = multiprocessing.Pool(processes=3)
m = multiprocessing.Manager()
camQueue = m.Queue()
botQueue = m.Queue()

logger.info('Init cam')
cam = CamThread(3, "Camera", config, logger, camQueue, botQueue)
cam.start()

logger.info('Init hue timer')
timer = HueTimer("Hue Timer", config, logger)
timer.start()

logger.info('Init hue')
hue = HueClass("Hue", timer, config, logger)
hue.lightOff()

timer.setHue(hue)

logger.info('Init motion sensor')
pirThread = PirThread(1, "PirThread", config, logger, hue)
pirThread.start()

logger.info('Init bot')
telegramBot = TelegramBot(1, "Bot", config, logger, hue, pirThread, cam, botQueue)
telegramBot.start()
cam.addBot(telegramBot)
pirThread.addBot(telegramBot)

logger.info('Init complete')

