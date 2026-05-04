import os
import asyncio
import logging
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- 1. الإعدادات الجاهزة ---
# الكود يسحب التوكن والآيدي من إعدادات Railway Variables تلقائياً
TOKEN = os.getenv("TOKEN") or os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID") # آيدي فيصل
DATA_CHANNEL_ID = os.getenv("DATA_CHANNEL_ID") # آيدي قناة تخزين البيانات (مثال: -100123456789)
PORT = int(os.environ.get('PORT', 8080))

# الروابط الخاصة بالمتجر والقنوات
URLS = {
    "spx_1m": "https://salla.sa/AZIZSPX/WzbWgKA",
    "spx_3m": "https://salla.sa/AZIZSPX/xvnbrQb",
    "spx_6m": "https://salla.sa/AZIZSPX/azdOBBK",
    "ind_1m": "https://salla.sa/AZIZSPX/EXKwOwZ",
    "support": "https://t.me/ess942",
    "free_channel": "https://t.me/+XXXXXXX",    # ⚠️ استبدله برابط قناتك المجانية
    "private_channel": "https://t.me/+YYYYYYY"  # ⚠️ استبدله برابط قناتك الخاصة
}

app = Flask(__name__)
bot_instance = Bot(token=TOKEN) if TOKEN else None

# --- 2. أزرار البوت (الواجهة) ---
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
        "مرحباً بك في بوت عزيز! 🚀\nاختر من الأزرار أدناه للبدء:",
        reply_markup=main_menu_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == 'get_free_link':
        await query.message.reply_text(f"✅ تفضل رابط القناة المجانية (مدى الحياة):\n{URLS['free_channel']}")

    elif data == 'menu_spx':
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

# --- 3. نظام الويب هوك (سلة + قناة البيانات) ---
@app.route('/webhook', methods=['POST'])
def salla_webhook():
    try:
        data = request.json
        event = data.get('event')

        if event in ['subscription.created', 'subscription.charged']:
            customer = data['data'].get('customer', {})
            name = f"{customer.get('first_name', 'عميل')} {customer.get('last_name', '')}"
            mobile = customer.get('mobile', 'N/A')
            
            # حساب تاريخ انتهاء الاشتراك (بعد 30 يوم)
            expiry_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            
            # رسالة سجل البيانات للقناة الخاصة
            db_log = (
                f"📝 **اشتراك جديد/مجدد**\n"
                f"👤 الاسم: {name}\n"
                f"📱 الجوال: `{mobile}`\n"
                f"📅 ينتهي في: {expiry_date}\n"
                f"⚙️ النوع: {event}"
            )

            if bot_instance:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                # 1. إرسال لقناة البيانات (الأرشيف)
                if DATA_CHANNEL_ID:
                    loop.run_until_complete(bot_instance.send_message(chat_id=DATA_CHANNEL_ID, text=db_log, parse_mode='Markdown'))
                # 2. إرسال تنبيه لفيصل (الأدمن)
                loop.run_until_complete(bot_instance.send_message(chat_id=ADMIN_ID, text=f"🔔 تم تأكيد دفع من {name}\nراجع قناة البيانات للتواريخ.", parse_mode='Markdown'))
                loop.close()

        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# --- 4. تشغيل السيرفر والبوت ---
def run_flask():
    app.run(host='0.0.0.0', port=PORT)

def main():
    if not TOKEN:
        print("❌ TOKEN missing!")
        return

    # تشغيل سيرفر الويب هوك في Thread منفصل
    threading.Thread(target=run_flask, daemon=True).start()

    # تشغيل البوت
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("🚀 البوت والسيستم شغالين تمام...")
    application.run_polling()

if __name__ == '__main__':
    main()
