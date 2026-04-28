import logging
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# 1. إعدادات البوت والروابط
TOKEN = '8232201715:AAFEvsg1y3tD8_CXOXx0NT2CsdZU_jw9sN8'
SALLA_TOKEN = 'حط_هنا_التوكن_اللي_هيبعته_فيصل' # Access Token من سلة بلس
CHANNEL_ID = '-1002462310103' # يوزر أو ID القناة

# روابط المنتجات من متجر فيصل
URLS = {
    "spx_1m": "https://salla.sa/spx-1-month",
    "spx_3m": "https://salla.sa/spx-3-months",
    "ind_1m": "https://salla.sa/indicators-1-month",
    "ind_1y": "https://salla.sa/indicators-1-year"
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- دالة التحقق من طلب سلة ---
def verify_salla_order(order_id):
    headers = {
        'Authorization': f'Bearer {SALLA_TOKEN}',
        'Content-Type': 'application/json'
    }
    try:
        response = requests.get(f'https://api.salla.dev/admin/v2/orders/{order_id}', headers=headers)
        if response.status_code == 200:
            data = response.json()
            status = data['data']['status']['id'] # الحالة
            # نتحقق إن الطلب مكتمل أو تم شحنه (بناءً على نظام سلة)
            if status in ['completed', 'delivered']:
                return True
        return False
    except Exception as e:
        print(f"Error Salla API: {e}")
        return False

# --- واجهة البوت ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 اشتراك تحليل SPX", callback_data='menu_spx')],
        [InlineKeyboardButton("📈 اشتراك المؤشرات الفنية", callback_data='menu_indicators')],
        [InlineKeyboardButton("✅ تأكيد الدفع (إرسال رقم الطلب)", callback_data='verify_payment')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("مرحباً بك في بوت خدماتنا التقنية! 🚀\nالرجاء اختيار الخدمة المطلوبة للاشتراك:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'menu_spx':
        keyboard = [
            [InlineKeyboardButton("شهر - 150 ريال", url=URLS["spx_1m"])],
            [InlineKeyboardButton("3 شهور - 400 ريال", url=URLS["spx_3m"])],
            [InlineKeyboardButton("🔙 عودة", callback_data='back_to_main')]
        ]
        await query.edit_message_text("اختر مدة اشتراك تحليل SPX:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'verify_payment':
        context.user_data['waiting_for_order'] = True
        await query.edit_message_text("من فضلك، قم بإرسال **رقم الطلب** المكون من أرقام فقط (مثال: 12345678) للتحقق من اشتراكك.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_for_order'):
        order_id = update.message.text.strip()
        
        if not order_id.isdigit():
            await update.message.reply_text("الرجاء إرسال رقم طلب صحيح (أرقام فقط).")
            return

        await update.message.reply_text("جاري التحقق من حالة الطلب في سلة... ⏳")
        
        if verify_salla_order(order_id):
            # إنشاء رابط دعوة مؤقت للقناة
            invite_link = await context.bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
            await update.message.reply_text(f"✅ تم التحقق! اشتراكك فعال.\nتفضل برابط الدخول للقناة:\n{invite_link.invite_link}")
        else:
            await update.message.reply_text("❌ لم نتمكن من العثور على طلب مكتمل بهذا الرقم. تأكد من إتمام الدفع أو تواصل مع الدعم.")
        
        context.user_data['waiting_for_order'] = False

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
