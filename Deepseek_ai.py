import os
import logging
import re
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = os.getenv("sk-9f5786059ed64f56bbd7bf3510005d31")
TELEGRAM_TOKEN = os.getenv("7892011487:AAFoX7bEAS3MBO6zzm5NjMyXPecNX2OCdHc")
BOT_USERNAME = os.getenv("ShweNarSin2_bot", "")

async def handle_mention(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        user_id = message.from_user.id
        
        # Extract text after bot mention
        if message.text and BOT_USERNAME:
            # Remove the mention and clean the text
            pattern = f'@?{BOT_USERNAME}\\s*'
            user_message = re.sub(pattern, '', message.text, flags=re.IGNORECASE).strip()
            
            if not user_message:
                await message.reply_text("🎵 **မင်းသား​ရှ်​မှုစ် AI Bot**\n\n@BotName နောက်မှာ မေးခွန်းရေးပါ\nဥပမာ: `@BotName AI ဆိုတာဘာလဲ?`")
                return
            
            logger.info(f"Mention from user {user_id}: {user_message}")
            
            # Call DeepSeek API
            headers = {
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": user_message}],
                "stream": False
            }
            
            # Show typing action
            await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")
            
            response = requests.post(DEEPSEEK_API_URL, json=data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                ai_response = response.json()["choices"][0]["message"]["content"]
                
                # Telegram message length limit (4096 characters)
                if len(ai_response) > 4096:
                    chunks = [ai_response[i:i+4090] for i in range(0, len(ai_response), 4090)]
                    for i, chunk in enumerate(chunks):
                        if i == 0:
                            await message.reply_text(chunk)
                        else:
                            await message.reply_text(chunk)
                else:
                    await message.reply_text(ai_response)
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                await message.reply_text("🎵 ကျေးဇူးပြု၍ နောက်မှထပ်ကြိုးစားပါ...")
                
    except requests.exceptions.Timeout:
        logger.error("DeepSeek API request timeout")
        await message.reply_text("⏰ အချိန်အကန့်အသတ်ကျော်သွားပါပြီ...")
    except Exception as e:
        logger.error(f"Error in handle_mention: {str(e)}")
        await message.reply_text("❌ ယာယီပြဿနာတစ်ခုရှိနေပါတယ်...")

async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle private messages (without mention)"""
    try:
        user_message = update.message.text
        user_id = update.message.from_user.id
        
        # If empty message or command-like text
        if not user_message.strip() or user_message.startswith('/'):
            usage_text = """
🎵 **မင်းသား​ရှ်​မှုစ် AI Bot**

မည်သည့်မေးခွန်းကိုမဆို ဤနေရာတွင် တိုက်ရိုက်မေးပါ

**Group များတွင်:** @BotName ကို mention လုပ်ပါ

**ဥပမာများ:**
- ဂီတသီအိုရီ
- ကုဒ်ရေးသားခြင်း
- ဘာသာပြန်ဆိုခြင်း
- သင်္ချာပြဿနာများ
            """
            await update.message.reply_text(usage_text)
            return
        
        logger.info(f"Private message from user {user_id}: {user_message}")
        
        # Call DeepSeek API
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": user_message}],
            "stream": False
        }
        
        # Show typing action
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action="typing")
        
        response = requests.post(DEEPSEEK_API_URL, json=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            ai_response = response.json()["choices"][0]["message"]["content"]
            
            if len(ai_response) > 4096:
                chunks = [ai_response[i:i+4090] for i in range(0, len(ai_response), 4090)]
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await update.message.reply_text(chunk)
                    else:
                        await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(ai_response)
        else:
            logger.error(f"API Error: {response.status_code} - {response.text}")
            await update.message.reply_text("🎵 ကျေးဇူးပြု၍ နောက်မှထပ်ကြိုးစားပါ...")
            
    except Exception as e:
        logger.error(f"Error in handle_private_message: {str(e)}")
        await update.message.reply_text("❌ ယာယီပြဿနာတစ်ခုရှိနေပါတယ်...")

async def handle_unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any unknown commands"""
    await update.message.reply_text(
        "🎵 **မင်းသား​ရှ်​မှုစ် AI Bot**\n\n"
        "မည်သည့်မေးခွန်းကိုမဆို တိုက်ရိုက်မေးမြန်းနိုင်ပါတယ်။\n\n"
        "**Group များတွင်:** @BotName ကို mention လုပ်ပါ\n"
        "**Private Chat တွင်:** တိုက်ရိုက်စာပို့ပါ"
    )

def main():
    # Check environment variables
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN not set!")
        return
    if not DEEPSEEK_API_KEY:
        logger.error("DEEPSEEK_API_KEY not set!")
        return
    
    # Create application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    # Mention handler for group chats
    if BOT_USERNAME:
        mention_filter = filters.TEXT & filters.Entity("mention")
        application.add_handler(MessageHandler(mention_filter, handle_mention))
        logger.info(f"Bot username: {BOT_USERNAME}")
    else:
        logger.warning("BOT_USERNAME not set, mention feature disabled")
    
    # Private message handler
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_private_message))
    
    # Handle any commands with usage info
    application.add_handler(MessageHandler(filters.COMMAND, handle_unknown_command))
    
    # Start the bot
    logger.info("🎵 မင်းသား​ရှ်​မှုစ် AI Bot စတင်နေပါပြီ...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
