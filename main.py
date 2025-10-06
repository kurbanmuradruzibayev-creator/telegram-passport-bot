import os
import telebot
import requests
import pandas as pd
import json
import re
import logging
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import sqlite3
from datetime import datetime

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# TOKEN olish
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN mavjud emas")

bot = telebot.TeleBot(TOKEN)

# Google Sheets sozlamalari
SHEET_ID = os.getenv("SHEET_ID")
SHEET_GID = os.getenv("SHEET_GID", "0")
if not SHEET_ID:
    raise ValueError("SHEET_ID mavjud emas")

API_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:json&gid={SHEET_GID}"

# SQLite bazasini yaratish
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            usage_count INTEGER DEFAULT 0,
            last_used TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Til sozlamalari
LANGUAGES = {
    'uz': {
        'welcome': "Assalomu alaykum! 👋\n\nPasport raqamingizni yuboring, men guruhingiz va guruh havolangizni topib beraman.",
        'format': "📝 Pasport raqamini shu formatda yuboring: AA1234567",
        'example': "Misol: AD9829103",
        'change_lang': "🌐 Tilni o'zgartirish",
        'search': "🔍 Pasport qidirish",
        'help': "🆘 Yordam",
        'debug': "🐛 Debug ma'lumot",
        'info': "ℹ️ Mening ma'lumotlarim",
        'back': "⬅️ Orqaga",
        'wrong_format': "❌ Noto'g'ri format! Pasport raqami quyidagi formatda bo'lishi kerak: AA1234567",
        'not_found': "❌ {} raqami bo'yicha ma'lumot topilmadi.",
        'found': "✅ Ma'lumot topildi!\n\n📋 Pasport: {}\n👤 Ism: {}\n🏫 Fakultet: {}\n👥 Guruh: {}\n🔗 Havola: {}",
        'error': "😔 Xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.",
        'choose_lang': "🌐 Tilni tanlang:",
        'main_menu': "🏠 Asosiy menyu",
        'usage_limit': "🚫 Siz faqat 1 marta foydalana olasiz! Bu shaxsiy ma'lumotlarni himoya qilish uchun.",
        'user_info': "📊 Sizning ma'lumotlaringiz:\n\n👤 ID: {}\n📛 Ism: {}\n📅 Birinchi foydalanish: {}\n🔢 Foydalanishlar soni: {}/1\n⏰ So'ngi foydalanish: {}",
        'first_usage': "Bu sizning birinchi foydalanishingiz. Ma'lumotlaringiz saqlandi.",
        'admin_contact': "📞 Admin bilan bog'lanish"
    },
    'ru': {
        'welcome': "Здравствуйте! 👋\n\nОтправьте номер паспорта, и я найду вашу группу и ссылку на группу.",
        'format': "📝 Отправьте номер паспорта в формате: AA1234567",
        'example': "Пример: AD9829103",
        'change_lang': "🌐 Сменить язык",
        'search': "🔍 Поиск паспорта",
        'help': "🆘 Помощь",
        'debug': "🐛 Отладка",
        'info': "ℹ️ Мои данные",
        'back': "⬅️ Назад",
        'wrong_format': "❌ Неправильный формат! Номер паспорта должен быть в формате: AA1234567",
        'not_found': "❌ По номеру {} информация не найдена.",
        'found': "✅ Информация найдена!\n\n📋 Паспорт: {}\n👤 Имя: {}\n🏫 Факультет: {}\n👥 Группа: {}\n🔗 Ссылка: {}",
        'error': "😔 Произошла ошибка. Пожалуйста, попробуйте позже.",
        'choose_lang': "🌐 Выберите язык:",
        'main_menu': "🏠 Главное меню",
        'usage_limit': "🚫 Вы можете использовать только 1 раз! Это для защиты личных данных.",
        'user_info': "📊 Ваши данные:\n\n👤 ID: {}\n📛 Имя: {}\n📅 Первое использование: {}\n🔢 Количество использований: {}/1\n⏰ Последнее использование: {}",
        'first_usage': "Это ваше первое использование. Ваши данные сохранены.",
        'admin_contact': "📞 Связаться с админом"
    },
    'en': {
        'welcome': "Hello! 👋\n\nSend your passport number, and I'll find your group and group link.",
        'format': "📝 Send passport number in format: AA1234567",
        'example': "Example: AD9829103",
        'change_lang': "🌐 Change language",
        'search': "🔍 Search passport",
        'help': "🆘 Help",
        'debug': "🐛 Debug info",
        'info': "ℹ️ My information",
        'back': "⬅️ Back",
        'wrong_format': "❌ Wrong format! Passport number should be in format: AA1234567",
        'not_found': "❌ No information found for number {}.",
        'found': "✅ Information found!\n\n📋 Passport: {}\n👤 Name: {}\n🏫 Faculty: {}\n👥 Group: {}\n🔗 Link: {}",
        'error': "😔 An error occurred. Please try again later.",
        'choose_lang': "🌐 Choose language:",
        'main_menu': "🏠 Main menu",
        'usage_limit': "🚫 You can only use 1 time! This is to protect personal data.",
        'user_info': "📊 Your information:\n\n👤 ID: {}\n📛 Name: {}\n📅 First usage: {}\n🔢 Usage count: {}/1\n⏰ Last used: {}",
        'first_usage': "This is your first usage. Your data has been saved.",
        'admin_contact': "📞 Contact admin"
    }
}

