import os
import shutil
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

from jellyfin_api import JellyfinClient
from downloader import DownloadManager

load_dotenv()
ADMIN_IDS = [int(i.strip()) for i in os.getenv("ADMIN_IDS").split(",")]
BASE_PATH = os.getenv("BASE_MEDIA_PATH")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Client("jelly_bot", 
             api_id=os.getenv("API_ID"), 
             api_hash=os.getenv("API_HASH"), 
             bot_token=os.getenv("BOT_TOKEN"), 
             workers=20)

jf = JellyfinClient(os.getenv("JELLYFIN_URL"), os.getenv("JELLYFIN_API_KEY"))
dl_manager = DownloadManager(app)

# Helper to find media in a message or its reply
def get_media_from_msg(msg: Message):
    if not msg: return None
    if msg.video or msg.document or msg.audio or msg.animation:
        return msg
    return None

@app.on_message(filters.command("download") & filters.user(ADMIN_IDS))
async def on_download_cmd(client, message: Message):
    # Check the command itself OR what it's replying to
    target = get_media_from_msg(message) or get_media_from_msg(message.reply_to_message)

    if not target:
        return await message.reply("❌ **Error:** Please reply to a video or file with `/download`.")

    buttons = [[
        InlineKeyboardButton("🎥 Movie", callback_data=f"dl|movies|{target.id}"),
        InlineKeyboardButton("📺 TV Show", callback_data=f"dl|shows|{target.id}")
    ]]
    await message.reply("Where should I save this?", 
                        reply_markup=InlineKeyboardMarkup(buttons), 
                        quote=True)

@app.on_callback_query(filters.regex(r"^dl\|"))
async def on_callback(client, callback_query):
    # data format: dl | category | target_message_id
    data = callback_query.data.split("|")
    category = data[1]
    target_id = int(data[2])
    chat_id = callback_query.message.chat.id
    
    # FORCE FETCH the message from Telegram servers to avoid 'NoneType'
    try:
        target_msg = await client.get_messages(chat_id, target_id)
    except Exception as e:
        return await callback_query.message.edit_text(f"❌ **Message lost:** {e}")

    if not get_media_from_msg(target_msg):
        return await callback_query.message.edit_text("❌ **Error:** The media is no longer available.")

    status_msg = await callback_query.message.edit_text("⏳ **Initializing...**")
    dest_path = os.path.join(BASE_PATH, category)

    try:
        final_file = await dl_manager.download_file(status_msg, target_msg, dest_path)
        await status_msg.edit_text(f"✅ **Success!**\n`{os.path.basename(final_file)}` saved to `{category}`.")
        
        if await jf.trigger_scan():
            await status_msg.reply("🔄 Jellyfin is scanning the library...")
    except Exception as e:
        logger.error(f"Fail: {e}")
        await status_msg.edit_text(f"❌ **Failed:** `{str(e)}` ")

if __name__ == "__main__":
    if not os.path.exists(BASE_PATH): os.makedirs(BASE_PATH, exist_ok=True)
    app.run()
