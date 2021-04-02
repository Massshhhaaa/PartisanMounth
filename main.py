#! /usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import time

from datetime import datetime, timedelta
from threading import Thread

import telebot
from telebot import types
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


import settings

from abc import ABC, abstractmethod
whitelist = []
user = {}

# import RPi.GPIO as GPIO


class Sensor(ABC):    
    wrn = u'\U0001F53A'
    off =  u'\U000025EF'
    on = u'\U00002B24'
    toright = u'\U00002192'
    toleft = u'\U00002190'
    upd = u'\U000021BB'; 

    def __init__(self, pinIn, isInner):
        self.pinIn = pinIn
        self.isInner = isInner
        self.blink = 0
        # GPIO.setmode(GPIO.BCM)
        # GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    
status = {
    'HeatFloor': Sensor.off,
    'HeatEngine': Sensor.off,
    'HangarLighting': Sensor.off 
}

logging.basicConfig(level=logging.INFO, filename='myapp.log', format='%(asctime)s %(levelname)s:%(message)s')
bot = telebot.TeleBot(settings.TOKEN, parse_mode=None)

class CleanArea(Sensor):
    items = []

    operating_mode = False # true -- security enable, by default system disabled
    uni_symbol = Sensor.off
    t3 = datetime.now() 

    messwrnng_buf = []

    def __init__(self, pinIn, isInner):
        super().__init__(pinIn, isInner)

        #False positives neutralization preferences
        self.maximumFalses = 2
        self.time_sensitive = 5 
        #warningRathing is increasуs when a signal is recived from several sensors
        self.warningRathing = 0 
        
        self.t_pushing = 0
        CleanArea.items.append(self)

    def handler(self):

        if self.operating_mode: #and GPIO.input(self.pinIn) == GPIO.LOW
            self.blink+=1
            if self.blink >= self.maximumFalses:
                self.warningRathing +=1 
                logging.info(f'Обнаружен блинк движения с порогом {self.maximumFalses}, с пина {self.pinIn}')

                return True  # WRITE ON WR AND TIME into datastruct edit markup_info

            # обнутелние таймера если за время T не замечено движений выше порого фильтрации
            if (datetime.now() - self.t3).seconds > self.time_sensitive:
                self.t3 = datetime.now() 
                self.blink = 0

        return False

    def calibration(self):
        self.maximumFalses, calibration_cycles = 0, 5

        # Калибровка состоит из несколькох циклов ожидания = time_sensetive
        for _ in range(1, calibration_cycles):
            t3 = datetime.now()

            while (datetime.now() - t3).seconds < self.time_sensitive:        
                self.handler()

                if self.blink > self.maximumFalses: self.maximumFalses = self.blink

            self.blink = 0

        logging.info (f"Калибровка датчика на пине {self.pinIn} завершена. Число допустимых ложных сигналов: {self.blink}")
        return True

    def send_for_all(self, bot, whitelist): 
        # push notification into chat for all users after that since 24 hourh we should delete this items.
        text = Sensor.wrn + f'В основном ангаре прямо сейчас обнаружено движение. Важность {self.warningRathing}'
        for memeber in whitelist: message = bot.send_message(memeber, text)
        self.t_pushing = time.time()
        #add yet sensed message in the buffer
        f = str(message.message_id) + ' ' + str(time.time())
        CleanArea.messwrnng_buf.append(f)
            


# TELEGRAM KEYBOARDS

def main_markup():
    enabled_count = 0
    # for value in status.values():
    #     if value == on:
    #         enabled_count += 1
    enabled_count = str(enabled_count)
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("Сигнализация "+ CleanArea.uni_symbol , callback_data="Signaling"),
        InlineKeyboardButton("Ночной старт", callback_data="NightStart"),
        InlineKeyboardButton(f"Управление ({enabled_count}) {Sensor.toright}", callback_data="Manage"),
        InlineKeyboardButton("Обновить " + Sensor.upd, callback_data="Update"),
    )
    return markup

def manage_markup():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton(f"Подогрев пола { status.get('HeatFloor') }", callback_data="HeatFloor"),
        InlineKeyboardButton(f"Подогрев двигателя самолета {status.get('HeatEngine')}", callback_data="HeatEngine"),
        InlineKeyboardButton(f"Приангарное освещение  {status.get('HangarLighting')}", callback_data="HangarLighting"),
        InlineKeyboardButton(f"{Sensor.toleft} Главная", callback_data="ToMain"),
    )
    return markup


def mkp_text():
    d = datetime.now() + timedelta(hours=0)
    text = f'Cинхронизация с контроллером { str(d.strftime("%d %b %H:%M")) } мск'
    text += f'\n\nПоследнее несанкционированное движения в ангарах: { str(d.strftime("%d %b %H:%M")) } '
    return text

 

