import os
import telebot
import requests
import pandas as pd
import json
import re
import logging
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import json
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

# JSON fayl orqali foydalanuvchi ma'lumotlarini saqlash
USERS_FILE = 'users.json'

def load_users():
    """Foydalanuvchilarni yuklash"""
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    """Foydalanuvchilarni saqlash"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def check_usage_limit(user_id):
    """Foydalanish cheklovini tekshirish"""
    users = load_users()
    user = users.get(str(user_id))
    
    if user and user.get('usage_count', 0) >= 1:
        return False  # Cheklovga duchor
    return True  # Foydalanish mumkin

def update_user_usage(message):
    """Foydalanuvchi ma'lumotlarini yangilash"""
    user_id = str(message.from_user.id)
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    users = load_users()
    
    if user_id in users:
        # Yangilash
        users[user_id]['usage_count'] += 1
        users[user_id]['last_used'] = datetime.now().isoformat()
        users[user_id]['username'] = username
        users[user_id]['first_name'] = first_name
        users[user_id]['last_name'] = last_name
    else:
        # Yangi foydalanuvchi
        users[user_id] = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'usage_count': 1,
            'created_at': datetime.now().isoformat(),
            'last_used': datetime.now().isoformat()
        }
    
    save_users(users)

def get_user_info(user_id):
    """Foydalanuvchi ma'lumotlarini olish"""
    users = load_users()
    return users.get(str(user_id))

