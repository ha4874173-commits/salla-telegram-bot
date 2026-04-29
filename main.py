import logging
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# --- 1. الإعدادات ---
TOKEN = '8232201715:AAFEvsg1y3tD8_CXOXx0NT2CsdZU_jw9sN8'
CHANNEL_ID = '-1003953368081'
ADMIN_ID = 5332562107  # آيدي 

URLS = {
    "spx_1m": "https://salla.sa/AZIZSPX/WzbWgKA",
    "spx_3m": "https://salla.sa/AZIZSPX/xvnbrQb",
    "spx_6m": "https://salla.sa/AZIZSPX/azdOBBK",
    "ind_1m": "https://salla.sa/AZIZSPX/EXKwOwZ",
    "support": "https://t.me/ess942"
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- 2. قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, expiry_date TEXT, trial_used INTEGER)')
    conn.commit()
    conn.close()

def add_user_trial(user_id):
    expiry = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, expiry_date, trial_used) VALUES (?, ?, 1)", (user_id, expiry))
    conn.commit()
    conn.close()

def has_used_trial(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT trial_used FROM users WHERE user_id=?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res is not None

# --- 3. واجهة البوت ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 اشتراك تحليلات SPX العالمية", callback_data='menu_spx')],
        [InlineKeyboardButton("📈 اشتراك المؤشرات الفنية الخاصة", callback_data='menu_indicators')],
        [InlineKeyboardButton("🎁 تجربة مجانية (7 أيام) 🎁", callback_data='free_trial')],
        [InlineKeyboardButton("💬 التواصل مع الدعم الفني", url=URLS["support"])]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً بك في بوت عزيز! 🚀\nاختر خدمتك المفضلة:", reply_markup=main_menu_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    await query.answer()

    # --- التجربة المجانية (تفعيل آلي) ---
    if data == 'free_trial':
        if has_used_trial(user_id):
            await query.edit_message_text("❌ عذراً، لقد استخدمت الفترة التجريبية مسبقاً.")
        else:
            add_user_trial(user_id)
            invite_link = await context.bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
            await query.edit_message_text(f"✅ تم تفعيل تجربتك المجانية لمدة 7 أيام!\nرابط القناة:\n{invite_link.invite_link}")

    # --- قائمة الاشتراكات المدفوعة ---
    elif data == 'menu_spx':
        keyboard = [[InlineKeyboardButton("رابط الدفع", url=URLS["spx_1m"])], [InlineKeyboardButton("✅ أرسل إثبات الدفع", callback_data='upload_proof')], [InlineKeyboardButton("🔙 عودة", callback_data='back_to_main')]]
        await query.edit_message_text("ادفع عبر سلة ثم أرسل الإثبات للمراجعة:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'menu_indicators':
        keyboard = [[InlineKeyboardButton("رابط الدفع", url=URLS["ind_1m"])], [InlineKeyboardButton("✅ أرسل إثبات الدفع", callback_data='upload_proof')], [InlineKeyboardButton("🔙 عودة", callback_data='back_to_main')]]
        await query.edit_message_text("ادفع عبر سلة ثم أرسل الإثبات للمراجعة:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'upload_proof':
        context.user_data['waiting_for_proof'] = True
        await query.edit_message_text("أرسل الآن صورة الإيصال أو رقم الطلب:")

    elif data == 'back_to_main':
        await query.edit_message_text("اختر خدمتك المفضلة:", reply_markup=main_menu_keyboard())

    # --- لوحة تحكم فيصل ---
    elif data.startswith('approve_'):
        if query.from_user.id != ADMIN_ID: return
        cust_id = int(data.split('_')[1])
        invite_link = await context.bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
        await context.bot.send_message(chat_id=cust_id, text=f"✅ تم تأكيد اشتراكك! رابط القناة:\n{invite_link.invite_link}")
        await query.edit_message_text(f"✅ تم قبول العميل {cust_id}")

    elif data.startswith('reject_'):
        if query.from_user.id != ADMIN_ID: return
        cust_id = int(data.split('_')[1])
        await context.bot.send_message(chat_id=cust_id, text="❌ لم يتم تأكيد الدفع، تواصل مع الدعم.")
        await query.edit_message_text(f"❌ تم رفض العميل {cust_id}")

# --- 4. استقبال الإثباتات ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_for_proof'):
        user = update.effective_user
        admin_kb = [[InlineKeyboardButton("✅ قبول", callback_data=f"approve_{user.id}")], [InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user.id}")]]
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"🔔 إثبات دفع جديد من {user.first_name} (ID: {user.id})")
        
        if update.message.photo:
            await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, reply_markup=InlineKeyboardMarkup(admin_kb))
        else:
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"النص: {update.message.text}", reply_markup=InlineKeyboardMarkup(admin_kb))
        
        await update.message.reply_text("⏳ تم الإرسال للمراجعة، انتظر الرد هنا.")
        context.user_data['waiting_for_proof'] = False

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()
