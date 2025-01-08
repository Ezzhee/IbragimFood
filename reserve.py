import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext, ConversationHandler, MessageHandler, filters
from datetime import datetime, timedelta

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация базы данных SQLite
conn = sqlite3.connect('bookings.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    name TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL
)
''')
conn.commit()

# Этапы общения
NAME, DATE, TIME = range(3)

# Обработчик команды /start
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Добро пожаловать! Чтобы забронировать столик, нажмите /book')

# Обработчик команды /book, начало процесса
async def book(update: Update, context: CallbackContext):
    await update.message.reply_text('Как вас зовут?')
    return NAME

# Получение имени пользователя
async def get_name(update: Update, context: CallbackContext):
    context.user_data['name'] = update.message.text
    await update.message.reply_text('Спасибо! Теперь выберите дату для бронирования.')
    dates = [(datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    keyboard = [[InlineKeyboardButton(date, callback_data=f"date_{date}")] for date in dates]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Выберите дату:', reply_markup=reply_markup)
    return DATE

# Выбор даты
async def choose_date(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    selected_date = query.data.split("_")[1]
    context.user_data['date'] = selected_date
    times = [f"{hour}:00" for hour in range(10, 22)]  # Часы с 10 до 22
    keyboard = [[InlineKeyboardButton(time, callback_data=f"time_{selected_date}_{time}")] for time in times]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=f"Вы выбрали дату {selected_date}. Теперь выберите время:", reply_markup=reply_markup)
    return TIME

# Выбор времени и завершение бронирования
async def choose_time(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    selected_time = query.data.split("_")[2]
    username = query.from_user.username
    name = context.user_data['name']
    date = context.user_data['date']
    cursor.execute('INSERT INTO bookings (username, name, date, time) VALUES (?, ?, ?, ?)', (username, name, date, selected_time))
    conn.commit()
    await query.edit_message_text(text=f"Ваш столик забронирован на {date} в {selected_time}.\nПодтверждение отправлено.")
    await context.bot.send_message(chat_id=query.message.chat_id, text=f"Подтверждение: ваш столик забронирован на {date} в {selected_time}. Спасибо!")
    return ConversationHandler.END

# Отмена бронирования
async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text('Бронирование отменено.')
    return ConversationHandler.END

# Основная функция
def main():
    application = Application.builder().token("6806195245:AAHp_o0iYMP4miCXSD90SPAiX8CSZoL2IbU").build()

    # Обработчики команд
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('book', book)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            DATE: [CallbackQueryHandler(choose_date, pattern=r"^date_")],
            TIME: [CallbackQueryHandler(choose_time, pattern=r"^time_")],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
