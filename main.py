import logging
import os
import sqlite3
import threading
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# --- 1. الإعدادات ---
TOKEN = '8232201715:AAFEvsg1y3tD8_CXOXx0NT2CsdZU_jw9sN8'
SALLA_TOKEN = 'ea8d83f12f8260155ab87809c4ee4e70c3099b06d93852a23d7c72451d9d89ad'
CHANNEL_ID = '-1003953368081'

URLS = {
    "spx_1m": "https://salla.sa/AZIZSPX/WzbWgKA",
    "spx_3m": "https://salla.sa/AZIZSPX/xvnbrQb",
    "spx_6m": "https://salla.sa/AZIZSPX/azdOBBK",
    "ind_1m": "https://salla.sa/AZIZSPX/EXKwOwZ",
    "support": "https://t.me/ess942"
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- 2. إعداد Flask لاستقبال الويب هوك ---
flask_app = Flask(__name__)

@flask_app.route('/webhook', methods=['POST'])
def salla_webhook():
    data = request.json
    if data.get('event') == 'order.updated' and data['data']['status']['id'] == 'completed':
        logging.info(f"✅ طلب جديد مكتمل رقم: {data['data']['id']}")
    return jsonify({'status': 'success'}), 200

# --- 3. قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, expiry_date TEXT, trial_used INTEGER)''')
    conn.commit()
    conn.close()

def add_user(user_id, days):
    expiry = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, expiry_date, trial_used) VALUES (?, ?, ?)", (user_id, expiry, 1))
    conn.commit()
    conn.close()

def has_used_trial(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT trial_used FROM users WHERE user_id=?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res is not None

# --- 4. التحقق من سلة ---
def verify_salla_order(order_id):
    headers = {'Authorization': f'Bearer {SALLA_TOKEN}', 'Content-Type': 'application/json'}
    try:
        response = requests.get(f'https://api.salla.dev/admin/v2/orders/{order_id}', headers=headers)
        if response.status_code == 200:
            status = response.json()['data']['status']['id']
            return status in ['completed', 'delivered']
        return False
    except:
        return False

# --- 5. واجهة البوت والتعامل مع الأزرار ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 اشتراك تحليلات SPX العالمية 📊", callback_data='menu_spx')],
        [InlineKeyboardButton("📈 اشتراك المؤشرات الفنية الخاصة 📈", callback_data='menu_indicators')],
        [InlineKeyboardButton("🎁 تجربة مجانية (7 أيام) 🎁", callback_data='free_trial')],
        [InlineKeyboardButton("✅ تأكيد الدفع (رقم الطلب) ✅", callback_data='verify_payment')],
        [InlineKeyboardButton("💬 التواصل مع الدعم الفني 💬", url=URLS["support"])]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً بك في بوت عزيز! 🚀\nالرجاء اختيار الخدمة المطلوبة:", reply_markup=main_menu_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == 'free_trial':
        if has_used_trial(user_id):
            await query.edit_message_text("❌ عذراً، لقد استخدمت الفترة التجريبية مسبقاً.")
        else:
            add_user(user_id, 7)
            invite_link = await context.bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
            await query.edit_message_text(f"✅ تم تفعيل التجربة المجانية لـ 7 أيام.\nرابط القناة:\n{invite_link.invite_link}")

    elif query.data == 'menu_spx':
        keyboard = [
            [InlineKeyboardButton("شهر - 100 ريال", url=URLS["spx_1m"])],
            [InlineKeyboardButton("3 شهور - 279 ريال", url=URLS["spx_3m"])],
            [InlineKeyboardButton("6 شهور - 549 ريال", url=URLS["spx_6m"])],
            [InlineKeyboardButton("🔙 عودة", callback_data='back_to_main')]
        ]
        await query.edit_message_text("اختر مدة اشتراك تحليل SPX:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'menu_indicators':
        keyboard = [
            [InlineKeyboardButton("Aziz pro مؤشر - 399 ريال", url=URLS["ind_1m"])],
            [InlineKeyboardButton("🔙 عودة", callback_data='back_to_main')]
        ]
        await query.edit_message_text("اختر مدة اشتراك المؤشرات الفنية:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'verify_payment':
        context.user_data['waiting_for_order'] = True
        await query.edit_message_text("أرسل رقم الطلب من سلة للتحقق:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data='back_to_main')]]))

    elif query.data == 'back_to_main':
        context.user_data['waiting_for_order'] = False
        await query.edit_message_text("الرجاء اختيار الخدمة المطلوبة:", reply_markup=main_menu_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_for_order'):
        order_id = update.message.text.strip()
        if order_id.isdigit():
            await update.message.reply_text("جاري التحقق من سلة... ⏳")
            if verify_salla_order(order_id):
                invite_link = await context.bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
                await update.message.reply_text(f"✅ تم التحقق! اشتراكك مفعل.\nرابط القناة:\n{invite_link.invite_link}")
            else:
                await update.message.reply_text("❌ لم نجد طلباً مكتملاً بهذا الرقم.")
        context.user_data['waiting_for_order'] = False

# --- 6. تشغيل السيرفر ---
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port)

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    threading.Thread(target=run_flask, daemon=True).start()
    app.run_polling()

if __name__ == '__main__':
    main()
