import logging
import os
import asyncio
import threading
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
    "whatsapp_support": "https://wa.me//0554852681" 
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
app_flask = Flask(__name__)

# --- 2. واجهة القائمة الرئيسية ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 اشتراك تحليلات SPX الخاصة", callback_data='menu_spx')],
        [InlineKeyboardButton("📈 اشتراك المؤشرات الفنية ", callback_data='menu_indicators')],
        [InlineKeyboardButton("🆓 القناة المجانية ", url=FREE_CHANNEL_URL)],
        [InlineKeyboardButton("✅ أرسل إثبات الدفع ", callback_data='upload_proof')],
        [InlineKeyboardButton("💬 الدعم الفني ", url=URLS["whatsapp_support"])]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحباً بك في بوت عزيز! 🚀\nاختر خدمتك المفضلة من الأزرار أدناه:",
        reply_markup=main_menu_keyboard()
    )

# --- 3. معالجة الأزرار والتنقل ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == 'back_to_main':
        context.user_data['waiting_for_proof'] = False
        await query.edit_message_text("الرئيسية 🏠\nاختر خدمتك المفضلة:", reply_markup=main_menu_keyboard())

    elif data == 'menu_spx':
        keyboard = [
            [InlineKeyboardButton("شهر - 100 ريال", url=URLS["spx_1m"])],
            [InlineKeyboardButton("3 شهور - 279 ريال", url=URLS["spx_3m"])],
            [InlineKeyboardButton("6 شهور - 549 ريال", url=URLS["spx_6m"])],
            [InlineKeyboardButton("✅ أرسل إثبات الدفع", callback_data='upload_proof')],
            [InlineKeyboardButton("🔙 العودة", callback_data='back_to_main')]
        ]
        await query.edit_message_text("باقات SPX 📊\nاختر المدة للدفع ثم أرسل الإثبات:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'menu_indicators':
        keyboard = [
            [InlineKeyboardButton("Aziz pro مؤشر - 399 ريال", url=URLS["ind_1m"])],
            [InlineKeyboardButton("✅ أرسل إثبات الدفع", callback_data='upload_proof')],
            [InlineKeyboardButton("🔙 العودة", callback_data='back_to_main')]
        ]
        await query.edit_message_text("المؤشرات الفنية 📈\nادفع ثم أرسل الإثبات للمراجعة:", reply_markup=InlineKeyboardMarkup(keyboard))

    # بدء عملية رفع الإثبات
    elif data == 'upload_proof':
        context.user_data['waiting_for_proof'] = True
        keyboard = [[InlineKeyboardButton("🔙 إلغاء والعودة للرئيسية", callback_data='back_to_main')]]
        await query.edit_message_text(
            "بانتظار الإثبات ⏳\nمن فضلك أرسل الآن صورة الإيصال (Screenshot) أو رقم الطلب هنا مباشرة:",
            reply_markup=InlineKeyboardMarkup(keyboard)
            
    # --- نظام القبول بتحديد المدة (للأدمن) ---
    elif data.startswith('approve_'):
        if query.from_user.id != ADMIN_ID: return
        
        # التقسيم: approve_{المدة}_{آيدي_العميل}
        parts = data.split('_')
        duration_days = int(parts[1])
        cust_id = int(parts[2])

        # حساب تاريخ الانتهاء
        expiry_date = (datetime.now() + timedelta(days=duration_days)).strftime('%Y-%m-%d')
        duration_text = "شهر واحد" if duration_days == 30 else f"{duration_days // 30} شهور"

        # 1. إنشاء رابط الدعوة
        invite = await context.bot.create_chat_invite_link(chat_id=PRIVATE_CHANNEL_ID, member_limit=1)
        
        # 2. إرسال للعميل
        await context.bot.send_message(
            chat_id=cust_id, 
            text=f"✅ تم تفعيل اشتراكك لمدة ({duration_text})!\nتفضل رابط القناة:\n{invite.invite_link}\n\nينتهي اشتراكك في: {expiry_date}"
        )

        # 3. جلب بيانات العميل للأرشيف
        try:
            member = await context.bot.get_chat(cust_id)
            name = f"{member.first_name} {member.last_name or ''}"
        except: name = "مستخدم"

        # 4. الإرسال للأرشيف (الداتا كاملة)
        archive_msg = (
            f"👤 **مشترك جديد مؤكد**\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📝 **الاسم:** {name}\n"
            f"🆔 **الآيدي:** `{cust_id}`\n"
            f"⏳ **المدة:** {duration_text}\n"
            f"📅 **ينتهي في:** `{expiry_date}`\n"
            f"━━━━━━━━━━━━━━━"
        )
        await context.bot.send_message(chat_id=ARCHIVE_CHANNEL_ID, text=archive_msg, parse_mode='Markdown')
        await query.edit_message_text(f"✅ تم تفعيل {name} لمدة {duration_text} وأرشفة البيانات.")

    elif data.startswith('reject_'):
        if query.from_user.id != ADMIN_ID: return
        cust_id = int(data.split('_')[1])
        await context.bot.send_message(chat_id=cust_id, text="❌ نعتذر، لم يتم تأكيد الدفع. راجع الدعم.")
        await query.edit_message_text(f"❌ تم رفض الطلب للآيدي {cust_id}.")

# --- 4. استقبال الإثباتات (أزرار القبول بالمدد) ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_for_proof'):
        user = update.effective_user
        
        # أزرار فيصل: قبول شهر، 3 شهور، 6 شهور، أو رفض
        admin_kb = [
            [InlineKeyboardButton("✅ قبول (شهر)", callback_data=f"approve_30_{user.id}")],
            [InlineKeyboardButton("✅ قبول (3 شهور)", callback_data=f"approve_90_{user.id}")],
            [InlineKeyboardButton("✅ قبول (6 شهور)", callback_data=f"approve_180_{user.id}")],
            [InlineKeyboardButton("❌ رفض الطلب", callback_data=f"reject_{user.id}")]
        ]
        
        caption = f"🔔 إثبات دفع جديد\n👤 العميل: {user.first_name}\n🆔 الآيدي: `{user.id}`"
        
        if update.message.photo:
            await context.bot.send_photo(chat_id=REQUESTS_CHANNEL_ID, photo=update.message.photo[-1].file_id, caption=caption, reply_markup=InlineKeyboardMarkup(admin_kb))
        else:
            await context.bot.send_message(chat_id=REQUESTS_CHANNEL_ID, text=f"{caption}\n📝 المحتوى: {update.message.text}", reply_markup=InlineKeyboardMarkup(admin_kb))
        
        await update.message.reply_text("⏳ تم إرسال إثباتك. سيصلك الرد هنا فور المراجعة من سلة.")
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
    application.run_polling()

if __name__ == '__main__':
    main()
