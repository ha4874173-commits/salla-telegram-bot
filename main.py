import logging
import os
import requests
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- 1. الإعدادات ---
TOKEN = '8232201715:AAFEvsg1y3tD8_CXOXx0NT2CsdZU_jw9sN8'
SALLA_TOKEN = 'حط_هنا_التوكن_اللي_هيبعته_فيصل' 
CHANNEL_ID = '-1002462310103'

URLS = {
    "spx_1m": "https://salla.sa/AZIZSPX/WzbWgKA",
    "spx_3m": "https://salla.sa/AZIZSPX/xvnbrQb",
    "spx_6m": "https://salla.sa/AZIZSPX/azdOBBK",
    "spx_1y": "https://salla.sa/spx-1-year",
    "ind_1m": "https://salla.sa/indicators-1-months",
    "ind_3m": "https://salla.sa/indicators-3-months",
    "ind_6m": "https://salla.sa/indicators-6-months",
    "ind_1y": "https://salla.sa/AZIZSPX/EXKwOwZ",
    "support": "https://t.me/your_support_username"
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- 2. قاعدة البيانات ---
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

# --- 3. نظام الطرد التلقائي ---
async def check_expirations(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE expiry_date <= ?", (now,))
    expired_users = c.fetchall()
    conn.close()

    for (user_id,) in expired_users:
        try:
            await context.bot.ban_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            await context.bot.unban_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            await context.bot.send_message(chat_id=user_id, text="⚠️ انتهت فترة التجربة المجانية 7 أيام. للاستمرار بالقناة يرجى الاشتراك.")
            
            # مسح المستخدم من الداتابيز بعد الطرد عشان ميفضلش يطرده كل دقيقة
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE user_id=?", (user_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"Error kicking {user_id}: {e}")

# --- 4. واجهة البوت ---
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
    await update.message.reply_text(
        "مرحباً بك في بوت خدماتنا التقنية! 🚀\nالرجاء اختيار الخدمة المطلوبة:",
        reply_markup=main_menu_keyboard()
    )
    
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
        await query.edit_message_text("اختر الخدمة المطلوبة:", reply_markup=main_menu_keyboard())

    # (بقية الأكواد الخاصة بـ menu_spx و menu_indicators والعودة زي الكود السابق)
    elif query.data == 'menu_spx':
        keyboard = [
            [InlineKeyboardButton("شهر - 100 ريال", url=URLS["spx_1m"])],
            [InlineKeyboardButton("3 شهور - 379 ريال", url=URLS["spx_3m"])],
            [InlineKeyboardButton("6 شهور - 549 ريال", url=URLS["spx_6m"])],
            [InlineKeyboardButton("🔙 عودة", callback_data='back_to_main')]
        ]
        await query.edit_message_text("اشتراكات تحليل SPX:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == 'menu_indicators':
        keyboard = [
            [InlineKeyboardButton(" مؤشر Aziz pro  - 399 ريال", url=URLS["ind_1y"])],
            [InlineKeyboardButton("🔙 عودة", callback_data='back_to_main')]
        ]
        await query.edit_message_text("اشتراكات المؤشرات الفنية:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'verify_payment':
        context.user_data['waiting_for_order'] = True
        await query.edit_message_text("أرسل رقم الطلب من سلة للتحقق:")

# (نفس دالة handle_message و verify_salla_order من الكود السابق مع إضافة المشترك المدفوع للداتابيز بمدته)

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    
    # تشغيل فحص انتهاء الاشتراك كل ساعة
    job_queue = app.job_queue
    job_queue.run_repeating(check_expirations, interval=3600, first=10)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    # (إضافة بقية الـ handlers)
    
    app.run_polling()

if __name__ == '__main__':
    main()
