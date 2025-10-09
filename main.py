import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Environment faylidan o'qish
load_dotenv()

# Logging sozlash
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Start komandasi
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await update.message.reply_text(
        f"Salom {user.first_name}! 👋\n"
        f"Menga istalgan matn yuboring, men uni o'qiyman va qaytaram."
    )

# Help komandasi
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 **Bot Buyruqlari:**

/start - Botni ishga tushirish
/help - Yordam olish
/info - Bot haqida ma'lumot

📝 **Qanday ishlaydi:**
Menga istalgan matn yuboring, men uni o'qiyman va qaytaram.
    """
    await update.message.reply_text(help_text)

# Info komandasi
async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info_text = """
ℹ️ **Bot Haqida:**

Bu oddiy Telegram bot
Yaratuvchi: Siz
Dastur: Python
    """
    await update.message.reply_text(info_text)

# Matn messagelarini qayta ishlash
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type = update.message.chat.type
    text = update.message.text
    
    logger.info(f"Foydalanuvchi ({update.message.chat.id}) {message_type} chatida: '{text}'")
    
    # Botning javobi
    response = f"📝 Sizning xabaringiz: {text}\n\n✅ Men bu matnni qabul qildim!"
    
    await update.message.reply_text(response)

# Xatolarni qayta ishlash
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Xatolik yuz berdi: {context.error}")
    
    if update and update.message:
        await update.message.reply_text("❌ Xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring.")

def main():
    # Bot application yaratish
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlerlar
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("info", info_command))
    
    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Botni ishga tushirish
    print("🤖 Bot ishga tushdi...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