# TELEGRAM INCOMING MESSAGES AND CALLS HANDLER

@bot.message_handler(content_types=['text'])
def send_welcome(message):    

    def send_markup(message):
        bot.delete_message(message.chat.id, message.message_id)
        x = bot.send_message(message.chat.id, text=mkp_text(), reply_markup=(main_markup()))
        
        mess_list = user.get(message.chat.id)
        for i in range(0, len(mess_list)):
            bot.delete_message(mess_list[i].chat.id, mess_list[i].message_id)
            mess_list.pop(i)

        mess_list.append(x)
        user.update({message.chat.id: mess_list})

    if message.chat.id in user: 
        send_markup(message)

    else: 
        if message.text == settings.AUTH_PASS: 
            mess_list = []
            user.update({message.chat.id: mess_list})
            logging.info(f'Добавлен новый чат с пользователем {message.chat.id}')
            send_markup(message)
        else: 
            bot.send_message(message.chat.id, text='Требуется пароль (இдஇ; )')
            bot.delete_message(message.chat.id, message.message_id)
           
     

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
#delete this on testing
    def update_icon(name):
        if status.get(name) == Sensor.off:
            status.update({name: Sensor.on})
        else:
            status.update({name: Sensor.off})

    # MAIN CALLBACKS
    if call.data == "Signaling":
        CleanArea.operating_mode = not CleanArea.operating_mode
        CleanArea.uni_symbol = Sensor.on if CleanArea.operating_mode else Sensor.off

        bot.edit_message_text(  mkp_text(),
                                 call.message.chat.id,
                                 call.message.message_id,
                                reply_markup=main_markup())
    elif call.data == "Update":
        bot.edit_message_text(mkp_text(),
                                call.message.chat.id,
                                call.message.message_id,
                                reply_markup=main_markup())
    elif call.data == "ToMain":
        bot.edit_message_text(  mkp_text(),
                                call.message.chat.id,
                                call.message.message_id,
                                reply_markup=main_markup())
    #Какая нужна структура репорта?
    # elif call.data == "Report":
    #     bot.edit_message_text('text',
    #                             call.message.chat.id,
    #                             call.message.message_id,
    #                             reply_markup=main_markup())
    #Switch to management page
    elif call.data == "Manage":
        bot.edit_message_text(  mkp_text(),
                                call.message.chat.id,
                                call.message.message_id,
                                reply_markup=manage_markup())
    # MANAGEMENT CALLBACKS
    elif call.data == "HeatFloor":
        update_icon("HeatFloor")
        bot.edit_message_text(  mkp_text(),
                                call.message.chat.id,
                                call.message.message_id,
                                reply_markup=manage_markup())
    elif call.data == "HeatEngine":
        update_icon("HeatEngine")
        bot.edit_message_text(  mkp_text(),
                                 call.message.chat.id,
                                 call.message.message_id,
                                 reply_markup=manage_markup())
    elif call.data == "HangarLighting":
        update_icon("HangarLighting")
        bot.edit_message_text(  mkp_text(),
                                call.message.chat.id,
                                call.message.message_id,
                                reply_markup=manage_markup())

s15 = CleanArea(15, True) 
s16 = CleanArea(16, True) 


def sensors_handler():
    while True:

        for sensor in CleanArea.items:
            if time.time()-sensor.t_pushing > 40: #ограничение по времени. отправлять не чаще X seconds
                if sensor.handler(): sensor.send_for_all(bot, whitelist)

 

def watchDog(CleanArea, bot, whitelist):
    # Время самоуничтожения уведомлений об обнаружении движения в секундах 
    destructionTime = 30 

    while True:                 
        # УДАЛЯЕТ УВЕОДОМЛЕНИЯ О ДВИЖЕНИИ
        if CleanArea.messwrnng_buf: 
            for el in CleanArea.messwrnng_buf: 
                x = float(el.split(' ')[1])  
                if time.time() - x > destructionTime: 
                    for member in whitelist: bot.delete_message(member, el.split(' ')[0])
                    CleanArea.messwrnng_buf.remove(el)


    

if __name__ == "__main__":
    
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO,
                        datefmt="%H:%M:%S")
    logging.info("Main    : before creating thread")

    handler    = Thread(target=sensors_handler, args=())

    # FOR DELITING UNNEECESSARY MESSAGES INTO THE CHAT
    watchDog   = Thread(target=watchDog, args=(CleanArea, bot, whitelist))

    # botPooling = Thread(target=bot.polling, args=())

    logging.info("Main    : before running thread")
    # handler.start()

    watchDog.start()

    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as E:
            time.sleep(1)



# References:
# 1. workink with gpio https://ph0en1x.net/106-rpi-gpio-installation-working-with-inputs-outputs-interrupts.html#pins-numeration-and-setup