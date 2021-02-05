#! /usr/bin/env python
# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
import settings 
import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from threading import Thread
import logging

import RPi.GPIO as GPIO

BUTTON_GPIO = 4
global x
global y = False


logging.basicConfig(level=logging.DEBUG, filename='myapp.log', format='%(asctime)s %(levelname)s:%(message)s')
bot = telebot.TeleBot(settings.TOKEN, parse_mode=None)

off = u'\U000025EF'
on = u'\U00002B24'
toright = u'\U00002192'
toleft = u'\U00002190'
upd = u'\U000021BB'

signaling = {
    'Signaling': off,
}

status = {
    'HeatFloor': off,
    'HeatEngine': off,
    'HangarLighting': off,
}

def checkUpdate(event):
    global x
    x = datetime.now()
    bot.send_message(chat_id = 441494356, text = 'Обнаружено движение', parse_mode='HTML')
    y = True


def xxx():
    global y
    if (GPIO.input(BUTTON_GPIO) == 0) and y:
        text = x - datetime.now()
        bot.send_message(chat_id = 441494356, text, parse_mode='HTML')
        y = False



# class Sensor(ABC):    
#     def __init__(self, pinIn, isInner):
#         self.pinIn = pinIn
#         self.isInner = isInner

#         self.blink = 0 
        
#         # gpio.setmode(gpio.BCM)
#         # gpio.stup(pin, gpio.IN)
    


# class ExternalArea(Sensor):
#     state = False


# class CleanArea(Sensor):
#     state = False


#     t3 = datetime.now() 

#     def __init__(self, pinIn, isInner):
#         super().__init__(pinIn, isInner)
#         self.maximumFalses = 100000
#         self.time_sensitive = 1.5
#         self.warningRathing = 0 

#     def handler(self):

#         if self.state :    #  and gpio.input(pinIn)
#             self.blink+=1

#             if (datetime.now() - self.t3).seconds < self.time_sensitive and self.blink > self.maximumFalses:
#                 self.warningRathing +=1 
#                 print('aaaa')
#                 logging.info('Обнаружен блинк  движения с порогом ' + str(self.maximumFalses)+", с пина "+ str(self.pinIn))

#             # обнутелние таймера если за время T не замечено движений выше порого фильтрации
#             if (datetime.now() - self.t3).seconds >= self.time_sensitive:
#                 self.t3 = datetime.now() 
#                 self.blink = 0
        


#     def calibration(self):
#         calibration_cycles = 5
#         self.maximumFalses = 0

#         for i in range(1, calibration_cycles):
#             t3 = datetime.now()

#             while (datetime.now() - t3).seconds < self.time_sensitive:        
#                 self.handler()
#                 if self.blink > self.maximumFalses: self.maximumFalses = self.blink
#             self.blink = 0
#         logging.info ("Калибровка датчика на пине "+ str(self.pinIn) +" завершена. Число ложных сигналов:  "+str(self.blink))
            


# s15 = CleanArea(15, True) 
# s16 = CleanArea(16, True) 
# s17 = CleanArea(17, True) 
# s18 = CleanArea(18, True) 

# s19 = CleanArea(19, True) 
# s20 = CleanArea(20, True) 
# s21 = CleanArea(21, True) 
# s22 = CleanArea(22, True) 


# while True:
    # s15.handler()
    # s16.handler()
    # s17.handler()
    # s18.handler()

    # s19.handler()
    # s20.handler()
    # s21.handler()
    # s22.handler()

def main_markup():
    enabled_count = 0
    for value in status.values():
        if value == on:
            enabled_count += 1
    enabled_count = str(enabled_count)

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("Сигнализация  "+ signaling.get('Signaling') , callback_data="Signaling"),
        InlineKeyboardButton("Управление ("+enabled_count+")  "+toright, callback_data="Manage"),
    )
    markup.row(
        InlineKeyboardButton("Сводка", callback_data="Report"),
        InlineKeyboardButton("Обновить " + upd, callback_data="Update"),
    )
    return markup



def main_markup_info():
    d = datetime.now() + timedelta(hours=0)
    text = """
Информация по состоянию представлена на """ + str(d.strftime("%d %b %H:%M") + """ мск""")
    return text



@bot.message_handler(commands=['start', 'help'])
@bot.message_handler(content_types=["text"])
def send_welcome(message):
    bot.send_message(message.chat.id, text=main_markup_info(), reply_markup=(main_markup()))



@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):

    def update_icon(name):
        if status.get(name) == off:
            status.update({name: on})
        else:
            status.update({name: off})

    def manage_markup():
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("Подогрев пола  " + status.get('HeatFloor'), callback_data="HeatFloor"),
            InlineKeyboardButton("Подогрев двигателя самолета  " + status.get('HeatEngine'),
                                 callback_data="HeatEngine"),
            InlineKeyboardButton("Приангарное освещение  " + status.get('HangarLighting'),
                                 callback_data="HangarLighting"),

            InlineKeyboardButton(toleft+" Главная ", callback_data="ToMain"),
        )
        return markup


    # MAIN CALLBACKS
    if call.data == "Signaling":
        if signaling.get("Signaling") == off:
            signaling.update({"Signaling": on})
        else:
            signaling.update({"Signaling": off})
        bot.edit_message_text(main_markup_info(), call.message.chat.id, call.message.message_id, reply_markup=main_markup())


    

    elif call.data == "Manage":
        bot.edit_message_text(main_markup_info(), call.message.chat.id, call.message.message_id,
                              reply_markup=manage_markup())

    elif call.data == "Update":
        bot.edit_message_text(main_markup_info(), call.message.chat.id, call.message.message_id, reply_markup=main_markup())
    elif call.data == "ToMain":
        bot.edit_message_text(main_markup_info(), call.message.chat.id, call.message.message_id, reply_markup=main_markup())




    


    elif call.data == "Report":
        text = """
    Сводка:
    ----------------------------
    подогрев пола          выкл 
    подогрев двигателя     вкл 
    ----------------------------

    Последняя активность внутри ангара была 24 Декабря в 11:20
    """
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              reply_markup=main_markup())
    # MANAGEMENT CALLBACKS
    elif call.data == "HeatFloor":
        update_icon("HeatFloor")
        bot.edit_message_text(main_markup_info(), call.message.chat.id, call.message.message_id,
                              reply_markup=manage_markup())

    elif call.data == "HeatEngine":
        update_icon("HeatEngine")
        bot.edit_message_text(main_markup_info(), call.message.chat.id, call.message.message_id,
                              reply_markup=manage_markup())

    elif call.data == "HangarLighting":
        update_icon("HangarLighting")
        bot.edit_message_text(main_markup_info(), call.message.chat.id, call.message.message_id,
                              reply_markup=manage_markup())




GPIO.setmode(GPIO.BCM)

GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.add_event_detect(BUTTON_GPIO, GPIO.RISING, callback=checkUpdate, bouncetime=50)

Thread(target=xxx, args=()).start()

while True:
    try:
        bot.polling(none_stop=True)
    except Exception as E:
        time.sleep(1)