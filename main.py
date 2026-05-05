import logging
import os
import asyncio
import threading
import sqlite3 # إضافة قاعدة بيانات
from datetime import datetime, timedelta
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

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

# --- إعداد قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS subscribers 
                 (user_id INTEGER PRIMARY KEY, name TEXT, expiry_date TEXT, notified INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def add_subscriber(user_id, name, expiry_date):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO subscribers (user_id, name, expiry_date, notified) VALUES (?, ?, ?, 0)", 
              (user_id, name, expiry_date))
    conn.commit()
    conn.close()

# --- إعداد البوت ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
app_flask = Flask(__name__)

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 اشتراك تحليلات SPX الخاصة  ", callback_data='menu_spx')],
        [InlineKeyboardButton("📈 اشتراك المؤشرات الفنية الخاصة ", callback_data='menu_indicators')],
        [InlineKeyboardButton("🆓      القناة المجانية        ", url=FREE_CHANNEL_URL)],
        [InlineKeyboardButton("✅     أرسل إثبات الدفع      ", callback_data='upload_proof')],
        [InlineKeyboardButton("💬       الدعم الفني        ", url=URLS["whatsapp_support"])]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "🚀 مرحبًا بك في بوت AZIZ Trading\n\n"
        "📊 بوابتك إلى تداول أكثر احترافية وقرارات مبنية على تحليل دقيق لحركة السوق \n\n"
        "📈 اختر من الأزرار أدناه للوصول إلى خدماتنا وابدأ رحلتك الآن"
    )
    await update.message.reply_text(welcome_message, reply_markup=main_menu_keyboard())

# وظيفة التنبيه التلقائي (تعمل كل فترة)
async def check_expirations(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # جلب المستخدمين الذين ينتهي اشتراكهم خلال 48 ساعة ولم يتم تنبيههم
    threshold = (datetime.now() + timedelta(hours=48)).strftime('%Y-%m-%d %H:%M')
    c.execute("SELECT user_id, name, expiry_date FROM subscribers WHERE expiry_date <= ? AND notified = 0", (threshold,))
    users = c.fetchall()
    
    for user in users:
        uid, name, exp = user
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"⚠️ تنبيه اقتراب انتهاء الاشتراك!\n\nعزيزي {name}، نود تذكيرك بأن اشتراكك في خدمات AZIZ Trading ينتهي قريباً بتاريخ: {exp}\n\nيرجى التجديد لضمان استمرار الخدمة."
            )
            c.execute("UPDATE subscribers SET notified = 1 WHERE user_id = ?", (uid,))
        except Exception as e:
            logging.error(f"Could not send reminder to {uid}: {e}")
            
    conn.commit()
    conn.close()

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
        await query.edit_message_text("بانتظار الإثبات ⏳\nمن فضلك أرسل الآن رقم الطلب هنا مباشرة:", reply_markup=InlineKeyboardMarkup(keyboard))
            
    elif data.startswith('approve_'):
        if query.from_user.id != ADMIN_ID: return
        parts = data.split('_')
        duration_days = int(parts[1])
        cust_id = int(parts[2])

        expiry_dt = datetime.now() + timedelta(days=duration_days)
        expiry_date_str = expiry_dt.strftime('%Y-%m-%d')
        duration_text = "شهر" if duration_days == 30 else f"{duration_days // 30} شهور"

        try:
            invite = await context.bot.create_chat_invite_link(chat_id=PRIVATE_CHANNEL_ID, member_limit=1)
            await context.bot.send_message(chat_id=cust_id, text=f"🎉 تم تفعيل اشتراكك بنجاح لمدة ({duration_text})!\nرابط القناة الخاصة:\n{invite.invite_link}\n\nينتهي اشتراكك في تاريخ: {expiry_date_str}")

            member = await context.bot.get_chat(cust_id)
            name = f"{member.first_name} {member.last_name or ''}"

            # حفظ في قاعدة البيانات للتنبيه لاحقاً
            add_subscriber(cust_id, name, expiry_date_str)

            archive_msg = (f"👤 **مشترك جديد مؤكد**\n━━━━━━━━━━━━━━━\n"
                           f"📝 **الاسم:** {name}\n🆔 **الآيدي:** `{cust_id}`\n"
                           f"⏳ **مدة الاشتراك:** {duration_text}\n📅 **تاريخ الانتهاء:** `{expiry_date_str}`\n━━━━━━━━━━━━━━━")
            await context.bot.send_message(chat_id=ARCHIVE_CHANNEL_ID, text=archive_msg, parse_mode='Markdown')
            await query.edit_message_text(f"✅ تم قبول {name} بنجاح لمدة {duration_text} وتم جدولته للتنبيه.")
        except Exception as e:
            await query.edit_message_text(f"⚠️ حدث خطأ أثناء التفعيل: {str(e)}")

    elif data.startswith('reject_'):
        if query.from_user.id != ADMIN_ID: return
        cust_id = int(data.split('_')[1])
        try:
            await context.bot.send_message(chat_id=cust_id, text="❌ نعتذر، لم يتم تأكيد الدفع. يرجى التواصل مع الدعم الفني.")
            await query.edit_message_text(f"❌ تم رفض الطلب للآيدي {cust_id}.")
        except:
            await query.edit_message_text(f"❌ تم الرفض (تعذر مراسلة العميل).")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_for_proof'):
        user = update.effective_user
        admin_kb = [[InlineKeyboardButton("✅ قبول (30 يوم)", callback_data=f"approve_30_{user.id}")],
                    [InlineKeyboardButton("✅ قبول (90 يوم)", callback_data=f"approve_90_{user.id}")],
                    [InlineKeyboardButton("✅ قبول (180 يوم)", callback_data=f"approve_180_{user.id}")],
                    [InlineKeyboardButton("❌ رفض الطلب", callback_data=f"reject_{user.id}")]]
        caption = f"🔔 إثبات دفع جديد\n👤 العميل: {user.first_name}\n🆔 الآيدي: `{user.id}`"
        if update.message.photo:
            await context.bot.send_photo(chat_id=REQUESTS_CHANNEL_ID, photo=update.message.photo[-1].file_id, caption=caption, reply_markup=InlineKeyboardMarkup(admin_kb))
        else:
            await context.bot.send_message(chat_id=REQUESTS_CHANNEL_ID, text=f"{caption}\n📝 المحتوى: {update.message.text}", reply_markup=InlineKeyboardMarkup(admin_kb))
        await update.message.reply_text("⏳ تم إرسال إثباتك بنجاح. سيتم الرد عليك هنا فور مراجعة سلة للطلب.")
        context.user_data['waiting_for_proof'] = False

@app_flask.route('/')
def home(): return "Bot is Online"

def main():
    if not TOKEN: return
    init_db() # إنشاء قاعدة البيانات عند التشغيل
    
    threading.Thread(target=lambda: app_flask.run(host='0.0.0.0', port=PORT), daemon=True).start()
    
    application = Application.builder().token(TOKEN).build()
    
    # إضافة مهمة التنبيه لتعمل كل ساعة (3600 ثانية) للبحث عن من اقترب انتهاؤهم
    job_queue = application.job_queue
    job_queue.run_repeating(check_expirations, interval=3600, first=10)

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.run_polling()

if __name__ == '__main__':
    main()
