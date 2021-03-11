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

import time 
# import RPi.GPIO as GPIO


off = u'\U000025EF'
on = u'\U00002B24'
toright = u'\U00002192'
toleft = u'\U00002190'
upd = u'\U000021BB'
wrn = u'\U0001F53A'

logging.basicConfig(level=logging.INFO, filename='myapp.log', format='%(asctime)s %(levelname)s:%(message)s')

bot = telebot.TeleBot(settings.TOKEN, parse_mode=None)

whitelist = []


status = {
    'HeatFloor': off,
    'HeatEngine': off,
    'HangarLighting': off,
}




class Sensor(ABC):    
    def __init__(self, pinIn, isInner):
        self.pinIn = pinIn
        self.isInner = isInner

        self.blink = 0 
        
        
        # GPIO.setmode(GPIO.BCM)
        # GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    

class CleanArea(Sensor):
    operating_mode = False # true -- security enable, by default system disabled
    uni_symbol = off
    t3 = datetime.now() 

    messwrnng_buf = []
    keyboardes_buf = []

    def __init__(self, pinIn, isInner):
        super().__init__(pinIn, isInner)

        #False positives neutralization preferences
        self.maximumFalses = 2
        self.time_sensitive = 5 
        #warningRathing is increasуs when a signal is recived from several sensors
        self.warningRathing = 0 
        
        self.t_pushing = 0


    def handler(self):

        if self.operating_mode: #and GPIO.input(self.pinIn) == GPIO.LOW
            self.blink+=1

            if self.blink >= self.maximumFalses:
                self.warningRathing +=1 
                logging.info(f'Обнаружен блинк движения с порогом {self.maximumFalses}, с пина {self.pinIn}')

                # push notification into chat for all users after that since 24 hourh we should delete this items.
                text = wrn + f'В основном ангаре прямо сейчас обнаружено движение. Важность {self.warningRathing}'

                if time.time()-self.t_pushing > 5: #ограничение по времени. отправлять не чаще X
                    for memeber in whitelist: message = bot.send_message(memeber, text)
                    self.t_pushing = time.time()

                
                    #add yet sensed message in the buffer
                    f = str(message.message_id) + ' ' + str(time.time())
                    CleanArea.messwrnng_buf.append(f)

           

                # WRITE ON WR AND TIME into datastruct edit markup_info

 
            # обнутелние таймера если за время T не замечено движений выше порого фильтрации
            if (datetime.now() - self.t3).seconds > self.time_sensitive:
                self.t3 = datetime.now() 
                self.blink = 0

        


    def calibration(self):
        self.maximumFalses, calibration_cycles = 0, 5

        for i in range(1, calibration_cycles):
            t3 = datetime.now()

            while (datetime.now() - t3).seconds < self.time_sensitive:        
                self.handler()

                if self.blink > self.maximumFalses: self.maximumFalses = self.blink

            self.blink = 0

        logging.info (f"Калибровка датчика на пине {self.pinIn} завершена. Число допустимых ложных сигналов: {self.blink})
            


s15 = CleanArea(15, True) 


def mkp_text():
    d = datetime.now() + timedelta(hours=0)
    text = f'Cинхронизация с контроллером { str(d.strftime("%d %b %H:%M")) } мск'
    text += f'\n\nПоследнее несанкционированное движения в ангарах: { str(d.strftime("%d %b %H:%M")) } '
    text += f'\n\neсли оно ложно, \nто использовать /calibration'
    return text


def main_markup():
    enabled_count = 0
    for value in status.values():
        if value == on:
            enabled_count += 1
    enabled_count = str(enabled_count)

    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("Сигнализация "+ CleanArea.uni_symbol , callback_data="Signaling"),
        InlineKeyboardButton(f"Управление ({enabled_count}) {toright}", callback_data="Manage"),
    )
    markup.row(
        InlineKeyboardButton("Сводка", callback_data="Report"),
        InlineKeyboardButton("Обновить " + upd, callback_data="Update"),
    )
    return markup

