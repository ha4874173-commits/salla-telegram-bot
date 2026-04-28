import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# 1. إعدادات البوت والروابط
TOKEN = '8232201715:AAFEvsg1y3tD8_CXOXx0NT2CsdZU_jw9sN8'

# روابط منتجات سلة (استبدلها بالروابط الحقيقية من متجر فيصل)
URLS = {
    "spx_1m": "https://salla.sa/spx-1-month",
    "spx_3m": "https://salla.sa/spx-3-months",
    "spx_6m": "https://salla.sa/spx-6-months",
    "spx_1y": "https://salla.sa/spx-1-year",
    "ind_1m": "https://salla.sa/indicators-1-month",
    "ind_3m": "https://salla.sa/indicators-3-months",
    "ind_6m": "https://salla.sa/indicators-6-months",
    "ind_1y": "https://salla.sa/indicators-1-year",
}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# القائمة الرئيسية
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 اشتراك تحليل SPX", callback_data='menu_spx')],
        [InlineKeyboardButton("📈 اشتراك المؤشرات الفنية", callback_data='menu_indicators')],
        [InlineKeyboardButton("✅ تأكيد الدفع (إرسال رقم الطلب)", callback_data='verify_payment')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "مرحباً بك في بوت خدماتنا التقنية! 🚀\nالرجاء اختيار الخدمة المطلوبة للاشتراك:"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup)

# معالجة الضغط على الأزرار
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # قائمة تحليل SPX
    if query.data == 'menu_spx':
        keyboard = [
            [InlineKeyboardButton("شهر - 100 ريال", url=URLS["spx_1m"])],
            [InlineKeyboardButton("3 شهور - 250 ريال", url=URLS["spx_3m"])],
            [InlineKeyboardButton("6 شهور - 450 ريال", url=URLS["spx_6m"])],
            [InlineKeyboardButton("سنة - 800 ريال", url=URLS["spx_1y"])],
            [InlineKeyboardButton("🔙 العودة للقائمة", callback_data='back_to_main')]
        ]
        await query.edit_message_text("اختر مدة الاشتراك في خدمة تحليل SPX:", reply_markup=InlineKeyboardMarkup(keyboard))

    # قائمة المؤشرات الفنية
    elif query.data == 'menu_indicators':
        keyboard = [
            [InlineKeyboardButton("شهر - 150 ريال", url=URLS["ind_1m"])],
            [InlineKeyboardButton("3 شهور - 400 ريال", url=URLS["ind_3m"])],
            [InlineKeyboardButton("6 شهور - 700 ريال", url=URLS["ind_6m"])],
            [InlineKeyboardButton("سنة - 1200 ريال", url=URLS["ind_1y"])],
            [InlineKeyboardButton("🔙 العودة للقائمة", callback_data='back_to_main')]
        ]
        await query.edit_message_text("اختر مدة الاشتراك في خدمة المؤشرات الفنية:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data == 'back_to_main':
        await start(update, context)

    elif query.data == 'verify_payment':
        await query.edit_message_text("من فضلك، أرسل رقم الطلب الخاص بك المكون من أرقام فقط للتحقق من اشتراكك.")

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("🚀 البوت المطور يعمل الآن بالأزرار الجديدة...")
    application.run_polling()

if __name__ == '__main__':
    main()
