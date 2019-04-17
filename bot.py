import traceback
import subprocess
import threading
import telegram
import time
import sys
import os

from datetime import date, datetime, timedelta
from collections import defaultdict
from hue import HueClass
from i18n.translator import Translator

exitFlag = 0

class TelegramBot (threading.Thread):

    # Process Constants
    START        = 1
    LOGIN        = 2
    LOGOUT       = 3
    CONFIG1      = 4 # Select section
    CONFIG2      = 5 # Seclect config
    CONFIG3      = 6 # Enter Value
    LIST         = 7
    NOTIFICATION = 8 # Enable or disable motion notifications
    LIGHT        = 9

    def __init__(self, threadID, name, config, logger, hue, pirThread, camThread, queue):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.starttime = time.strftime("%c")
        self.name = name
        self.login = {} # Dictionary
        self.logger = logger
        self.queue = queue
        self.token = config['TELEGRAM']['token']
        self.password = config['TELEGRAM']['password']
        self.minNotificationIntervall = int(config['TELEGRAM']['min_notification_interval'])
        self.path = os.path.dirname(os.path.realpath(__file__))
        self.tr = Translator(self.path, ['en_US', 'de_DE'], config['TELEGRAM']['language'])
        self.offset = 0
        self.timeout = 30
        self.network_delay=1.0
        self.config = config
        self.process = 0
        self.hue = hue
        self.pirThread = pirThread
        self.camThread = camThread
        self.running = 1
        self.chats = defaultdict(dict)
        self.bot = telegram.Bot(token=self.token)

    def reportMotionDetection(self):
        self.logger.info("Bot Detect motion")
        now = int(time.time())
        for chat_id,values in self.chats.iteritems():
            sendNotification = 0
            for valueskey,valuesvalue in values.iteritems():
                if (valueskey == "notification") and (valuesvalue == "yes"):
                    lastNotification = self.chats[chat_id]['send_notification']
                    durationSinceLastNotificaton = now - lastNotification
                    if durationSinceLastNotificaton > self.minNotificationIntervall:
                        sendNotification = 1
                    else:
                        self.logger.info("Motion detect notification disabled. Duration since last notification: " + str(durationSinceLastNotificaton))
            if sendNotification == 1:
                self.chats[chat_id]['send_notification'] = now
                self.bot.send_message(chat_id=chat_id, text=self.tr._("Motion detected."))
                self.logger.info("Send motion detect notification to " + str(chat_id))
                self.camThread.handleNotification(chat_id)

    def run(self):
        while self.running:
            try:
                updates = self.bot.get_updates( offset=self.offset)
                for update in updates:
                    now = date.today()
                    self.chats[update.message.chat_id]['lastupdate'] = now
                    self.chats[update.message.chat_id]['user'] = update.effective_user.first_name
                    self.bot.send_chat_action( chat_id=update.message.chat_id, 
                                               action=telegram.ChatAction.TYPING)
                    self.offset = update.update_id + 1 # Only fetch new updates
                    if update.message.text is None:
                        update.message.reply_text(self.tr._("Sorry, but I don't understand."))
                    else:
                        self.handleUpdate(update)
            except:
                self.logger.error(str(sys.exc_info()))
        print "Exiting " + self.name

