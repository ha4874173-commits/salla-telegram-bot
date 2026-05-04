import os
import asyncio
import logging
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import threading

# --- 1. الإعدادات (تأكد من إضافتها في Railway Variables) ---
TOKEN = os.getenv("TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID") # آيدي فيصل
PORT = int(os.environ.get('PORT', 8080))

# روابط سلة والدعم
URLS = {
    "spx_1m": "https://salla.sa/AZIZSPX/WzbWgKA",
    "spx_3m": "https://salla.sa/AZIZSPX/xvnbrQb",
    "spx_6m": "https://salla.sa/AZIZSPX/azdOBBK",
    "ind_1m": "https://salla.sa/AZIZSPX/EXKwOwZ",
    "support": "https://t.me/ess942",
    "free_channel": "https://t.me/YourFreeChannel" # حط رابط قناتك المجانية هنا
}

app = Flask(__name__)
# إنشاء نسخة البوت لإرسال التنبيهات التلقائية
bot_instance = Bot(token=TOKEN)

# --- 2. واجهة البوت (الأزرار) ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 اشتراك تحليلات SPX العالمية", callback_data='menu_spx')],
        [InlineKeyboardButton("📈 اشتراك المؤشرات الفنية الخاصة", callback_data='menu_indicators')],
        [InlineKeyboardButton("🆓 القناة المجانية (مدى الحياة)", url=URLS["free_channel"])],
        [InlineKeyboardButton("💬 التواصل مع الدعم الفني", url=URLS["support"])]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحباً بك في بوت عزيز! 🚀\nيمكنك الاشتراك في القنوات أو متابعة القناة المجانية أدناه:",
        reply_markup=main_menu_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == 'menu_spx':
        keyboard = [
            [InlineKeyboardButton("شهر - 100 ريال", url=URLS["spx_1m"])],
            [InlineKeyboardButton("3 شهور - 279 ريال", url=URLS["spx_3m"])],
            [InlineKeyboardButton("6 شهور - 549 ريال", url=URLS["spx_6m"])],
            [InlineKeyboardButton("🔙 عودة", callback_data='back_to_main')]
        ]
        await query.edit_message_text("اختر مدة الاشتراك للدفع عبر سلة:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'menu_indicators':
        keyboard = [
            [InlineKeyboardButton("Aziz pro مؤشر - 399 ريال", url=URLS["ind_1m"])],
            [InlineKeyboardButton("🔙 عودة", callback_data='back_to_main')]
        ]
        await query.edit_message_text("اشترك في المؤشرات الفنية عبر سلة:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'back_to_main':
        await query.edit_message_text("اختر خدمتك المفضلة:", reply_markup=main_menu_keyboard())

# --- 3. نظام الويب هوك (تأكيد الاشتراك التلقائي من سلة) ---
@app.route('/webhook', methods=['POST'])
def salla_webhook():
    try:
        data = request.json
        event = data.get('event')

        # رصد المشتركين الجدد أو تجديد الاشتراك
        if event in ['subscription.created', 'subscription.charged']:
            customer = data['data'].get('customer', {})
            full_name = f"{customer.get('first_name', 'عميل')} {customer.get('last_name', '')}"
            mobile = customer.get('mobile', 'غير مسجل')
            
            status_text = "✨ مشترك جديد" if event == 'subscription.created' else "💰 تجديد اشتراك"
            
            alert_msg = (
                f"🔔 **تنبيه من سلة: {status_text}**\n\n"
                f"👤 الاسم: {full_name}\n"
                f"📱 الجوال: `{mobile}`\n"
                f"📝 الحدث: {event}\n\n"
                f"✅ تم الدفع بنجاح عبر سلة."
            )

            # إرسال التنبيه لفيصل
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(bot_instance.send_message(chat_id=ADMIN_ID, text=alert_msg, parse_mode='Markdown'))
            loop.close()

        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# --- 4. تشغيل البوت والسيرفر معاً ---
def run_flask():
    app.run(host='0.0.0.0', port=PORT)

def main():
    # تشغيل Flask في Thread منفصل عشان ما يعطلش البوت
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # تشغيل بوت تليجرام
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("🚀 البوت والويب هوك يعملان معاً...")
    application.run_polling()

if __name__ == '__main__':
    main()