@bot.message_handler(commands=['start', 'help'])
@bot.message_handler(content_types=["text"])
def send_welcome(message):
    if message.chat.id not in whitelist: 
        if message.text == settings.AUTH_PASS: 
            whitelist.append(message.chat.id) 
            x = bot.send_message(message.chat.id, text=mkp_text(), reply_markup=(main_markup()))
        else: bot.send_message(message.chat.id, text='password required  (இдஇ; )')

    else: 
        x = bot.send_message(message.chat.id, text=mkp_text(), reply_markup=(main_markup()))


    p, n = {'chat_id': message.chat.id, 'mess_id': message.message_id}, {'chat_id': x.chat.id, 'mess_id': x.message_id}
    CleanArea.keyboardes_buf.append(p)
    CleanArea.keyboardes_buf.append(n)


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
            InlineKeyboardButton(f"Подогрев пола { status.get('HeatFloor') }", callback_data="HeatFloor"),
            InlineKeyboardButton(f"Подогрев двигателя самолета {status.get('HeatEngine')}", callback_data="HeatEngine"),
            InlineKeyboardButton(f"Приангарное освещение  {status.get('HangarLighting')}", callback_data="HangarLighting"),
            InlineKeyboardButton(f"{toleft} Главная", callback_data="ToMain"),
        )
        return markup


    # MAIN CALLBACKS
    if call.data == "Signaling":

        CleanArea.operating_mode = not CleanArea.operating_mode
        CleanArea.uni_symbol = on if CleanArea.operating_mode else off

        bot.edit_message_text(mkp_text(), call.message.chat.id, call.message.message_id, reply_markup=main_markup())

    elif call.data == "Update":
        bot.edit_message_text(mkp_text(), call.message.chat.id, call.message.message_id, reply_markup=main_markup())
    elif call.data == "ToMain":
        bot.edit_message_text(mkp_text(), call.message.chat.id, call.message.message_id, reply_markup=main_markup())

    elif call.data == "Report":
        bot.edit_message_text('text', call.message.chat.id, call.message.message_id,
                              reply_markup=main_markup())



    elif call.data == "Manage":
        bot.edit_message_text(mkp_text(), call.message.chat.id, call.message.message_id,
                              reply_markup=manage_markup())

    # MANAGEMENT CALLBACKS
    elif call.data == "HeatFloor":
        update_icon("HeatFloor")
        bot.edit_message_text(mkp_text(), call.message.chat.id, call.message.message_id,
                              reply_markup=manage_markup())

    elif call.data == "HeatEngine":
        update_icon("HeatEngine")
        bot.edit_message_text(mkp_text(), call.message.chat.id, call.message.message_id,
                              reply_markup=manage_markup())

    elif call.data == "HangarLighting":
        update_icon("HangarLighting")
        bot.edit_message_text(mkp_text(), call.message.chat.id, call.message.message_id,
                              reply_markup=manage_markup())
        print(call.message.chat.id, call.message.message_id)



def thread_function(a):
    # Время самоуничтожения уведомлений об обнаружении движения в секундах 
    destructionTime = 30 

    t = datetime.now()
    while True:


        # УДАЛЯЕТ УВЕОДОМЛЕНИЯ О ДВИЖЕНИИ
        for el in CleanArea.messwrnng_buf: 
            x = float(el.split(' ')[1])  
            if time.time() - x > destructionTime: 
                for member in whitelist: bot.delete_message(member, el.split(' ')[0])
                CleanArea.messwrnng_buf.remove(el)


        # УДАЛЯЕТ ВСЕ СООБЩЕНИЯ, ЕСЛИ В ЧАТЕ ИХ БОЛЬШЕ 1
        y = CleanArea.keyboardes_buf
        if len(y) > 1: 
            bot.delete_message(y[0].get('chat_id'), y[0].get('mess_id'))
            CleanArea.keyboardes_buf.pop(0)

        s15.handler()



if __name__ == "__main__":
    
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO,
                        datefmt="%H:%M:%S")
    logging.info("Main    : before creating thread")
    x = Thread(target=thread_function, args=(1,))
    logging.info("Main    : before running thread")
    x.start()

    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as E:
            time.sleep(1)



# References:
# 1. workink with gpio https://ph0en1x.net/106-rpi-gpio-installation-working-with-inputs-outputs-interrupts.html#pins-numeration-and-setup