# Foydalanuvchi tillari saqlash
user_languages = {}

def get_user_language(chat_id):
    """Foydalanuvchi tilini olish"""
    return user_languages.get(chat_id, 'uz')

def check_usage_limit(user_id):
    """Foydalanish cheklovini tekshirish"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT usage_count FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result and result[0] >= 1:
        return False  # Cheklovga duchor
    return True  # Foydalanish mumkin

def update_user_usage(message):
    """Foydalanuvchi ma'lumotlarini yangilash"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Foydalanuvchi mavjudligini tekshirish
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        # Yangilash
        cursor.execute('''
            UPDATE users 
            SET usage_count = usage_count + 1, 
                last_used = CURRENT_TIMESTAMP,
                username = ?, first_name = ?, last_name = ?
            WHERE user_id = ?
        ''', (username, first_name, last_name, user_id))
    else:
        # Yangi foydalanuvchi
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, last_name, usage_count, last_used)
            VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
        ''', (user_id, username, first_name, last_name))
    
    conn.commit()
    conn.close()

def get_user_info(user_id):
    """Foydalanuvchi ma'lumotlarini olish"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, username, first_name, last_name, usage_count, 
               created_at, last_used 
        FROM users WHERE user_id = ?
    ''', (user_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    return result

def create_main_keyboard(lang):
    """Asosiy keyboard yaratish"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    lang_text = LANGUAGES[lang]
    
    keyboard.add(
        KeyboardButton(lang_text['search']),
        KeyboardButton(lang_text['info']),
        KeyboardButton(lang_text['help']),
        KeyboardButton(lang_text['debug'])
    )
    keyboard.add(KeyboardButton(lang_text['change_lang']))
    
    return keyboard

def create_language_keyboard(lang):
    """Til tanlash keyboard yaratish"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    lang_text = LANGUAGES[lang]
    
    keyboard.add(
        KeyboardButton("🇺🇿 O'zbek"),
        KeyboardButton("🇷🇺 Русский"),
        KeyboardButton("🇺🇸 English")
    )
    keyboard.add(KeyboardButton(lang_text['back']))
    
    return keyboard

def create_back_keyboard(lang):
    """Faqat orqaga tugmasi"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(LANGUAGES[lang]['back']))
    return keyboard

def load_data():
    """Google Sheets'dan jadvalni DataFrame sifatida olish"""
    try:
        resp = requests.get(API_URL, timeout=10)
        resp.raise_for_status()
        
        text = resp.text

        # Google JSON formatini tozalash
        match = re.search(r"google.visualization.Query.setResponse\((.*)\);", text, re.DOTALL)
        if not match:
            raise ValueError("Google Sheets JSON ni o'qib bo'lmadi")
        
        json_str = match.group(1)
        data = json.loads(json_str)

        # Ustun nomlari - birinchi qatordagi ma'lumotlardan olamiz
        if data["table"]["rows"]:
            first_row = data["table"]["rows"][0]
            cols = [cell["v"] if cell and "v" in cell else f"Column_{i+1}" 
                   for i, cell in enumerate(first_row["c"])]
        else:
            # Agar qator bo'lmasa, default nomlar
            cols = [f"Column_{i+1}" for i in range(len(data["table"]["cols"]))]

        # Qatorlar (birinchi qatorni o'tkazib yuboramiz, chunki u sarlavha)
        rows = []
        for i, r in enumerate(data["table"]["rows"]):
            if i == 0:  # Birinchi qator sarlavha, uni o'tkazib yuboramiz
                continue
            values = [cell["v"] if cell and "v" in cell else "" for cell in r["c"]]
            rows.append(values)

        df = pd.DataFrame(rows, columns=cols)
        logger.info(f"Ma'lumotlar muvaffaqiyatli yuklandi. {len(df)} qator")
        logger.info(f"Ustunlar: {list(df.columns)}")
        return df
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Google Sheets ga ulanishda xatolik: {e}")
        raise
    except Exception as e:
        logger.error(f"Ma'lumotlarni o'qishda xatolik: {e}")
        raise

# /start komandasi
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user_languages[message.chat.id] = 'uz'  # Default til
    lang = get_user_language(message.chat.id)
    lang_text = LANGUAGES[lang]
    
    welcome_text = (
        f"{lang_text['welcome']}\n\n"
        f"{lang_text['format']}\n\n"
        f"{lang_text['example']}"
    )
    
    bot.send_message(
        message.chat.id, 
        welcome_text,
        reply_markup=create_main_keyboard(lang)
    )

# INFO tugmasi
@bot.message_handler(func=lambda msg: any(msg.text == LANGUAGES[lang]['info'] for lang in LANGUAGES))
def user_info(message):
    user_id = message.from_user.id
    lang = get_user_language(message.chat.id)
    lang_text = LANGUAGES[lang]
    
    user_data = get_user_info(user_id)
    
    if user_data:
        user_id, username, first_name, last_name, usage_count, created_at, last_used = user_data
        
        full_name = f"{first_name or ''} {last_name or ''}".strip() or "Noma'lum"
        created_str = created_at.split()[0] if created_at else "Noma'lum"
        last_used_str = last_used.split()[0] if last_used else "Hali foydalanilmagan"
        
        info_text = lang_text['user_info'].format(
            user_id, full_name, created_str, usage_count, last_used_str
        )
    else:
        info_text = "📊 Siz hali foydalanmagan
