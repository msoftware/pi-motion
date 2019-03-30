import sun
import time
import threading
from datetime import date, datetime, timedelta
from multiprocessing import Process

from qhue import Bridge
# https://github.com/quentinsf/qhue

class HueClass:

    # Hue config 
    MOTION = 1
    ON     = 2
    OFF    = 3

    def __init__(self, name, timer, config, logger):
        self.name = name
        self.config = config
        self.logger = logger
        self.mode = HueClass.MOTION
        self.timer = timer
        self.lightState = False
        self.initConfig()
        self.b = Bridge(self.ip, self.user)
        self.logger.info('Init Hue OK')

    def initConfig(self):
        self.ip               = self.config.get("HUE", "bridge_ip")
        self.user             = self.config.get("HUE", "bridge_user")
        self.lights           = self.config.get("HUE", "lamps").split(',')
        self.followUpDuration = self.config.get("HUE", "followupduration")
        self.ignoreDaylight   = self.config.get("HUE", "ignore_daylight")
        self.latitude         = float(self.config.get("HUE", "latitude"))
        self.longitude        = float(self.config.get("HUE", "longitude"))
        self.logger.info("self.ignoreDaylight " + self.ignoreDaylight)

    def isHueEnabled(self):
        hueEnabled = 1
        now = date.today()
        sunrise, sunset = sun.getSunsetSunrise( now, self.longitude, self.latitude )
        if sunrise < datetime.now():
            self.logger.info("After sunrise " + str(sunrise))
            hueEnabled = 0
        if sunset < datetime.now():
            self.logger.info("After sunset " + str(sunset))
            hueEnabled = 1
        if self.ignoreDaylight == "on":
            self.logger.info("Ignore daylight is on ")
            hueEnabled = 1
        return hueEnabled

    def getLightState(self):
        return self.lightState

    def setHueLight(self, state):
        if (state == True and (self.mode == HueClass.MOTION or self.mode == HueClass.ON)) or (state == False and (self.mode == HueClass.MOTION or self.mode == HueClass.OFF)):
            self.lightState = state
            for light in self.lights:
                self.logger.info('Switch light ' + light + ' ' + str(state))
                self.b.lights(int(light), 'state', on=state)

    def lightOn(self):
        if self.isHueEnabled() == 1:
            self.logger.info('lightOn ' + str(HueClass.MOTION))
            if self.mode == HueClass.MOTION:
                self.logger.info('Switch lights on (MOTION)')
                self.setHueLight(True)
                lightOffTime = time.time() + (int(self.followUpDuration)*60)
                self.timer.setLightOffTime(lightOffTime)
            if self.mode == HueClass.ON:
                self.logger.info('Switch lights on (ON)')
                self.setHueLight(True)
        else:
            self.logger.info('Lights disabled (daylight outside)')

    def setMode(self, mode):
        self.logger.info('Hue set mode ' + str(mode))
        self.mode = mode
        if self.mode == HueClass.ON:
            self.timer.setLightOffTime(0) # Reset timer
            self.setHueLight(True)
        else:
            self.setHueLight(False)

    def lightOff(self):
        if self.mode == HueClass.MOTION:
             self.setHueLight(False)
             self.logger.info('Light Off done')

    def quit(self):
        self.timer.quit()

####################################################################################

class HueTimer (threading.Thread):

    def __init__(self, name, config, logger):
        threading.Thread.__init__(self)
        self.name = name
        self.config = config
        self.logger = logger
        self.running = 1
        self.lightOffTime = 0
        self.logger.info('Init Hue Timer OK')

    def setHue(self, hue):
        self.hue = hue

    def setLightOffTime(self, lightOffTime):
        self.logger.info('setLightOffTime ' + str(lightOffTime))
        self.lightOffTime = lightOffTime

    def run(self):
        while self.running:
            try:
                if self.lightOffTime > 0:
                    self.logger.info('Light off in ' + str(self.lightOffTime - time.time()) + ' sec.')
                    if self.lightOffTime < time.time():
                        self.lightOffTime = 0
                        self.hue.lightOff()
                time.sleep(1)
            except: 
                self.logger.error(str(sys.exc_info()))
        print "Exiting " + self.name

    def quit(self):
        self.running = 0

