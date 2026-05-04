import os
import asyncio
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- 1. الإعدادات ---
TOKEN = os.getenv("TOKEN") or os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
DATA_CHANNEL_ID = "-1003970062260" 
PORT = int(os.environ.get('PORT', 8080))

URLS = {
    "spx_1m": "https://salla.sa/AZIZSPX/WzbWgKA",
    "spx_3m": "https://salla.sa/AZIZSPX/xvnbrQb",
    "spx_6m": "https://salla.sa/AZIZSPX/azdOBBK",
    "ind_1m": "https://salla.sa/AZIZSPX/EXKwOwZ",
    "support": "https://t.me/ess942",
    "free_channel": "https://t.me/#-3907521588", # ضع رابط قناتك المجانية هنا
    "private_channel": "https://t.me/#-3953368081" # ضع رابط قناتك الخاصة هنا
}

app = Flask(__name__)
bot_instance = Bot(token=TOKEN) if TOKEN else None

# --- 2. أزرار الواجهة ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 اشتراك تحليلات SPX العالمية", callback_data='menu_spx')],
        [InlineKeyboardButton("📈 اشتراك المؤشرات الفنية الخاصة", callback_data='menu_indicators')],
        [InlineKeyboardButton("🆓 القناة المجانية (مدى الحياة)", url=URLS["free_channel"])],
        [InlineKeyboardButton("💬 التواصل مع الدعم الفني", url=URLS["support"])]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً بك في بوت عزيز التجاري! 🚀", reply_markup=main_menu_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == 'menu_spx':
        keyboard = [
            [InlineKeyboardButton("🗓️ باقة شهر - 100 ريال", url=URLS["spx_1m"])],
            [InlineKeyboardButton("🗓️ باقة 3 شهور - 279 ريال", url=URLS["spx_3m"])],
            [InlineKeyboardButton("🗓️ باقة 6 شهور - 549 ريال", url=URLS["spx_6m"])],
            [InlineKeyboardButton("🔙 عودة", callback_data='back_to_main')]
        ]
        await query.edit_message_text("اختر باقة SPX المناسبة للدفع عبر سلة:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == 'menu_indicators':
        keyboard = [
            [InlineKeyboardButton("📈 مؤشر Aziz Pro - 399 ريال", url=URLS["ind_1m"])],
            [InlineKeyboardButton("🔙 عودة", callback_data='back_to_main')]
        ]
        await query.edit_message_text("اشتراك المؤشرات الخاصة:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'back_to_main':
        await query.edit_message_text("اختر خدمتك المفضلة:", reply_markup=main_menu_keyboard())

# --- 3. الويب هوك وتأكيد الدفع ---
@app.route('/webhook', methods=['POST'])
def salla_webhook():
    try:
        data = request.json
        if data.get('event') in ['subscription.created', 'subscription.charged']:
            customer = data['data'].get('customer', {})
            name = f"{customer.get('first_name')} {customer.get('last_name')}"
            mobile = customer.get('mobile', 'N/A')
            expiry = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            
            log_text = f"📝 **دفع جديد مؤكد**\n👤 الاسم: {name}\n📱 الجوال: `{mobile}`\n📅 انتهاء الصلاحية المتوقع: {expiry}"

            if bot_instance:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(bot_instance.send_message(chat_id=DATA_CHANNEL_ID, text=log_text))
                loop.run_until_complete(bot_instance.send_message(chat_id=ADMIN_ID, text=f"🔔 إشعار: تم دفع اشتراك جديد من {name}"))
                loop.close()
        return jsonify({'status': 'success'}), 200
    except:
        return jsonify({'status': 'error'}), 500

# --- 4. التشغيل ---
def main():
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT), daemon=True).start()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling()

if __name__ == '__main__':
    main()
