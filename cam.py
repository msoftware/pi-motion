#!/usr/bin/python 

import threading
import time
import datetime
import picamera
import sys
import traceback
import sun
import psutil
import subprocess
import os
import Queue
from datetime import date

class CamElement:

    def __init__(self, filename, type, chat_id):
        self.filename = filename
        self.type = type
        self.chat_id = chat_id

class CamThread (threading.Thread):

    def __init__(self, threadID, name, config, logger, queue, botQueue):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.config = config
        self.logger = logger
        self.running = 1
        self.queue = queue
        self.botQueue = botQueue
        self.queueTimeout = 300 # Run into emptty queue exception every x sec.
        self.initConfig()
        self.logger.info('Init ' + self.name)

    def initConfig(self):
        self.resolution        = self.config.get("CAMERA", "resolution")
        self.width,self.height = self.resolution.split("x")
        self.width             = int(self.width)
        self.height            = int(self.height)
        self.dir               = self.config.get("CAMERA", "dir")  
        self.exposure          = self.config.get("CAMERA", "exposure")
        self.rotation          = int(self.config.get("CAMERA", "rotation"))
        self.videoduration     = int(self.config.get("CAMERA", "videoduration"))
        self.framerate         = int(self.config.get("CAMERA", "videoframerate"))
        self.enabled           = self.config.get("CAMERA", "enabled")
        self.notificationMode  = self.config.get("CAMERA", "notification_mode")
        self.brightness        = int(self.config.get("CAMERA", "brightness"))
        self.contrast          = int(self.config.get("CAMERA", "contrast"))
        self.imageeffect       = self.config.get("CAMERA", "image_effect")
        self.awbmode           = self.config.get("CAMERA", "awb_mode")
        self.exposuremode      = self.config.get("CAMERA", "exposure")
        self.latitude         = float(self.config.get("HUE", "latitude"))
        self.longitude        = float(self.config.get("HUE", "longitude"))

    def waitForHue(self, seconds):
        try:
            waitForHue = 1
            now = date.today()
            sunrise, sunset = sun.getSunsetSunrise( now, self.longitude, self.latitude )
            if sunrise < datetime.datetime.now():
                waitForHue = 0
            if sunset < datetime.datetime.now():
                waitForHue = 1
            if waitForHue == 1:
                time.sleep (seconds) 
        except:
            print "Exception in user code:"
            print '-'*60
            traceback.print_exc(file=sys.stdout)
            print '-'*60

    def run(self):
        self.logger.info('Start ' + self.name)
        camera = picamera.PiCamera()
        self.logger.info("Camera server running")
        while self.running == 1:
            try:
                camera.resolution = (self.width, self.height)
                camera.exposure_mode = self.exposure
                camera.rotation = self.rotation
                camera.framerate = self.framerate
                camera.brightness = self.brightness
                camera.contrast = self.contrast
                camera.image_effect = self.imageeffect
                camera.awb_mode = self.awbmode
                camera.exposure_mode = self.exposuremode
                start = time.time()
                self.logger.info(self.name + " running " + str(start))
                self.logger.info("CPU: " + str(psutil.cpu_percent()))
                self.logger.info("Memory: " + str(dict(psutil.virtual_memory()._asdict())))
                camElement = self.queue.get(True, self.queueTimeout)
                if camElement.type == "jpg":
                    if self.enabled == "on":
                        self.waitForHue(5)
                        self.logger.info("Take photo filename " + camElement.filename)
                        camera.capture(str(camElement.filename))
                        finish = time.time() - start
                        self.logger.info('Take photo done (' + str('{:04.2f}'.format(finish)) + 'sec.)!')
                        self.bot.camHandler(camElement.filename, camElement.chat_id, camElement.type)
                    else:
                        self.bot.camHandler(camElement.filename, camElement.chat_id, "dis")
                elif camElement.type == "h264":
                    if self.enabled == "on":
                        self.waitForHue(2)
                        # Override camera resolution for video. Telegram will only work with 480x320
                        camera.resolution = (480, 320)
                        self.logger.info("Take video filename: " + camElement.filename + " duration: " + str(self.videoduration))
                        camera.start_recording(str(camElement.filename))
                        time.sleep(self.videoduration)
                        camera.stop_recording()
                        # Convert video with ffmpeg
                        outfile = camElement.filename.replace(".h264", ".mp4")
                        self.logger.info("Convert video outfile: " + outfile)
                        cmd = "ffmpeg -i " + camElement.filename + " -an -c:v copy -y " + outfile + " 2> /dev/null"
                        returnCode = int(subprocess.call(cmd, shell=True))
                        if returnCode == 0:
                            self.bot.camHandler(outfile, camElement.chat_id, camElement.type)
                            os.remove(camElement.filename)
                        else:
                            self.bot.camHandler(camElement.filename, camElement.chat_id, "err")
                        # Resore video resolution
                        camera.resolution = (self.width, self.height)
                    else:
                        self.bot.camHandler(camElement.filename, camElement.chat_id, "dis")
                else:
                    self.logger.info("Type: " + camElement.type)
                    
            except Queue.Empty:
                self.logger.info("Queue.Empty for " + str(self.queueTimeout) + " sec.")
                pass
            except:
                self.logger.info("Unexpected error:", sys.exc_info()[0])
        camera.close() # Gracefully close PiCam if client disconnects

    def addBot(self, bot):
        self.bot = bot

    def handleNotification(self, chat_id):
        self.logger.info(self.name + " handleNotification " + self.notificationMode)
        if self.notificationMode == "photo":
            self.takePhoto(chat_id)
        elif self.notificationMode == "video":
            self.takeVideo(chat_id)

    def takeVideo(self, chat_id):
        self.logger.info(self.name + " takeVideo " + str(chat_id))
        type = "h264"
        filename = self.getFilename(type)
        camElement = CamElement(filename, type, chat_id)
        self.queue.put (camElement,True)

    def takePhoto(self, chat_id):
        self.logger.info(self.name + " takePhoto " + str(chat_id))
        type = "jpg"
        filename = self.getFilename(type)
        camElement = CamElement(filename, type, chat_id)
        self.queue.put (camElement,True)

    # Type: jpg or h264
    def getFilename(self, type):
        datetimestr=str(datetime.datetime.now())
        datetimestr=datetimestr.replace(" ", "_")
        datetimestr=datetimestr.replace(":", ".")
        filename = self.dir + datetimestr + "." + type
        return filename

    def quit(self):
        self.running = 0
        self.logger.info(self.name + " quit cam")
        type = "quit"
        camElement = CamElement("", type, "")
        self.queue.put (camElement,True)
