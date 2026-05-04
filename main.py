import logging
import os
import asyncio
import threading
from datetime import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 1. الإعدادات والمعرفات ---
TOKEN = os.getenv("TOKEN") or os.getenv("BOT_TOKEN")
ADMIN_ID = 5332562107  # 

# معرفات القنوات
PRIVATE_CHANNEL_ID = '-1003953368081'  # القناة الخاصة
FREE_CHANNEL_URL = 'https://t.me/c/3907521588/1' # القناة المجانية
REQUESTS_CHANNEL_ID = '-1003846832363' # قناة الطلبات
ARCHIVE_CHANNEL_ID = '-1003989339996'  # قناة الأرشيف

PORT = int(os.environ.get('PORT', 8080))

URLS = {
    "spx_1m": "https://salla.sa/AZIZSPX/WzbWgKA",
    "spx_3m": "https://salla.sa/AZIZSPX/xvnbrQb",
    "spx_6m": "https://salla.sa/AZIZSPX/azdOBBK",
    "ind_1m": "https://salla.sa/AZIZSPX/EXKwOwZ",
    "whatsapp_support": "https://wa.me/0554852681" # 
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
app_flask = Flask(__name__)

# --- 2. واجهة البوت الرئيسية ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 اشتراك تحليلات SPX الخاصه", callback_data='menu_spx')],
        [InlineKeyboardButton("📈 اشتراك المؤشرات الفنية الخاصة", callback_data='menu_indicators')],
        [InlineKeyboardButton("🆓 القناة المجانية", url=FREE_CHANNEL_URL)],
        [InlineKeyboardButton("💬 الدعم الفني ", url=URLS["whatsapp_support"])]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحباً بك في بوت عزيز! 🚀\nاختر خدمتك المفضلة من الأزرار أدناه:",
        reply_markup=main_menu_keyboard()
    )

# --- 3. معالجة الضغط على الأزرار ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == 'menu_spx':
        keyboard = [
            [InlineKeyboardButton("شهر - 100 ريال", url=URLS["spx_1m"])],
            [InlineKeyboardButton("3 شهور - 279 ريال", url=URLS["spx_3m"])],
            [InlineKeyboardButton("6 شهور - 549 ريال", url=URLS["spx_6m"])],
            [InlineKeyboardButton("✅ أرسل إثبات الدفع", callback_data='upload_proof')],
            [InlineKeyboardButton("🔙 عودة", callback_data='back_to_main')]
        ]
        await query.edit_message_text("اختر مدة الاشتراك للدفع عبر سلة، ثم أرسل الإثبات:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'menu_indicators':
        keyboard = [
            [InlineKeyboardButton("Aziz pro مؤشر - 399 ريال", url=URLS["ind_1m"])],
            [InlineKeyboardButton("✅ أرسل إثبات الدفع", callback_data='upload_proof')],
            [InlineKeyboardButton("🔙 عودة", callback_data='back_to_main')]
        ]
        await query.edit_message_text("ادفع عبر الرابط ثم أرسل الإثبات للمراجعة اليدوية:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'upload_proof':
        context.user_data['waiting_for_proof'] = True
        await query.edit_message_text("من فضلك أرسل الآن صورة الإيصال (Screenshot) أو رقم الطلب :")

    elif data == 'back_to_main':
        context.user_data['waiting_for_proof'] = False
        await query.edit_message_text("اختر خدمتك المفضلة:", reply_markup=main_menu_keyboard())

    elif data.startswith(('approve_', 'reject_')):
        if query.from_user.id != ADMIN_ID: return
        action, cust_id = data.split('_')
        cust_id = int(cust_id)

        if action == 'approve':
            # 1. إنشاء رابط الدعوة
            invite = await context.bot.create_chat_invite_link(chat_id=PRIVATE_CHANNEL_ID, member_limit=1)
            
            # 2. إرسال الرابط للعميل
            await context.bot.send_message(chat_id=cust_id, text=f"🎉 تم تأكيد اشتراكك بنجاح!\nتفضل رابط الانضمام للقناة الخاصة:\n{invite.invite_link}")
            
            # 3. محاولة الحصول على اسم العميل للأرشفة
            try:
                member = await context.bot.get_chat(cust_id)
                full_name = f"{member.first_name} {member.last_name if member.last_name else ''}"
                username = f"@{member.username}" if member.username else "بدون يوزر"
            except:
                full_name = "مستخدم"
                username = "غير متاح"

            # 4. إرسال البيانات لقناة الأرشيف (هنا التعديل لضمان وصول الداتا)
            archive_msg = (
                f"✅ **تم قبول مشترك جديد**\n\n"
                f"👤 **الاسم:** {full_name}\n"
                f"🆔 **الآيدي:** `{cust_id}`\n"
                f"🔗 **اليوزر:** {username}\n"
                f"📅 **تاريخ التفعيل:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"⚙️ **الحالة:** تم الإرسال بنجاح"
            )
            await context.bot.send_message(chat_id=ARCHIVE_CHANNEL_ID, text=archive_msg, parse_mode='Markdown')
            
            # 5. تحديث رسالة قناة الطلبات
            await query.edit_message_text(f"✅ تم قبول {full_name} ({cust_id}) وأرشفة البيانات.")
            
        else:
            await context.bot.send_message(chat_id=cust_id, text="❌ نعتذر، لم يتم تأكيد الدفع. يرجى مراجعة الدعم الفني.")
            await query.edit_message_text(f"❌ تم رفض طلب العميل {cust_id}.")

# --- 4. استقبال الإثباتات وتوجيهها لقناة الطلبات ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_for_proof'):
        user = update.effective_user
        admin_kb = [
            [InlineKeyboardButton("✅ قبول", callback_data=f"approve_{user.id}"),
             InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user.id}")]
        ]
        
        caption = f"🔔 إثبات دفع جديد\n👤 العميل: {user.first_name}\n🆔 الآيدي: `{user.id}`"
        
        if update.message.photo:
            await context.bot.send_photo(chat_id=REQUESTS_CHANNEL_ID, photo=update.message.photo[-1].file_id, caption=caption, reply_markup=InlineKeyboardMarkup(admin_kb))
        else:
            await context.bot.send_message(chat_id=REQUESTS_CHANNEL_ID, text=f"{caption}\n📝 المحتوى: {update.message.text}", reply_markup=InlineKeyboardMarkup(admin_kb))
        
        await update.message.reply_text("⏳ تم إرسال إثباتك بنجاح. سيتم الرد عليك هنا فور مراجعة سلة للطلب.")
        context.user_data['waiting_for_proof'] = False

# --- 5. التشغيل ---
@app_flask.route('/')
def home(): return "Bot is Online"

def main():
    if not TOKEN: return
    threading.Thread(target=lambda: app_flask.run(host='0.0.0.0', port=PORT), daemon=True).start()
    
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 البوت يعمل الآن.. الداتا ستنتقل للأرشيف فور القبول.")
    application.run_polling()

if __name__ == '__main__':
    main()
