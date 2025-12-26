import aiohttp
import logging

class JellyfinClient:
    def __init__(self, url, api_key):
        self.url = url.rstrip('/')
        self.headers = {
            "X-Emby-Token": api_key,
            "Content-Type": "application/json"
        }

    async def get_system_info(self):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.url}/System/Info", headers=self.headers, timeout=5) as r:
                    return r.status == 200
            except Exception:
                return False

    async def trigger_scan(self):
        async with aiohttp.ClientSession() as session:
            # Refresh the whole library
            async with session.post(f"{self.url}/Library/Refresh", headers=self.headers) as r:
                return r.status == 204

    async def get_libraries(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.url}/Library/VirtualFolders", headers=self.headers) as r:
                return await r.json()
