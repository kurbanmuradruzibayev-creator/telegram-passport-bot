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
        "📝 Pasport raqamini shu formatda yuboring: AA1234567\n\n"
        "Misol: AD9829103"
    )
    bot.send_message(message.chat.id, welcome_text)

# /debug komandasi
@bot.message_handler(commands=['debug'])
def debug_info(message):
    try:
        data = load_data()
        
        debug_text = "🔍 DEBUG MA'LUMOTLARI:\n\n"
        debug_text += f"📊 Jadval o'lchami: {data.shape}\n"
        debug_text += f"🔤 Ustunlar soni: {len(data.columns)}\n\n"
        
        debug_text += "📋 USTUNLAR RO'YXATI:\n"
        for i, col in enumerate(data.columns, 1):
            debug_text += f"{i}. '{col}'\n"
        
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
        
        bot.send_message(message.chat.id, debug_text)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"Debug xatosi: {e}")

# Pasport raqamiga qarab qidirish
@bot.message_handler(func=lambda msg: True)
def check_passport(message):
    if message.text.startswith('/'):
        return
    
    passport = message.text.strip().upper()
    
    # Pasport formatini tekshirish
    if not re.match(r'^[A-Z]{2}\d{7}$', passport):
        error_msg = (
            "❌ Noto'g'ri format!\n\n"
            "Pasport raqami quyidagi formatda bo'lishi kerak: AA1234567\n\n"
            "📝 Misol: AD9829103\n"
            "Iltimos, qaytadan kiriting:"
        )
        bot.send_message(message.chat.id, error_msg)
        return

    try:
        bot.send_chat_action(message.chat.id, 'typing')
        data = load_data()
        
        logger.info(f"Qidirilayotgan pasport: {passport}")
        logger.info(f"Ustunlar: {list(data.columns)}")
        
        # Sizning ustunlaringizga mos qidiruv
        # Birinchi ustun "Pasport raqami" deb faraz qilamiz
        if len(data.columns) >= 1:
            passport_column = data.columns[0]  # Birinchi ustun
            logger.info(f"Pasport ustuni: {passport_column}")
            
            # Pasport raqamini qidirish
            data[passport_column] = data[passport_column].fillna('').astype(str)
            row = data[data[passport_column].str.upper() == passport]

            if not row.empty:
                # Qolgan ustunlarni aniqlash
                group = "Noma'lum"
                link = "Havola mavjud emas"
                
                # Ikkinchi ustun "To'liq ismi", uchinchi "Fakultet", 
                # to'rtinchi "Guruh", beshinchi "GURUH LINKI" deb faraz qilamiz
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
                bot.send_message(message.chat.id, result_text)
            else:
                bot.send_message(
                    message.chat.id, 
                    f"❌ {passport} raqami bo'yicha ma'lumot topilmadi.\n\n"
                    "Iltimos, pasport raqamingizni qaytadan tekshiring yoki "
                    "administrator bilan bog'laning."
                )
        else:
            bot.send_message(message.chat.id, "❌ Jadvalda ma'lumotlar topilmadi.")
            
    except Exception as e:
        logger.error(f"Xatolik: {e}")
        error_message = (
            f"😔 Xatolik yuz berdi: {str(e)[:100]}\n\n"
            "Iltimos, keyinroq qayta urinib ko'ring yoki /debug buyrug'i bilan tekshiring."
        )
        bot.send_message(message.chat.id, error_message)

if __name__ == "__main__":
    logger.info("Bot ishga tushdi...")
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Botda xatolik: {e}")