###############################################################################
#                                                                             # 
#                  Follow up process handler definition                       # 
#                                                                             # 
###############################################################################

    def doProcessLogin(self, update):
        if update.message.text == self.password:
            update.message.reply_text(self.tr._("Login OK"))
            update.message.reply_text(self.tr._("If you need support just enter /help"))
            self.login[update.message.chat_id] = 1
            self.chats[update.message.chat_id]['login'] = "yes"
            self.chats[update.message.chat_id]['send_notification'] = 0
            self.process = 0
        else:
            update.message.reply_text(self.tr._("Invalid login. Please try again"))

    def doProcessLogout(self, update):
        yesno = update.message.text.lower()
        if yesno == self.tr._("yes"):
            text = self.tr._("Logout successful")
            self.login[update.message.chat_id] = 0
            self.chats[update.message.chat_id]['login'] = "no"
        else:
            text = self.tr._("Logout cancelled")
        reply_markup = telegram.ReplyKeyboardRemove()
        self.bot.send_message(chat_id=update.message.chat_id, 
                              text=text, 
                              reply_markup=reply_markup)
        self.process = 0

    def doProcessList(self, update):
        self.selectedSection = update.message.text
        if self.existsSection(self.selectedSection):
            text=self.tr._("Configuration values in section ") + self.selectedSection + ":\r\n"
            for option in self.config[self.selectedSection]:  
                option_key = telegram.KeyboardButton(text=option)
                if not option.startswith("_"):
                    text = text + option + "=" + self.config.get(self.selectedSection, option) + "\r\n";
            reply_markup = telegram.ReplyKeyboardRemove()
            self.process = TelegramBot.CONFIG2
        else:
            text = self.tr._("Sorry, invalid section. Enter /list and try again.") 
            reply_markup = telegram.ReplyKeyboardRemove()
            self.process = 0
        self.bot.send_message(chat_id=update.message.chat_id, 
                              text=text, 
                              reply_markup=reply_markup)

    def doProcessNotification(self, update):
        yesno = update.message.text.lower()
        reply_markup = telegram.ReplyKeyboardRemove()
        if yesno == self.tr._("yes"):
            self.chats[update.message.chat_id]['notification'] = yesno
            text = self.tr._("Motion sensor notification enabled")
        elif yesno == self.tr._("no"):
            self.chats[update.message.chat_id]['notification'] = yesno
            text = self.tr._("Motion sensor notification disabled")
        else:
            text = self.tr._("Sorry, but I don't understand.")
        self.bot.send_message(chat_id=update.message.chat_id, 
                              text=text, 
                              reply_markup=reply_markup)
            
    def doProcessLight(self, update):
        lightselection = update.message.text.lower()
        reply_markup = telegram.ReplyKeyboardRemove()
        if lightselection == self.tr._("on"):
            self.hue.setMode (HueClass.ON)
            text = self.tr._("Switch light on")
        elif lightselection == self.tr._("off"):
            self.hue.setMode (HueClass.OFF)
            text = self.tr._("Switch light off")
        elif lightselection == self.tr._("motion"):
            self.hue.setMode (HueClass.MOTION)
            text = self.tr._("Switch light on in case of motion detection")
        else:
            text = self.tr._("Sorry, but I don't understand.")
        self.bot.send_message(chat_id=update.message.chat_id, 
                              text=text, 
                              reply_markup=reply_markup)

    def doProcessEcho(self, update):
        update.message.reply_text(self.tr._("Sorry, but I don't understand."))
        update.message.reply_text(self.tr._("If you need support just enter /help"))
        self.process = 0

    def startProcess(self, process):
        self.process = process

