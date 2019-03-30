
import sys, time, datetime, threading
import RPi.GPIO as GPIO

class PirThread (threading.Thread):

    def __init__(self, threadID, name, config, logger, hue):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.hue = hue
        self.name = name
        self.config = config
        self.bot = None
        self.logger = logger
        self.running = 1
        self.minmeasrures = int(self.config['MOTION']['minduration']) * 2 # x2 because of 0.5 interval
        self.motionDetect = 0
        # Init GPIO
        self.gpio = int(self.config['MOTION']['gpio'])
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.gpio, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        time.sleep(3) # Give sensor time to startup

    def addBot(self, bot):
        self.bot = bot

    def run(self):
        self.logger.info('Start ' + self.name)
        measrures = 0
        lastPirValue = 0
        self.setMotionDetect(0) # Init 
        while self.running:
            try:
                pirValue = int(GPIO.input(self.gpio))
                measrures = measrures + pirValue
                if pirValue == False:
                    measrures = 0
                if measrures == 0:
                    if lastPirValue == 1:
                        self.setMotionDetect(0)
                        self.logger.info("Measure " + str(measrures))
                else:
                    self.logger.info("Measure " + str(measrures))
                if measrures >= self.minmeasrures:
                    self.setMotionDetect(1)
                lastPirValue = pirValue
            except:
                self.logger.error(str(sys.exc_info()))
            time.sleep(0.5)
        self.logger.info('Exit ' + self.name)

    def quit(self):
        self.running = 0

    def setMotionDetect(self,motionDetect):
        self.motionDetect = motionDetect
        self.logger.info("setMotionDetect " + str(motionDetect))
        if self.motionDetect == 1:
            if self.bot is None:
                self.logger.info("No bot avalable")
            else:
                self.bot.reportMotionDetection()
            if self.hue is None:
                self.logger.info("No hue lamp avalable")
            else:
                self.hue.lightOn()

