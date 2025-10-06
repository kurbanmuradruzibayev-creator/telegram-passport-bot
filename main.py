import os
import telebot
import requests
import pandas as pd
import json
import re
import logging

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

        # Ustun nomlari
        cols = [c["label"] for c in data["table"]["cols"]]

        # Qatorlar
        rows = []
        for r in data["table"]["rows"]:
            values = [cell["v"] if cell else "" for cell in r["c"]]
            rows.append(values)

        df = pd.DataFrame(rows, columns=cols)
        logger.info(f"Ma'lumotlar muvaffaqiyatli yuklandi. {len(df)} qator")
        logger.info(f"Ustunlar: {list(df.columns)}")  # Debug uchun
        return df
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Google Sheets ga ulanishda xatolik: {e}")
        raise
    except Exception as e:
        logger.error(f"Ma'lumotlarni o'qishda xatolik: {e}")
        raise

def find_column(df, keywords):
    """Ustun nomida berilgan kalit so'zlarni qidiradi"""
    for col in df.columns:
        if any(keyword in col.lower() for keyword in keywords):
            return col
    return None

# /start komandasi
@bot.message_handler(commands=['start'])
def start(message):
    welcome_text = """
Assalomu alaykum! 👋

Pasport raqamingizni yuboring, men guruhingiz va guruh havolangizni topib beraman.

📝 Pasport raqamini shu formatda yuboring: AA1234567
    """
    bot.send_message(message.chat.id, welcome_text)

# /debug komandasi - ustunlarni tekshirish uchun
@bot.message_handler(commands=['debug'])
def debug_info(message):
    try:
        data = load_data()
        columns_info = "📊 Jadval ustunlari:\n\n"
        for i, col in enumerate(data.columns, 1):
            columns_info += f"{i}. {col}\n"
        
        # Avtomatik topilgan ustunlar
        passport_col = find_column(data, ['pasport', 'passport'])
        group_col = find_column(data, ['guruh', 'group'])
        link_col = find_column(data, ['link', 'havola', 'url'])
        
        columns_info += f"\n🔍 Avtomatik topilgan ustunlar:\n"
        columns_info += f"Pasport: {passport_col if passport_col else 'Topilmadi'}\n"
        columns_info += f"Guruh: {group_col if group_col else 'Topilmadi'}\n"
        columns_info += f"Link: {link_col if link_col else 'Topilmadi'}\n"
        
        bot.send_message(message.chat.id, columns_info)
    except Exception as e:
        bot.send_message(message.chat.id, f"Debug xatosi: {e}")

# Pasport raqamiga qarab qidirish
@bot.message_handler(func=lambda msg: True)
def check_passport(message):
    # /debug komandasini tekshirish
    if message.text.startswith('/'):
        return
    
    passport = message.text.strip().upper()
    
    # Pasport formatini tekshirish
    if not re.match(r'^[A-Z]{2}\d{7}$', passport):
        bot.send_message(
            message.chat.id, 
            "❌ Noto'g'ri format!\n\n" +
            "Pasport raqami quyidagi formatda bo'lishi kerak: AA1234567\n" +
            "📝 Iltimos, qaytadan kiriting:"
        )
        return

    try:
        bot.send_chat_action(message.chat.id, 'typing')
        data = load_data()
        
        # Ustun nomlarini topish
        passport_column = find_column(data, ['pasport', 'passport'])
        group_column = find_column(data, ['guruh', 'group'])
        link_column = find_column(data, ['link', 'havola', 'url'])
        
        logger.info(f"Topilgan ustunlar: pasport={passport_column}, guruh={group_column}, link={link_column}")
        
        if not passport_column:
            error_msg = f"❌ Jadvalda pasport raqami ustuni topilmadi.\n\nMavjud ustunlar:\n"
            for col in data.columns:
                error_msg += f"• {col}\n"
            error_msg += "\n/debug buyrug'i orqali batafsil ma'lumot oling"
            bot.send_message(message.chat.id, error_msg)
            return

        # Pasport raqamini qidirish
        # NaN qiymatlarni tozalash
        data[passport_column] = data[passport_column].fillna('').astype(str)
        row = data[data[passport_column].str.upper() == passport]

        if not row.empty:
            # Guruh va link ustunlarini topish
            group = row.iloc[0][group_column] if group_column and group_column in row.columns and pd.notna(row.iloc[0][group_column]) else "Noma'lum"
            link = row.iloc[0][link_column] if link_column and link_column in row.columns and pd.notna(row.iloc[0][link_column]) else "Havola mavjud emas"
            
            result_text = f"""
✅ Ma'lumot topildi!

📋 Pasport: {passport}
👥 Guruh: {group}
🔗 Havola: {link}

Yana qayta tekshirishingiz mumkin!
            """
            bot.send_message(message.chat.id, result_text)
        else:
            bot.send_message(
                message.chat.id, 
                f"❌ {passport} raqami bo'yicha ma'lumot topilmadi.\n\n" +
                "Iltimos, pasport raqamingizni qaytadan tekshiring yoki " +
                "administrator bilan bog'laning."
            )
            
    except Exception as e:
        logger.error(f"Xatolik: {e}")
        bot.send_message(
            message.chat.id, 
            "😔 Hozirda ma'lumotlar bazasiga ulanib bo'lmadi.\n\n" +
            "Iltimos, keyinroq qayta urinib ko'ring."
        )

if __name__ == "__main__":
    logger.info("Bot ishga tushdi...")
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Botda xatolik: {e}")
