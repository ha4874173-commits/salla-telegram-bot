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
    "free_channel": "https://t.me/c/3907521588/1",
    "private_channel": "https://t.me/c/3953368081/1"
}

app = Flask(__name__)
bot_instance = Bot(token=TOKEN) if TOKEN else None

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
        "مرحباً بك في بوت عزيز التجاري! 🚀\nاختر من الأزرار أدناه للبدء:",
        reply_markup=main_menu_keyboard()
    )

async def check_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(ADMIN_ID):
        return 
    await update.message.reply_text(
        "🔍 **نظام فحص الاشتراكات:**\n"
        "جميع البيانات مسجلة في قناة الأرشيف.\n"
        "يمكنك البحث داخل القناة برقم الجوال أو الاسم."
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == 'get_free_link':
        await query.message.reply_text(f"✅ تفضل رابط القناة المجانية:\n{URLS['free_channel']}")
    elif data == 'menu_spx':
        keyboard = [
            [InlineKeyboardButton("اشتراك شهر", url=URLS["spx_1m"])],
            [InlineKeyboardButton("🔙 عودة", callback_data='back_to_main')]
        ]
        await query.edit_message_text("روابط اشتراك SPX عبر سلة:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == 'back_to_main':
        await query.edit_message_text("اختر خدمتك المفضلة:", reply_markup=main_menu_keyboard())

# --- 3. نظام الويب هوك (إصلاح مكان السطر 132) ---
@app.route('/webhook', methods=['POST'])
def salla_webhook():
    try:
        data = request.json
        event = data.get('event')

        if event in ['subscription.created', 'subscription.charged']:
            customer = data['data'].get('customer', {})
            name = f"{customer.get('first_name')} {customer.get('last_name')}"
            mobile = customer.get('mobile', 'N/A')
            expiry = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            
            log_text = (
                f"📝 **سجل اشتراك جديد**\n"
                f"👤 الاسم: {name}\n"
                f"📱 الجوال: `{mobile}`\n"
                f"📅 ينتهي في: {expiry}\n"
                f"🔗 رابط القناة الخاصة: {URLS['private_channel']}"
            )

            # هنا تم إصلاح المسافات (السطر 132 وما بعده)
            if bot_instance:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                # الإرسال لقناة الأرشيف
                loop.run_until_complete(bot_instance.send_message(chat_id=DATA_CHANNEL_ID, text=log_text, parse_mode='Markdown'))
                # تنبيه فيصل
                loop.run_until_complete(bot_instance.send_message(chat_id=ADMIN_ID, text=f"🔔 تم تأكيد دفع من {name}، راجع الأرشيف.", parse_mode='Markdown'))
                loop.close()

        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# --- 4. تشغيل النظام ---
def run_flask():
    app.run(host='0.0.0.0', port=PORT)

def main():
    if not TOKEN:
        print("❌ TOKEN IS MISSING!")
        return

    threading.Thread(target=run_flask, daemon=True).start()

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("check", check_subscriptions))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("🚀 البوت يعمل الآن بشكل صحيح!")
    application.run_polling()

if __name__ == '__main__':
    main()
