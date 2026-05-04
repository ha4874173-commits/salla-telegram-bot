import os
import asyncio
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 1. الإعدادات ---
TOKEN = os.getenv("TOKEN") or os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID") # تأكد إنك حاطط آيدي فيصل هنا في Railway
DATA_CHANNEL_ID = "-1003970062260" 
PORT = int(os.environ.get('PORT', 8080))

URLS = {
    "spx_1m": "https://salla.sa/AZIZSPX/WzbWgKA",
    "spx_3m": "https://salla.sa/AZIZSPX/xvnbrQb",
    "spx_6m": "https://salla.sa/AZIZSPX/azdOBBK",
    "ind_1m": "https://salla.sa/AZIZSPX/EXKwOwZ",
    "whatsapp_support": "https://wa.me/966XXXXXXXXX", # استبدل بالرقم الحقيقي
    "free_channel": "https://t.me/c/3907521588/1",
    "private_channel": "https://t.me/c/3953368081/1"
}

app = Flask(__name__)
bot_instance = Bot(token=TOKEN) if TOKEN else None

# --- 2. الواجهة ---
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 اشتراك تحليلات SPX العالمية", callback_data='menu_spx')],
        [InlineKeyboardButton("📈 اشتراك المؤشرات الفنية الخاصة", callback_data='menu_indicators')],
        [InlineKeyboardButton("✅ تأكيد اشتراك (إرسال فاتورة/صورة)", callback_data='verify_sub')],
        [InlineKeyboardButton("🆓 القناة المجانية (مدى الحياة)", url=URLS["free_channel"])],
        [InlineKeyboardButton("💬 الدعم الفني (واتساب)", url=URLS["whatsapp_support"])]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً بك في بوت عزيز! 🚀\nأرسل صورة الفاتورة أو اختر من القائمة:", reply_markup=main_menu_keyboard())

# --- 3. حل مشكلة إرسال الإثبات للأدمن ---
async def handle_verification_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # إذا كان المرسل هو الأدمن نفسه، لا نفعل شيئاً
    if str(update.effective_user.id) == str(ADMIN_ID):
        return

    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("✅ قبول", callback_data=f"approve_{user.id}"),
         InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user.id}")]
    ]
    
    # التأكد من إرسال الطلب لفيصل (ADMIN_ID)
    try:
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            await context.bot.send_photo(
                chat_id=ADMIN_ID, 
                photo=file_id, 
                caption=f"📩 طلب تفعيل جديد\nمن: {user.first_name}\nID: `{user.id}`",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif update.message.text:
            await context.bot.send_message(
                chat_id=ADMIN_ID, 
                text=f"📩 طلب تفعيل جديد (نصي)\nمن: {user.first_name}\nالرسالة: {update.message.text}\nID: `{user.id}`",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        await update.message.reply_text("✅ تم إرسال إثباتك لفيصل للمراجعة. انتظر الرد هنا.")
    except Exception as e:
        print(f"Error sending to admin: {e}")
        await update.message.reply_text("❌ حدث خطأ في إرسال طلبك، حاول لاحقاً.")

# --- 4. معالجة القبول والرفض ---
async def admin_decision_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    action, user_id = data.split("_")

    if action == "approve":
        await context.bot.send_message(chat_id=user_id, text=f"🎉 تم قبول اشتراكك! رابط القناة:\n{URLS['private_channel']}")
        await context.bot.send_message(chat_id=DATA_CHANNEL_ID, text=f"✅ تفعيل يدوي ناجح للعميل {user_id}")
        msg = "✅ تم القبول بنجاح"
    else:
        await context.bot.send_message(chat_id=user_id, text="❌ نعتذر، تم رفض الطلب لعدم وضوح البيانات.")
        msg = "❌ تم الرفض"

    if query.message.photo:
        await query.edit_message_caption(caption=query.message.caption + f"\n\n{msg}")
    else:
        await query.edit_message_text(text=query.message.text + f"\n\n{msg}")

# --- 5. الويب هوك وتشغيل البوت ---
@app.route('/webhook', methods=['POST'])
def salla_webhook():
    # كود معالجة سلة (كما هو)
    return jsonify({'status': 'success'}), 200

def main():
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=PORT), daemon=True).start()
    
    application = Application.builder().token(TOKEN).build()
    
    # الأوامر
    application.add_handler(CommandHandler("start", start))
    
    # معالجة أزرار القبول والرفض (يجب أن تكون قبل معالج الأزرار العام)
    application.add_handler(CallbackQueryHandler(admin_decision_handler, pattern="^(approve|reject)_"))
    
    # معالجة أزرار القائمة
    application.add_handler(CallbackQueryHandler(lambda u, c: None, pattern="^menu_")) # لتجنب أخطاء الأنماط
    
    # أهم سطر: استقبال الصور والنصوص من العميل
    application.add_handler(MessageHandler(filters.PHOTO | filters.TEXT & (~filters.COMMAND), handle_verification_request))
    
    application.run_polling()

if __name__ == '__main__':
    main()
