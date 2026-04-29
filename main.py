import logging
import os
import sqlite3
import threading
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# --- 1. الإعدادات ---
TOKEN = '8232201715:AAFEvsg1y3tD8_CXOXx0NT2CsdZU_jw9sN8'
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
tg_application = None # سيتم تعريفه لاحقاً

@flask_app.route('/webhook', methods=['POST'])
def salla_webhook():
    data = request.json
    # التحقق من أن الحدث هو اكتمال الطلب
    if data.get('event') == 'order.updated':
        order_status = data['data']['status']['id']
        if order_status == 'completed':
            customer_name = data['data']['customer']['first_name']
            # هنا نقوم بإنشاء رابط دعوة وإرساله (يتطلب وجود Chat ID للعميل)
            logging.info(f"✅ طلب مكتمل للعميل: {customer_name}")
            # ملاحظة: الويب هوك لا يرسل Telegram ID، لذا العميل يجب أن يفعل البوت يدوياً أولاً
    return jsonify({'status': 'success'}), 200

# --- 3. قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, expiry_date TEXT, trial_used INTEGER)''')
    conn.commit()
    conn.close()

def add_user(user_id, days):
    expiry = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, expiry_date, trial_used) VALUES (?, ?, ?)", 
              (user_id, expiry, 1))
    conn.commit()
    conn.close()

def has_used_trial(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT trial_used FROM users WHERE user_id=?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res is not None

# --- 4. واجهة البوت والتعامل مع الأزرار ---
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
            await query.edit_message_text(f"✅ تم تفعيل التجربة المجانية لـ 7 أيام.\nرابط الدخول للقناة:\n{invite_link.invite_link}")

    elif query.data == 'back_to_main':
        await query.edit_message_text("الرجاء اختيار الخدمة المطلوبة:", reply_markup=main_menu_keyboard())

# --- 5. تشغيل السيرفر والبوت معاً ---
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port)

def main():
    init_db()
    global tg_application
    tg_application = Application.builder().token(TOKEN).build()
    
    tg_application.add_handler(CommandHandler("start", start))
    tg_application.add_handler(CallbackQueryHandler(button_handler))
    
    # تشغيل Flask في خلفية الكود
    threading.Thread(target=run_flask, daemon=True).start()
    
    print("🚀 البوت والويب هوك يعملان الآن...")
    tg_application.run_polling()

if __name__ == '__main__':
    main()
