import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import os
from dotenv import load_dotenv
import traceback
from datetime import datetime, timedelta

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# ==================== CẤU HÌNH VIP 2026 ====================
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# yt-dlp options VIP chống 403 mạnh nhất 2026
ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
    'impersonate': 'chrome',
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'extractor_args': {
        'youtube': {
            'player_client': ['ios', 'android', 'web'],
            'player_skip': ['configs', 'webpage', 'js'],
        }
    },
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
    },
    'sleep_interval': 1,
    'max_sleep_interval': 5,
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin',
    'options': '-vn -af "volume=0.8"'
}

# ==================== CLASS NHẠC ====================
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.thumbnail = data.get('thumbnail')
        self.requester = None

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await loop.run_in_executor(
                    None, lambda: ydl.extract_info(url, download=not stream)
                )
                if 'entries' in info:
                    info = info['entries'][0]
                filename = info['url'] if stream else ydl.prepare_filename(info)
                return cls(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), data=info)
        except yt_dlp.utils.DownloadError as e:
            if "403" in str(e) or "Forbidden" in str(e):
                raise Exception("YOUTUBE_403")
            raise Exception(f"Lỗi tải nhạc: {str(e)}")
        except Exception as e:
            raise Exception(f"Lỗi không xác định: {str(e)}")