def create_main_keyboard():
    """Asosiy keyboard yaratish"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    keyboard.add(
        KeyboardButton("🔍 Pasport qidirish"),
        KeyboardButton("ℹ️ Mening ma'lumotlarim"),
        KeyboardButton("🆘 Yordam"),
        KeyboardButton("🐛 Debug ma'lumot")
    )
    
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
    welcome_text = (
        "Assalomu alaykum! 👋\n\n"
        "Pasport raqamingizni yuboring, men guruhingiz va guruh havolangizni topib beraman.\n\n"
        "📝 Pasport raqamini shu formatda yuboring: AA1234567"
    )
    
    bot.send_message(
        message.chat.id, 
        welcome_text,
        reply_markup=create_main_keyboard()
    )

# INFO tugmasi
@bot.message_handler(func=lambda msg: msg.text == "ℹ️ Mening ma'lumotlarim")
def user_info(message):
    user_id = message.from_user.id
    
    user_data = get_user_info(user_id)
    
    if user_data:
        created_at = user_data.get('created_at', '')
        last_used = user_data.get('last_used', '')
        usage_count = user_data.get('usage_count', 0)
        
        # Sana formatini soddalashtirish
        created_str = created_at.split('T')[0] if created_at else "Noma'lum"
        last_used_str = last_used.split('T')[0] if last_used else "Hali foydalanilmagan"
        
        full_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip() or "Noma'lum"
        
        info_text = (
            f"📊 Sizning ma'lumotlaringiz:\n\n"
            f"👤 ID: {user_id}\n"
            f"📛 Ism: {full_name}\n"
            f"📅 Birinchi foydalanish: {created_str}\n"
            f"🔢 Foydalanishlar soni: {usage_count}/1\n"
            f"⏰ So'ngi foydalanish: {last_used_str}"
        )
    else:
        info_text = "📊 Siz hali foydalanmagansiz. Birinchi marta pasport qidiruvingizda ma'lumotlaringiz saqlanadi."
    
    bot.send_message(
        message.chat.id,
        info_text,
        reply_markup=create_main_keyboard()
    )

# Yordam
@bot.message_handler(func=lambda msg: msg.text == "🆘 Yordam")
def help_command(message):
    help_text = (
        "🤖 Botdan foydalanish:\n\n"
        "1. 🔍 Pasport qidirish - pasport raqamingizni kiriting\n"
        "2. ℹ️ Mening ma'lumotlarim - sizning foydalanish statistikangiz\n"
        "3. 🐛 Debug ma'lumot - texnik ma'lumotlar\n\n"
        "📝 Pasport formati: AA1234567\n"
        "🚫 Har bir foydalanuvchi faqat 1 marta foydalana oladi"
    )
    
    bot.send_message(
        message.chat.id,
        help_text,
        reply_markup=create_main_keyboard()
    )

# Debug
@bot.message_handler(func=lambda msg: msg.text == "🐛 Debug ma'lumot")
def debug_info(message):
    try:
        data = load_data()
        
        debug_text = "🔍 DEBUG MA'LUMOTLARI:\n\n"
        debug_text += f"📊 Jadval o'lchami: {data.shape}\n"
        debug_text += f"🔤 Ustunlar soni: {len(data.columns)}\n\n"
        
        debug_text += "📋 USTUNLAR RO'YXATI:\n"
        for i, col in enumerate(data.columns, 1):
            debug_text += f"{i}. '{col}'\n"
        
        if len(data) > 0:
            debug_text += "\n📝 BIRINCHI 3 QATOR:\n"
            for i in range(min(3, len(data))):
                row_text = f"Qator {i+1}: "
                for col in data.columns:
                    value = data.iloc[i][col]
                    if pd.notna(value) and value != "":
                        row_text += f"'{value}' "
                    else:
                        row_text += "NULL "
                debug_text += row_text + "\n"
        else:
            debug_text += "\n📝 Jadvalda ma'lumotlar yo'q"
        
        bot.send_message(message.chat.id, debug_text)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"Debug xatosi: {e}")

# Pasport raqamiga qarab qidirish
@bot.message_handler(func=lambda msg: True)
def check_passport(message):
    if message.text in ["🔍 Pasport qidirish", "ℹ️ Mening ma'lumotlarim", "🆘 Yordam", "🐛 Debug ma'lumot"]:
        return
    
    user_id = message.from_user.id
    
    # Foydalanish cheklovini tekshirish
    if not check_usage_limit(user_id):
        bot.send_message(
            message.chat.id,
            "🚫 Siz faqat 1 marta foydalana olasiz! Bu shaxsiy ma'lumotlarni himoya qilish uchun.",
            reply_markup=create_main_keyboard()
        )
        return
    
    passport = message.text.strip().upper()
    
    # Pasport formatini tekshirish
    if not re.match(r'^[A-Z]{2}\d{7}$', passport):
        bot.send_message(
            message.chat.id, 
            "❌ Noto'g'ri format! Pasport raqami quyidagi formatda bo'lishi kerak: AA1234567",
            reply_markup=create_main_keyboard()
        )
        return

    try:
        bot.send_chat_action(message.chat.id, 'typing')
        data = load_data()
        
        logger.info(f"Qidirilayotgan pasport: {passport}")
        logger.info(f"Ustunlar: {list(data.columns)}")
        
        # Sizning ustunlaringizga mos qidiruv
        if len(data.columns) >= 1 and len(data) > 0:
            passport_column = data.columns[0]  # Birinchi ustun
            logger.info(f"Pasport ustuni: {passport_column}")
            
            # Pasport raqamini qidirish
            data[passport_column] = data[passport_column].fillna('').astype(str)
            row = data[data[passport_column].str.upper() == passport]

            if not row.empty:
                # Foydalanuvchi ma'lumotlarini yangilash
                update_user_usage(message)
                
                # Qolgan ustunlarni aniqlash
                group = "Noma'lum"
                link = "Havola mavjud emas"
                
                if len(data.columns) >= 4:
                    group_value = row.iloc[0][data.columns[3]]
                    group = group_value if pd.notna(group_value) else "Noma'lum"
                
                if len(data.columns) >= 5:
                    link_value = row.iloc[0][data.columns[4]]
                    link = link_value if pd.notna(link_value) else "Havola mavjud emas"
                
                # Ism va fakultet
                ism = "Noma'lum"
                fakultet = "Noma'lum"
                
                if len(data.columns) >= 2:
                    ism_value = row.iloc[0][data.columns[1]]
                    ism = ism_value if pd.notna(ism_value) else "Noma'lum"
                
                if len(data.columns) >= 3:
                    fakultet_value = row.iloc[0][data.columns[2]]
                    fakultet = fakultet_value if pd.notna(fakultet_value) else "Noma'lum"
                
                result_text = (
                    "✅ Ma'lumot topildi!\n\n"
                    f"📋 Pasport: {passport}\n"
                    f"👤 Ism: {ism}\n"
                    f"🏫 Fakultet: {fakultet}\n"
                    f"👥 Guruh: {group}\n"
                    f"🔗 Havola: {link}\n\n"
                    "Yana qayta tekshirishingiz mumkin!"
                )
                bot.send_message(
                    message.chat.id, 
                    result_text,
                    reply_markup=create_main_keyboard()
                )
            else:
                bot.send_message(
                    message.chat.id, 
                    f"❌ {passport} raqami bo'yicha ma'lumot topilmadi.\n\n"
                    "Iltimos, pasport raqamingizni qaytadan tekshiring yoki "
                    "administrator bilan bog'laning.",
                    reply_markup=create_main_keyboard()
                )
        else:
            bot.send_message(
                message.chat.id, 
                "❌ Jadvalda ma'lumotlar topilmadi yoki jadval bo'sh.",
                reply_markup=create_main_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Xatolik: {e}")
        bot.send_message(
            message.chat.id, 
            f"😔 Xatolik yuz berdi: {str(e)[:100]}\n\n"
            "Iltimos, keyinroq qayta urinib ko'ring.",
            reply_markup=create_main_keyboard()
        )

if __name__ == "__main__":
    logger.info("Bot ishga tushdi...")
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Botda xatolik: {e}")
