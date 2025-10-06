import os
import telebot
import requests
import pandas as pd
import json
import re
import logging
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

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

def create_main_keyboard():
    """Asosiy keyboard yaratish"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    keyboard.add(
        KeyboardButton("🔍 Pasport qidirish"),
        KeyboardButton("ℹ️ Mening ma'lumotlarim")
    )
    keyboard.add(
        KeyboardButton("🆘 Yordam"),
        KeyboardButton("📞 INFO")
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

# INFO tugmasi - universitet haqida ma'lumot
@bot.message_handler(func=lambda msg: msg.text == "📞 INFO")
def info_command(message):
    info_text = (
        "🏫 CYBER UNIVERSITY\n\n"
        "📞 Murojaatlar uchun: 558885555\n\n"
        "🌐 Ijtimoiy tarmoqlar:\n\n"
        "📲 Telegram: https://t.me/cyberuni_uz\n"
        "🌐 Veb-sayt: csu.uz\n"
        "📸 Instagram: instagram.com/csu.uz\n"
        "📘 Facebook: www.facebook.com/profile.php?id=61577521082631\n"
        "💼 LinkedIn: www.linkedin.com/company/csu_uz/\n"
        "📚 Kutubxona: https://t.me/CYBERUNI_LIBRARY\n\n"
        "📍 Manzil: Toshkent shahar\n"
        "🎓 Talabalar soni: 5000+\n"
        "👨‍🏫 O'qituvchilar soni: 200+"
    )
    
    bot.send_message(
        message.chat.id,
        info_text,
        reply_markup=create_main_keyboard()
    )

# Mening ma'lumotlarim tugmasi
@bot.message_handler(func=lambda msg: msg.text == "ℹ️ Mening ma'lumotlarim")
def user_info(message):
    info_text = (
        "📊 Siz hali foydalanmagansiz.\n\n"
        "Birinchi marta pasport qidiruvingizda ma'lumotlaringiz saqlanadi.\n"
        "🔍 Pasport qidirish tugmasini bosing va pasport raqamingizni yuboring."
    )
    
    bot.send_message(
        message.chat.id,
        info_text,
        reply_markup=create_main_keyboard()
    )

# Yordam tugmasi
@bot.message_handler(func=lambda msg: msg.text == "🆘 Yordam")
def help_command(message):
    help_text = (
        "🤖 Botdan foydalanish:\n\n"
        "1. 🔍 Pasport qidirish - pasport raqamingizni kiriting\n"
        "2. ℹ️ Mening ma'lumotlarim - sizning foydalanish statistikangiz\n"
        "3. 📞 INFO - universitet haqida batafsil ma'lumot\n\n"
        "📝 Pasport formati: AA1234567\n"
        "🚫 Diqqat: Har bir foydalanuvchi faqat 1 marta foydalana oladi\n\n"
        "❓ Savollar bo'lsa: 558885555"
    )
    
    bot.send_message(
        message.chat.id,
        help_text,
        reply_markup=create_main_keyboard()
    )

# Pasport raqamiga qarab qidirish
@bot.message_handler(func=lambda msg: True)
def check_passport(message):
    if message.text in ["🔍 Pasport qidirish", "ℹ️ Mening ma'lumotlarim", "🆘 Yordam", "📞 INFO"]:
        return
    
    passport = message.text.strip().upper()
    
    # Pasport formatini tekshirish
    if not re.match(r'^[A-Z]{2}\d{7}$', passport):
        bot.send_message(
            message.chat.id, 
            "❌ Noto'g'ri format!\n\n"
            "Pasport raqami quyidagi formatda bo'lishi kerak: AA1234567\n\n"
            "Iltimos, qaytadan kiriting:",
            reply_markup=create_main_keyboard()
        )
        return

    try:
        bot.send_chat_action(message.chat.id, 'typing')
        data = load_data()
        
        # Sizning ustunlaringizga mos qidiruv
        if len(data.columns) >= 1 and len(data) > 0:
            passport_column = data.columns[0]  # Birinchi ustun
            
            # Pasport raqamini qidirish
            data[passport_column] = data[passport_column].fillna('').astype(str)
            row = data[data[passport_column].str.upper() == passport]

            if not row.empty:
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
                    "🎓 CYBER UNIVERSITY da o'qishingiz bilan tabriklaymiz!"
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
