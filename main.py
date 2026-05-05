import logging
import os
import asyncio
import threading
import sqlite3
from datetime import datetime, timedelta
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 1. الإعدادات والمعرفات ---
TOKEN = os.getenv("TOKEN") or os.getenv("BOT_TOKEN")
ADMIN_ID = 5332562107 

PRIVATE_CHANNEL_ID = '-1003953368081' 
FREE_CHANNEL_URL = 'https://t.me/c/3907521588/1' 
REQUESTS_CHANNEL_ID = '-1003846832363' 
ARCHIVE_CHANNEL_ID = '-1003989339996'  

PORT = int(os.environ.get('PORT', 8080))

URLS = {
    "spx_1m": "https://salla.sa/AZIZSPX/WzbWgKA",
    "spx_3m": "https://salla.sa/AZIZSPX/xvnbrQb",
    "spx_6m": "https://salla.sa/AZIZSPX/azdOBBK",
    "ind_1m": "https://salla.sa/AZIZSPX/EXKwOwZ",
    "whatsapp_support": "https://wa.me/+966554852681" 
}

# --- 2. إدارة قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('aziz_trading.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS subscribers 
                 (user_id INTEGER PRIMARY KEY, name TEXT, expiry_date TEXT, notified INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def add_subscriber(user_id, name, expiry_date):
    conn = sqlite3.connect('aziz_trading.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO subscribers (user_id, name, expiry_date, notified) VALUES (?, ?, ?, 0)", 
              (user_id, name, expiry_date))
    conn.commit()
    conn.close()

# --- 3. إعداد Flask وLogging ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
app_flask = Flask(__name__)

# --- 4. لوحة المفاتيح الرئيسية ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 اشتراك تحليلات SPX الخاصة  ", callback_data='menu_spx')],
        [InlineKeyboardButton("📈 اشتراك المؤشرات الفنية الخاصة ", callback_data='menu_indicators')],
        [InlineKeyboardButton("🆓      القناة المجانية        ", url=FREE_CHANNEL_URL)],
        [InlineKeyboardButton("✅     أرسل إثبات الدفع      ", callback_data='upload_proof')],
        [InlineKeyboardButton("💬       الدعم الفني        ", url=URLS["whatsapp_support"])]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- 5. المهام التلقائية (تنبيه + طرد) ---
async def daily_check_job(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('aziz_trading.db')
    c = conn.cursor()
    now = datetime.now()
    now_str = now.strftime('%Y-%m-%d %H:%M')
    
    # أ- تنبيه قبل 48 ساعة
    threshold_48h = (now + timedelta(hours=48)).strftime('%Y-%m-%d %H:%M')
    c.execute("SELECT user_id, name, expiry_date FROM subscribers WHERE expiry_date <= ? AND notified = 0", (threshold_48h,))
    to_notify = c.fetchall()
    for user in to_notify:
        try:
            await context.bot.send_message(chat_id=user[0], text=f"⚠️ تذكير: اشتراكك ينتهي بتاريخ {user[2]}. يرجى التجديد لتجنب الخروج التلقائي.")
            c.execute("UPDATE subscribers SET notified = 1 WHERE user_id = ?", (user[0],))
        except: pass

    # ب- طرد من انتهى اشتراكهم
    c.execute("SELECT user_id, name FROM subscribers WHERE expiry_date <= ?", (now_str,))
    to_kick = c.fetchall()
    for user in to_kick:
        uid, name = user[0], user[1]
        try:
            await context.bot.ban_chat_member(chat_id=PRIVATE_CHANNEL_ID, user_id=uid)
            await context.bot.unban_chat_member(chat_id=PRIVATE_CHANNEL_ID, user_id=uid) # لتمكينه من العودة مستقبلاً
            await context.bot.send_message(chat_id=uid, text="❌ انتهى اشتراكك وتمت إزالتك من القناة. ننتظر عودتك بالتجديد!")
            await context.bot.send_message(chat_id=ARCHIVE_CHANNEL_ID, text=f"🚫 خروج تلقائي: {name} ({uid})")
            c.execute("DELETE FROM subscribers WHERE user_id = ?", (uid,))
        except: pass
        
    conn.commit()
    conn.close()

# --- 6. الأوامر والمعالجات ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "🚀 مرحبًا بك في بوت AZIZ Trading\n\n"
        "📊 بوابتك إلى تداول أكثر احترافية وقرارات مبنية على تحليل دقيق لحركة السوق \n\n"
        "📈 اختر من الأزرار أدناه للوصول إلى خدماتنا وابدأ رحلتك الآن"
    )
    await update.message.reply_text(welcome_message, reply_markup=main_menu_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == 'back_to_main':
        context.user_data['waiting_for_proof'] = False
        await query.edit_message_text("الرئيسية 🏠\n 📈 اختر من الأزرار أدناه للوصول إلى خدماتنا وابدأ رحلتك الآن :", reply_markup=main_menu_keyboard())

    elif data == 'menu_spx':
        keyboard = [[InlineKeyboardButton("شهر - 100 ريال", url=URLS["spx_1m"])],
                    [InlineKeyboardButton("3 شهور - 279 ريال", url=URLS["spx_3m"])],
                    [InlineKeyboardButton("6 شهور - 549 ريال", url=URLS["spx_6m"])],
                    [InlineKeyboardButton("✅ أرسل إثبات الدفع", callback_data='upload_proof')],
                    [InlineKeyboardButton("🔙 العودة", callback_data='back_to_main')]]
        await query.edit_message_text("باقات SPX 📊\nاختر المدة للدفع عبر سلة ثم أرسل الإثبات هنا:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'menu_indicators':
        keyboard = [[InlineKeyboardButton("Aziz pro مؤشر - 399 ريال", url=URLS["ind_1m"])],
                    [InlineKeyboardButton("✅ أرسل إثبات الدفع", callback_data='upload_proof')],
                    [InlineKeyboardButton("🔙 العودة", callback_data='back_to_main')]]
        await query.edit_message_text("المؤشرات الفنية 📈\nادفع عبر الرابط ثم أرسل الإثبات للمراجعة:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'upload_proof':
        context.user_data['waiting_for_proof'] = True
        keyboard = [[InlineKeyboardButton("🔙 إلغاء والعودة للرئيسية", callback_data='back_to_main')]]
        await query.edit_message_text("بانتظار الإثبات ⏳\nمن فضلك أرسل الآن رقم الطلب أو صورة الإيصال هنا:", reply_markup=InlineKeyboardMarkup(keyboard))
            
    elif data.startswith('approve_'):
        if query.from_user.id != ADMIN_ID: return
        parts = data.split('_')
        days, cust_id = int(parts[1]), int(parts[2])
        expiry_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M')
        
        try:
            invite = await context.bot.create_chat_invite_link(chat_id=PRIVATE_CHANNEL_ID, member_limit=1)
            await context.bot.send_message(chat_id=cust_id, text=f"🎉 تم تفعيل اشتراكك!\nالرابط: {invite.invite_link}\nينتهي في: {expiry_date}")
            
            member = await context.bot.get_chat(cust_id)
            name = f"{member.first_name} {member.last_name or ''}"
            add_subscriber(cust_id, name, expiry_date) # حفظ في قاعدة البيانات

            archive_msg = f"✅ **مشترك جديد**\n👤 الاسم: {name}\n🆔 الآيدي: `{cust_id}`\n📅 الانتهاء: `{expiry_date}`"
            await context.bot.send_message(chat_id=ARCHIVE_CHANNEL_ID, text=archive_msg, parse_mode='Markdown')
            await query.edit_message_text(f"✅ تم تفعيل {name}.")
        except Exception as e:
            await query.edit_message_text(f"⚠️ خطأ: {str(e)}")

    elif data.startswith('reject_'):
        if query.from_user.id != ADMIN_ID: return
        cust_id = int(data.split('_')[1])
        await context.bot.send_message(chat_id=cust_id, text="❌ نعتذر، لم يتم تأكيد الدفع.")
        await query.edit_message_text(f"❌ تم رفض الطلب للآيدي {cust_id}.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_for_proof'):
        user = update.effective_user
        admin_kb = [[InlineKeyboardButton("✅ 30 يوم", callback_data=f"approve_30_{user.id}"),
                     InlineKeyboardButton("✅ 90 يوم", callback_data=f"approve_90_{user.id}"),
                     InlineKeyboardButton("✅ 180 يوم", callback_data=f"approve_180_{user.id}")],
                    [InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user.id}")]]
        
        caption = f"🔔 إثبات جديد من {user.first_name}\n🆔 الآيدي: `{user.id}`"
        if update.message.photo:
            await context.bot.send_photo(chat_id=REQUESTS_CHANNEL_ID, photo=update.message.photo[-1].file_id, caption=caption, reply_markup=InlineKeyboardMarkup(admin_kb))
        else:
            await context.bot.send_message(chat_id=REQUESTS_CHANNEL_ID, text=f"{caption}\n📝 المحتوى: {update.message.text}", reply_markup=InlineKeyboardMarkup(admin_kb))
        
        await update.message.reply_text("⏳ تم الإرسال. انتظر رسالة التفعيل هنا.")
        context.user_data['waiting_for_proof'] = False

# --- 7. تشغيل البوت ---
@app_flask.route('/')
def home(): return "Bot is Online"

def main():
    init_db()
    threading.Thread(target=lambda: app_flask.run(host='0.0.0.0', port=PORT), daemon=True).start()
    
    application = Application.builder().token(TOKEN).build()
    
    # فحص التنبيه والطرد كل ساعة
    application.job_queue.run_repeating(daily_check_job, interval=3600, first=10)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.run_polling()

if __name__ == '__main__':
    main()
