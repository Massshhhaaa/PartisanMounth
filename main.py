#! /usr/bin/env python
# -*- coding: utf-8 -*-


# 8.12.20 3hour
# 15.12.20 4hour
import settings 
import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta

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
        # InlineKeyboardButton("Подогрев пола  "+ status.get('HeatFloor'), callback_data="®HeatFloor"),
        # InlineKeyboardButton("Подогрев двигателя самолета  "+ status.get('HeatEngine'), callback_data="HeatEngine"),
        # InlineKeyboardButton("Приангарное освещение  "+ status.get('HangarLighting'), callback_data="HangarLighting"),


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


bot.polling(none_stop=True)

