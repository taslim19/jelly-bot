import os
import time
import humanize
import logging

logger = logging.getLogger(__name__)

class DownloadManager:
    def __init__(self, client):
        self.client = client
        self.active_updates = {}

    async def progress_callback(self, current, total, status_msg, start_time, file_name):
        now = time.time()
        last_update = self.active_updates.get(status_msg.id, 0)
        if now - last_update < 5 and current != total:
            return

        self.active_updates[status_msg.id] = now
        percentage = (current * 100 / total) if total > 0 else 0
        speed = current / (now - start_time) if (now - start_time) > 0 else 0
        eta = (total - current) / speed if speed > 0 else 0
        
        progress_str = (
            f"📥 **Downloading:** `{file_name}`\n"
            f"📊 **Progress:** {percentage:.1f}%\n"
            f"🚀 **Speed:** {humanize.naturalsize(speed)}/s\n"
            f"⏱️ **ETA:** {humanize.precisedelta(int(eta), minimum_unit='seconds') if eta > 0 else 'Calculating...'}"
        )
        try:
            await status_msg.edit_text(progress_str)
        except:
            pass

    async def download_file(self, status_msg, media_msg, dest_folder):
        # Determine which attribute has the file
        media = (media_msg.video or media_msg.document or 
                 media_msg.audio or media_msg.animation)
        
        if not media:
            raise ValueError("The message contains no downloadable media.")

        # Get filename or create one
        file_name = getattr(media, 'file_name', None)
        if not file_name:
            # Fallback for files without names
            ext = ".mp4" if media_msg.video else ".file"
            file_name = f"media_{media_msg.id}{ext}"
            
        temp_path = os.path.join(dest_folder, f"{file_name}.temp")
        final_path = os.path.join(dest_folder, file_name)
        
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder, exist_ok=True)
            
        start_time = time.time()
        try:
            # Use the message object directly for download
            await self.client.download_media(
                message=media_msg, 
                file_name=temp_path,
                progress=self.progress_callback,
                progress_args=(status_msg, start_time, file_name)
            )
            
            os.rename(temp_path, final_path)
            os.chmod(final_path, 0o664)
            return final_path
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise e
