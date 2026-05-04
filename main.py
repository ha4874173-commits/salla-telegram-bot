import os
import asyncio
import logging
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import threading

# --- 1. الإعدادات ---
TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.environ.get('ADMIN_ID') 
PORT = int(os.environ.get('PORT', 8080))

# الروابط الخاصة بك
URLS = {
    "spx_1m": "https://salla.sa/AZIZSPX/WzbWgKA",
    "spx_3m": "https://salla.sa/AZIZSPX/xvnbrQb",
    "spx_6m": "https://salla.sa/AZIZSPX/azdOBBK",
    "ind_1m": "https://salla.sa/AZIZSPX/EXKwOwZ",
    "support": "https://t.me/ess942",
    "free_channel_link": "https://t.me/+XXXXX", # ضع هنا رابط قناتك المجانية
    "private_channel_link": "https://t.me/+YYYYY" # ضع هنا رابط قناتك الخاصة
}

app = Flask(__name__)
bot_instance = Bot(token=TOKEN)

# --- 2. واجهة البوت ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 اشتراك تحليلات SPX العالمية", callback_data='menu_spx')],
        [InlineKeyboardButton("📈 اشتراك المؤشرات الفنية الخاصة", callback_data='menu_indicators')],
        [InlineKeyboardButton("🆓 الحصول على رابط القناة المجانية", callback_data='get_free_link')],
        [InlineKeyboardButton("💬 التواصل مع الدعم الفني", url=URLS["support"])]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحباً بك في بوت عزيز! 🚀\nاختر من الأزرار أدناه للحصول على الروابط أو الاشتراك:",
        reply_markup=main_menu_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == 'get_free_link':
        # الرد برابط القناة المجانية فوراً عند الضغط على الزرار
        await query.message.reply_text(f"🎁 تفضل رابط القناة المجانية (مدى الحياة):\n{URLS['free_channel_link']}")

    elif data == 'menu_spx':
        keyboard = [
            [InlineKeyboardButton("شهر - 100 ريال", url=URLS["spx_1m"])],
            [InlineKeyboardButton("3 شهور - 279 ريال", url=URLS["spx_3m"])],
            [InlineKeyboardButton("6 شهور - 549 ريال", url=URLS["spx_6m"])],
            [InlineKeyboardButton("🔙 عودة", callback_data='back_to_main')]
        ]
        await query.edit_message_text("اختر الباقة المناسبة للدفع عبر سلة:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'menu_indicators':
        keyboard = [
            [InlineKeyboardButton("Aziz pro مؤشر - 399 ريال", url=URLS["ind_1m"])],
            [InlineKeyboardButton("🔙 عودة", callback_data='back_to_main')]
        ]
        await query.edit_message_text("اشترك في المؤشرات الفنية عبر سلة:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'back_to_main':
        await query.edit_message_text("اختر خدمتك المفضلة:", reply_markup=main_menu_keyboard())

# --- 3. نظام الويب هوك (الإرسال التلقائي بعد التأكد من الاشتراك) ---
@app.route('/webhook', methods=['POST'])
def salla_webhook():
    try:
        data = request.json
        event = data.get('event')

        if event in ['subscription.created', 'subscription.charged']:
            customer = data['data'].get('customer', {})
            customer_name = customer.get('first_name', 'عميل')
            # محاولة الحصول على الـ Telegram ID إذا كان مسجلاً في سلة (أو إرسال لفيصل للمتابعة)
            
            # 1. إرسال تنبيه لفيصل
            alert_for_admin = (
                f"✅ **تم تأكيد اشتراك جديد!**\n"
                f"👤 العميل: {customer_name}\n"
                f"📱 الجوال: {customer.get('mobile')}\n"
                f"💰 الحدث: {event}\n\n"
                f"قم بالتواصل معه لإضافته للقناة الخاصة إذا لم يصله الرابط."
            )
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(bot_instance.send_message(chat_id=ADMIN_ID, text=alert_for_admin, parse_mode='Markdown'))
            loop.close()

        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'status': 'error'}), 500

# --- 4. تشغيل النظام ---
def run_flask():
    app.run(host='0.0.0.0', port=PORT)

def main():
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("🚀 البوت شغال ونظام الروابط التلقائية مفعل...")
    application.run_polling()

if __name__ == '__main__':
    main()