###############################################################################
#                                                                             # 
#                            Handler definition                               # 
#                                                                             # 
###############################################################################

    def handleUpdate(self, update):
        self.logger.info(str(update.message.chat_id) + " " + update.message.text)
        print str(update.message.chat_id) + " " + update.message.text
        if   update.message.text == '/start':
            self.handleStart(update)
        elif update.message.text == '/help':
            self.handleHelp(update)
        elif update.message.text == '/login':
            self.handleLogin(update)
        elif update.message.text == '/logout':
            self.handleLogout(update)
        elif update.message.text == '/status':
            self.handleStatus(update)
        elif update.message.text == '/light':
            self.handleLight(update)
        elif update.message.text == '/photo':
            self.handlePhoto(update)
        elif update.message.text == '/video':
            self.handleVideo(update)
        elif update.message.text == '/list':
            self.handleList(update)
        elif update.message.text == '/notification':
            self.handleNotification(update)
        elif update.message.text == '/restart':
            self.handleExit(update)
        else:
            self.handleMessage(update)

    def handleMessage(self, update):
        print "handleMessage"
        if self.process == TelegramBot.LOGIN:
            self.doProcessLogin(update)
        elif self.process == TelegramBot.LOGOUT: 
            self.doProcessLogout(update)
        elif self.process == TelegramBot.LIST: 
            self.doProcessList(update)
        elif self.process == TelegramBot.NOTIFICATION:
            self.doProcessNotification(update)
        elif self.process == TelegramBot.LIGHT:
            self.doProcessLight(update)
        else:
            self.doProcessEcho(update)

    def handleStart(self, update):
        self.login[update.message.chat_id] = 0
        self.startProcess (TelegramBot.START)
        update.message.reply_text(self.tr._("Welcome to the the world's smartest motion tracker.") + self.tr._("If you need support just enter /help"))

    def handleStatus(self, update):
        if self.isLoggedIn(update):
            self.startProcess (TelegramBot.START)
            update.message.reply_text(self.tr._("Bot is up and running since ") + str(self.starttime))
            for key,values in self.chats.iteritems():
                chatMessage = ""
                for valueskey,valuesvalue in values.iteritems():
                    chatMessage = chatMessage + "\r\n" + str(valueskey) + ":= " + str(valuesvalue)
                chatMessage = chatMessage + "\r\n" + self.tr._("Light") + ":= " + str(self.hue.getLightState())
                update.message.reply_text(self.tr._("Chat") + " " + str(key) + chatMessage)
        else:
            self.loginRequred(update)

    def handleLight(self, update):
        if self.isLoggedIn(update):
            self.startProcess (TelegramBot.LIGHT)
            on_key = telegram.KeyboardButton(text=self.tr._("On"))
            off_key  = telegram.KeyboardButton(text=self.tr._("Off"))
            motion_key  = telegram.KeyboardButton(text=self.tr._("Motion"))
            light_keyboard = [[ on_key, off_key, motion_key ]]
            reply_markup = telegram.ReplyKeyboardMarkup(light_keyboard)
            self.bot.send_message(chat_id=update.message.chat_id,
                                 text=self.tr._("Switch light?"),
                                 reply_markup=reply_markup)
        else:
            self.loginRequred(update)

    def handleHelp(self, update):
        update.message.reply_text(self.tr._("I can help youe with your motion sensor.") + "\r\n" +
                                  self.tr._("You can control me by sending these commands:") + "\r\n" +
                                  self.tr._("/login - You have to login before you can use me") + "\r\n" + 
                                  self.tr._("/logout - Logout from the motion sensor") + "\r\n" + 
                                  self.tr._("/notification - Enable/disable motion sensor notifications") + "\r\n" + 
                                  self.tr._("/list - Show motion sensor configuration") + "\r\n" + 
                                  self.tr._("/light - Switch on/off the light") + "\r\n" + 
                                  self.tr._("/status - Get current status of ther motion sensor") + "\r\n" + 
                                  self.tr._("/restart - In case of problems, you can restart the motion sensor") + "\r\n" + 
                                  self.tr._("/photo - Capture a photo from the camera") + "\r\n" + 
                                  self.tr._("/video - Capture a short video from the camera") + "\r\n")

    def camHandler(self, filename, chat_id, type):
        self.logger.info("camHandler chat_id: " + str(chat_id) + " filename: " + str(filename) + " type: " + str(type))
        timeString = str(time.strftime("%Y-%m-%d %H:%M"))
        if type == "jpg": 
            self.bot.send_photo(chat_id=chat_id, photo=open(str(filename), 'rb'))
            self.bot.send_message(chat_id=chat_id, text=self.tr._("Photo:") + " " + timeString)
        elif type == "h264":
            self.bot.send_video(chat_id=chat_id, video=open(str(filename), 'rb'), timeout=180) # 180 sec. timeout
            self.bot.send_message(chat_id=chat_id, text=self.tr._("Video:") + " " + timeString)
        elif type == "dis":
            self.bot.send_message(chat_id=chat_id, text=self.tr._("Camera is disabled by configurataion."))
        elif type == "err":
            self.bot.send_message(chat_id=chat_id, text=self.tr._("Error convertig video file:") + " " + filename)
        else:
            self.logger.info("camHandler unknown type: " + camElement.type)
        
    def handlePhoto(self, update):
        if self.isLoggedIn(update):
            update.message.reply_text(self.tr._("Please wait a moment until the photo is taken"))
            self.camThread.takePhoto(update.message.chat_id)
        else:
            self.loginRequred(update)

    def handleVideo(self, update):
        if self.isLoggedIn(update):
            update.message.reply_text(self.tr._("Please wait a moment. Video capturing will be performed"))
            self.camThread.takeVideo(update.message.chat_id)
        else:
            self.loginRequred(update)

    def handleNotification(self, update):
        if self.isLoggedIn(update):
            self.startProcess (TelegramBot.NOTIFICATION)
            yes_key = telegram.KeyboardButton(text=self.tr._("Yes"))
            no_key  = telegram.KeyboardButton(text=self.tr._("No"))
            yes_no_keyboard = [[ yes_key, no_key ]]
            reply_markup = telegram.ReplyKeyboardMarkup(yes_no_keyboard)
            self.bot.send_message(chat_id=update.message.chat_id,
                                 text=self.tr._("Do you want to get notified in case of motion detection?"),
                                 reply_markup=reply_markup)
        else:
            self.loginRequred(update)

    def handleList(self, update):
        if self.isLoggedIn(update):
            self.startProcess (TelegramBot.LIST)
            message=self.tr._("Which section of the configuration do you want to inspect?")
            self.showSectionKeyboardMessage (update, message)
        else:
            self.loginRequred(update)

    def handleLogin(self, update):
        self.startProcess (TelegramBot.LOGIN)
        update.message.reply_text(self.tr._("Enter your password:"))

    def handleLogout(self, update):
        if self.isLoggedIn(update):
            self.startProcess (TelegramBot.LOGOUT)
            yes_key = telegram.KeyboardButton(text=self.tr._("Yes"))
            no_key  = telegram.KeyboardButton(text=self.tr._("No"))
            yes_no_keyboard = [[ yes_key, no_key ]]
            reply_markup = telegram.ReplyKeyboardMarkup(yes_no_keyboard)
            self.bot.send_message(chat_id=update.message.chat_id,
                                 text=self.tr._("Do you want to logout?"),
                                 reply_markup=reply_markup)
        else:
            update.message.reply_text(self.tr._("You are not logged in. You don't need to logout."))

    def handleExit(self, update):
        if self.isLoggedIn(update):
            update.message.reply_text(self.tr._("Exit done. Restart will occur now."))
            self.bot.get_updates( offset=self.offset, timeout=1, network_delay=1)
            self.running = 0
            self.pirThread.quit()
            self.camThread.quit()
            self.hue.quit()
            sys.exit()
        else:
            self.loginRequred(update)

###############################################

    def showSectionKeyboardMessage (self, update, message):
        sections = self.config.sections()
        section_keyboard = [[],[]]
        row = 0
        for section in sections:
            section_key = telegram.KeyboardButton(text=section) 
            section_keyboard[row].append(section_key)
            row = (row + 1) % 2
        reply_markup = telegram.ReplyKeyboardMarkup(section_keyboard)
        self.bot.send_message(chat_id=update.message.chat_id,
                              text=message,
                              reply_markup=reply_markup)

    def isValidOptionValue(self, section, option, value):
        return True # TODO Input validation

    def existsOption(self, section, option):
        return self.config.has_option(section, option)

    def existsSection(self, section):
        return self.config.has_section(section) 

    def isLoggedIn(self, update):
        if update.message.chat_id in self.login and self.login[update.message.chat_id] == 1:
            return 1
        else:
            return 0

    def loginRequred(self, update):
        update.message.reply_text(self.tr._("Login required. Please /login first."))

