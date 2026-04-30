import asyncio
import os
import re
import traceback
from collections import deque

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp

load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = "!"
EMBED_COLOR = 0x1DB954

# ==================== COOKIES ====================
COOKIES_FILE = "cookies.txt"

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": False,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.youtube.com/",
    },
    "extractor_args": {"youtube": {"skip": ["dash", "hls"], "player_client": ["android", "web"]}},
    "retries": 5,
    "fragment_retries": 5,
    "skip_unavailable_fragments": True,
    "cookiefile": COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -hide_banner -loglevel error",
    "options": "-vn -bufsize 512k",
}

# ... (phần còn lại giữ nguyên như code trước)

class YTDLSource(discord.PCMVolumeTransformer):
    ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)
    # ... (giữ nguyên)

# ... (toàn bộ code MusicPlayer, MusicCog, lệnh join, play, skip... giữ nguyên như bản trước)

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

@bot.event
async def on_ready():
    print(f"[OK] Bot online: {bot.user}")
    if os.path.exists(COOKIES_FILE):
        print("[OK] Cookies đã được load từ cookies.txt")
    else:
        print("[WARNING] Không tìm thấy cookies.txt - một số video có thể bị chặn")
    try:
        await bot.add_cog(MusicCog(bot))
        synced = await bot.tree.sync()
        print(f"[OK] Synced {len(synced)} commands.")
    except Exception as e:
        print(f"[ERROR] Sync failed: {e}")
        traceback.print_exc()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/play"))

# ... (phần còn lại giữ nguyên)

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("[ERROR] Chưa có DISCORD_TOKEN!")
        exit(1)
    bot.run(BOT_TOKEN)