# ==================== MUSIC COG ====================
class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}  # guild_id: list of YTDLSource
        self.now_playing = {}  # guild_id: YTDLSource
        self.disconnect_tasks = {}

    def get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]

    async def play_next(self, ctx_or_interaction, voice_client):
        guild_id = ctx_or_interaction.guild.id if hasattr(ctx_or_interaction, 'guild') else ctx_or_interaction.guild_id
        queue = self.get_queue(guild_id)

        if not queue:
            self.now_playing.pop(guild_id, None)
            # Auto disconnect sau 5 phút
            if guild_id not in self.disconnect_tasks:
                task = asyncio.create_task(self.auto_disconnect(voice_client, guild_id))
                self.disconnect_tasks[guild_id] = task
            return

        source = queue.pop(0)
        self.now_playing[guild_id] = source

        def after_playing(error):
            if error:
                print(f"Playback error: {error}")
            coro = self.play_next(ctx_or_interaction, voice_client)
            fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
            try:
                fut.result()
            except:
                pass

        voice_client.play(source, after=after_playing)

        # Gửi embed now playing
        embed = discord.Embed(
            title="🎵 Đang phát",
            description=f"**{source.title}**",
            color=discord.Color.pink()
        )
        if source.thumbnail:
            embed.set_thumbnail(url=source.thumbnail)
        if source.duration:
            embed.add_field(name="Thời lượng", value=str(timedelta(seconds=source.duration)), inline=True)
        embed.set_footer(text=f"Yêu cầu bởi {source.requester.display_name if source.requester else 'Unknown'} • be bo cute VIP 💖")

        if hasattr(ctx_or_interaction, 'response'):
            await ctx_or_interaction.followup.send(embed=embed)
        else:
            await ctx_or_interaction.send(embed=embed)

    async def auto_disconnect(self, voice_client, guild_id):
        await asyncio.sleep(300)  # 5 phút
        if voice_client.is_connected() and not voice_client.is_playing() and len(self.get_queue(guild_id)) == 0:
            await voice_client.disconnect()
            self.disconnect_tasks.pop(guild_id, None)

    @app_commands.command(name="play", description="Phát nhạc từ YouTube (link hoặc tên bài)")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()

        if not interaction.user.voice:
            await interaction.followup.send("❌ Bạn phải vào voice channel trước nhé bé ơi~", ephemeral=True)
            return

        voice_channel = interaction.user.voice.channel
        guild_id = interaction.guild.id

        if guild_id not in self.queues:
            self.queues[guild_id] = []

        try:
            source = await YTDLSource.from_url(query, loop=self.bot.loop, stream=True)
            source.requester = interaction.user

            voice_client = interaction.guild.voice_client
            if not voice_client:
                voice_client = await voice_channel.connect()
            elif voice_client.channel != voice_channel:
                await voice_client.move_to(voice_channel)

            queue = self.get_queue(guild_id)
            if voice_client.is_playing() or voice_client.is_paused():
                queue.append(source)
                embed = discord.Embed(
                    title="➕ Đã thêm vào hàng chờ",
                    description=f"**{source.title}**",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed)
            else:
                queue.append(source)
                await self.play_next(interaction, voice_client)

        except Exception as e:
            error_msg = str(e)
            if "YOUTUBE_403" in error_msg:
                msg = "😭 **YouTube đang chặn mạnh lắm rồi bé ơi!**\n\n" \
                      "Cách fix nhanh:\n" \
                      "1. Upload file `cookies.txt` (xem hướng dẫn bên dưới)\n" \
                      "2. Hoặc thử link khác / dùng từ khóa tìm kiếm\n" \
                      "3. Update bot lên bản VIP này đã giảm 403 rất nhiều rồi!"
            else:
                msg = f"❌ Lỗi: {error_msg}\n\nThử lại sau hoặc liên hệ admin nhé~"
            await interaction.followup.send(msg, ephemeral=True)

    @app_commands.command(name="skip", description="Bỏ qua bài hát hiện tại")
    async def skip(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.is_playing():
            voice_client.stop()
            await interaction.response.send_message("⏭️ Đã skip bài hát!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Không có bài nào đang phát!", ephemeral=True)

    @app_commands.command(name="queue", description="Xem hàng chờ nhạc")
    async def queue(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        queue = self.get_queue(guild_id)
        now = self.now_playing.get(guild_id)

        embed = discord.Embed(title="📋 Hàng chờ nhạc", color=discord.Color.purple())
        if now:
            embed.add_field(name="🎵 Đang phát", value=now.title, inline=False)
        if queue:
            queue_list = "\n".join([f"{i+1}. {song.title}" for i, song in enumerate(queue[:10])])
            embed.add_field(name=f"⏳ Còn {len(queue)} bài", value=queue_list, inline=False)
        else:
            embed.description = "Hàng chờ trống ~"
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="nowplaying", description="Xem bài đang phát")
    async def nowplaying(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        now = self.now_playing.get(guild_id)
        if now:
            embed = discord.Embed(title="🎵 Đang phát", description=now.title, color=discord.Color.pink())
            if now.thumbnail:
                embed.set_thumbnail(url=now.thumbnail)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Không có bài nào đang phát!", ephemeral=True)

    @app_commands.command(name="leave", description="Bot rời voice channel")
    async def leave(self, interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        if voice_client:
            await voice_client.disconnect()
            self.queues.pop(interaction.guild.id, None)
            self.now_playing.pop(interaction.guild.id, None)
            await interaction.response.send_message("👋 Tạm biệt bé ơi~", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Bot không ở trong voice channel!", ephemeral=True)

    @app_commands.command(name="volume", description="Điều chỉnh âm lượng (0-100)")
    async def volume(self, interaction: discord.Interaction, percent: int):
        voice_client = interaction.guild.voice_client
        if voice_client and voice_client.source:
            if 0 <= percent <= 100:
                voice_client.source.volume = percent / 100
                await interaction.response.send_message(f"🔊 Âm lượng: {percent}%", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Âm lượng từ 0 đến 100 thôi bé ơi!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Không có nhạc đang phát!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Music(bot))

# ==================== BOT EVENTS ====================
@bot.event
async def on_ready():
    print(f"✅ {bot.user} đã online! (VIP 2026 - be bo cute)")
    await bot.add_cog(Music(bot))          # ← Dòng quan trọng này bị thiếu!
    try:
        synced = await bot.tree.sync()
        print(f"✅ Đã sync {len(synced)} slash commands")
    except Exception as e:
        print(f"Lỗi sync commands: {e}")

@bot.event
async def on_voice_state_update(member, before, after):
    # Auto leave nếu bot một mình
    if member.id == bot.user.id:
        return
    voice_client = member.guild.voice_client
    if voice_client and len(voice_client.channel.members) == 1:
        await asyncio.sleep(10)
        if voice_client and len(voice_client.channel.members) == 1:
            await voice_client.disconnect()

bot.run(TOKEN)
