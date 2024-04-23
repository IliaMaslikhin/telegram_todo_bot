import telebot
from telebot import types
import schedule
import time
import threading
from datetime import datetime, timedelta

token = "YOURTOKEN"
bot = telebot.TeleBot(token)

users = {}
reminder_time = None
date = None

def add_todo(user_id, date, task):
    if user_id not in users:
        users[user_id] = {}
    if date not in users[user_id]:
        users[user_id][date] = []
    users[user_id][date].append(task)
    print("Задача", task, "добавлена на дату", date)

def send_reminder(user_id, date):
    if date in users[user_id]:
        for task in users[user_id][date]:
            bot.send_message(user_id, "Напоминание о задаче: " + task)
        del users[user_id][date]

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item1 = types.KeyboardButton('Добавить задачу')
    item2 = types.KeyboardButton('Показать задачи')
    markup.add(item1, item2)
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

@bot.message_handler(content_types=['text'])
def handle_text(message):
    global reminder_time, date
    if message.text == 'Добавить задачу':
        add_task_date(message)
    elif message.text == 'Показать задачи':
        show_tasks(message)
    elif reminder_time is not None and date is None:
        if message.text in ['Сегодня', 'Завтра']:
            date = datetime.now().strftime('%d.%m.%Y') if message.text == 'Сегодня' else (datetime.now() + timedelta(days=1)).strftime('%d.%m.%Y')
            msg = bot.send_message(message.chat.id, 'Введите название задачи')
            bot.register_next_step_handler(msg, handle_text)
        else:
            date = message.text
            msg = bot.send_message(message.chat.id, 'Введите название задачи')
            bot.register_next_step_handler(msg, handle_text)
    elif reminder_time is not None and date is not None:
        task_name = message.text
        add_todo(message.chat.id, date, task_name)
        schedule.every().day.at(reminder_time).do(send_reminder, user_id=message.chat.id, date=date)
        bot.send_message(message.chat.id, "Задача добавлена")
        reminder_time = None
        date = None
        start(message)

def add_task_date(message):
    markup = types.InlineKeyboardMarkup()
    for i in range(24):  # Часы
        button = types.InlineKeyboardButton(text=str(i).zfill(2), callback_data=f"hour_{i}")
        markup.add(button)
    bot.send_message(message.chat.id, "Выберите час:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('hour_'))
def callback_hour(call):
    global reminder_time
    hour = int(call.data.split('_')[1])
    if 0 <= hour < 24:
        reminder_time = str(hour).zfill(2) + ":"
        markup = types.InlineKeyboardMarkup()
        for i in range(60):  # Минуты
            button = types.InlineKeyboardButton(text=str(i).zfill(2), callback_data=f"minute_{i}")
            markup.add(button)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Выберите минуты:", reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "Недопустимый час! Пожалуйста, выберите значение от 0 до 23.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('minute_'))
def callback_minute(call):
    global reminder_time
    minute = int(call.data.split('_')[1])
    if 0 <= minute < 60:
        reminder_time += str(minute).zfill(2)
        markup = types.InlineKeyboardMarkup()
        buttons = ['Сегодня', 'Завтра', 'Другое']
        for button in buttons:
            markup.add(types.InlineKeyboardButton(text=button, callback_data=f"date_{button}"))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Выберите дату:", reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "Недопустимые минуты! Пожалуйста, выберите значение от 0 до 59.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('date_'))
def callback_date(call):
    global date
    selected_date = call.data.split('_')[1]
    if selected_date in ['Сегодня', 'Завтра']:
        date = datetime.now().strftime('%d.%m.%Y') if selected_date == 'Сегодня' else (datetime.now() + timedelta(days=1)).strftime('%d.%m.%Y')
        msg = bot.send_message(call.message.chat.id, 'Введите название задачи')
        bot.register_next_step_handler(msg, handle_text)
    elif selected_date == 'Другое':
        markup = types.InlineKeyboardMarkup()
        months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
        for i, month in enumerate(months, start=1):  # Месяцы
            button = types.InlineKeyboardButton(text=month, callback_data=f"month_{i}")
            markup.add(button)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Выберите месяц:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('day_'))
def callback_day(call):
    global date
    day = int(call.data.split('_')[1])
    if 1 <= day <= 31:
        date += str(day).zfill(2) + "." + str(datetime.now().year)
        msg = bot.send_message(call.message.chat.id, 'Введите название задачи')
        bot.register_next_step_handler(msg, handle_text)
    else:
        bot.answer_callback_query(call.id, "Недопустимый день! Пожалуйста, выберите значение от 1 до 31.")

def show_tasks(message):
    text = ""
    if message.chat.id in users:
        for date in users[message.chat.id]:
            text += date + ':\n'
            for task in users[message.chat.id][date]:
                text += ' - ' + task + '\n'
    if text == "":
        text = "Нет задач"
    bot.send_message(message.chat.id, text)

def run_pending():
    while True:
        schedule.run_pending()
        time.sleep(1)

threading.Thread(target=run_pending).start()
bot.polling(none_stop=True)
