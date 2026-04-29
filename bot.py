import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
queues = {}
current_song = {}

# ====================== THÔNG BÁO JOIN/LEAVE ======================
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    log_channel_id = int(os.getenv("LOG_CHANNEL_ID", "0"))
    log_channel = bot.get_channel(log_channel_id)
    if not log_channel:
        return

    now = datetime.now().strftime("%H:%M")
    avatar_url = member.display_avatar.url

    if before.channel is None and after.channel is not None:
        embed = discord.Embed(title="Tham gia Voice Chat", color=discord.Color.green())
        embed.set_thumbnail(url=avatar_url)
        embed.description = f"{member.mention} đã tham gia voice chat **{after.channel.name}**"
        embed.set_footer(text=f"• Hôm nay lúc {now}")
        await log_channel.send(embed=embed)

    elif before.channel is not None and after.channel is None:
        embed = discord.Embed(title="Rời Voice Chat", color=discord.Color.red())
        embed.set_thumbnail(url=avatar_url)
        embed.description = f"{member.mention} đã rời voice chat"
        embed.set_footer(text=f"• Hôm nay lúc {now}")
        await log_channel.send(embed=embed)

# ====================== KẾT NỐI VOICE BỀN ======================
async def connect_voice_robust(ctx, channel, max_retries=5):
    for attempt in range(1, max_retries + 1):
        try:
            if ctx.voice_client:
                if ctx.voice_client.channel == channel:
                    return ctx.voice_client
                await ctx.voice_client.disconnect(force=True)
                await asyncio.sleep(1)
            vc = await channel.connect(timeout=30.0, reconnect=True)
            await asyncio.sleep(2)
            return vc
        except Exception as e:
            if attempt < max_retries:
                await ctx.send(f"⏳ Thử lại lần {attempt}...")
                await asyncio.sleep(4 * attempt)
            else:
                await ctx.send("🚫 Không kết nối được voice.")
                return None

# ====================== PLAY + XỬ LÝ LỖI 403 ======================
@bot.command(name="play", aliases=["p", "phat"])
async def play(ctx, *, search: str):
    if not ctx.author.voice or not ctx.author.voice.channel:
        return await ctx.send("❌ Bạn phải vào Voice Channel trước!")

    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening,
        name=f"Đang tìm: {search[:45]}"
    ))

    vc = await connect_voice_robust(ctx, ctx.author.voice.channel)
    if not vc:
        return

    # ====================== LINK MP3 TRỰC TIẾP ======================
    direct_audio_ext = ('.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac')
    if search.lower().startswith('http') and search.lower().endswith(direct_audio_ext):
        url = search
        title = search.split('/')[-1].split('?')[0]
        await ctx.send(f"🎵 Đang phát link trực tiếp: **{title}**")

        source = discord.FFmpegOpusAudio(url, before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5')
        guild_id = ctx.guild.id
        if vc.is_playing() or vc.is_paused():
            if guild_id not in queues:
                queues[guild_id] = []
            queues[guild_id].append((url, title, "N/A"))
            await ctx.send(f"📝 Đã thêm: **{title}**")
        else:
            def after_play(e):
                asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
            vc.play(source, after=after_play)
            current_song[guild_id] = (title, "N/A")
            await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f"Đang phát: {title[:40]}"))
            await ctx.send(f"🎵 **Đang phát:** {title}")
        return

    await ctx.send(f"🔍 Đang tìm: **{search}**")

    # ====================== YTDLP VỚI XỬ LÝ 403 ======================
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'default_search': 'ytsearch',
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        },
        'extractor_args': {
            'youtube': {
                'player_client': ['web', 'android']
            }
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search, download=False)
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg or "Sign in" in error_msg or "not a bot" in error_msg:
            return await ctx.send("❌ Link này bị chặn (403). Hãy thử gõ **tên bài hát** thay vì dán link nhé!\nVí dụ: `!play lofi chill`")
        return await ctx.send(f"❌ Lỗi: {error_msg[:80]}")

    url = info.get('url')
    title = info.get('title', 'Unknown Track')
    duration = info.get('duration_string', 'N/A')

    if not url:
        return await ctx.send("❌ Không tìm thấy audio!")

    source = discord.FFmpegOpusAudio(
        url,
        before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
    )

    guild_id = ctx.guild.id
    if vc.is_playing() or vc.is_paused():
        if guild_id not in queues:
            queues[guild_id] = []
        queues[guild_id].append((url, title, duration))
        await ctx.send(f"📝 Đã thêm: **{title}** ({duration})")
    else:
        def after_play(e):
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
        vc.play(source, after=after_play)
        current_song[guild_id] = (title, duration)
        await bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=f"Đang phát: {title[:40]} ({duration})"
        ))
        await ctx.send(f"🎵 **Đang phát:** {title} ({duration})")

async def play_next(ctx):
    guild_id = ctx.guild.id
    vc = ctx.voice_client
    if not vc or not vc.is_connected():
        return
    if guild_id in queues and queues[guild_id]:
        url, title, duration = queues[guild_id].pop(0)
        def after_play(e):
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
        vc.play(discord.FFmpegOpusAudio(url, before_options='-reconnect 1 -reconnect_streamed 1'), after=after_play)
        current_song[guild_id] = (title, duration)
        await bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=f"Đang phát: {title[:40]} ({duration})"
        ))
        await ctx.send(f"🎵 Tiếp: **{title}** ({duration})")
    else:
        current_song.pop(guild_id, None)
        await bot.change_presence(activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="Nhạc hay 🎵"
        ))
        await asyncio.sleep(90)
        if vc.is_connected() and not vc.is_playing():
            await vc.disconnect()
            await ctx.send("👋 Hết nhạc, bot rời kênh.")

# ====================== LỆNH KHÁC ======================
@bot.command(name="skip", aliases=["s"])
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Đã skip!")
    else:
        await ctx.send("❌ Không có nhạc đang phát!")

@bot.command(name="queue", aliases=["q"])
async def show_queue(ctx):
    guild_id = ctx.guild.id
    if guild_id in queues and queues[guild_id]:
        msg = "**📋 Hàng đợi:**\n"
        for i, (_, title, duration) in enumerate(queues[guild_id], 1):
            msg += f"{i}. {title} ({duration})\n"
        await ctx.send(msg)
    else:
        await ctx.send("📭 Queue trống!")

@bot.command(name="nowplaying", aliases=["np"])
async def nowplaying(ctx):
    guild_id = ctx.guild.id
    if guild_id in current_song:
        title, duration = current_song[guild_id]
        await ctx.send(f"🎶 **Đang phát:** {title} ({duration})")
    else:
        await ctx.send("❌ Không có nhạc đang phát!")

@bot.command(name="leave", aliases=["stop"])
async def leave(ctx):
    if ctx.voice_client:
        queues.pop(ctx.guild.id, None)
        current_song.pop(ctx.guild.id, None)
        await ctx.voice_client.disconnect()
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Nhạc hay 🎵"))
        await ctx.send("👋 Bot đã rời!")
    else:
        await ctx.send("❌ Bot không ở trong voice!")

@bot.command(name="help")
async def help_cmd(ctx):
    embed = discord.Embed(title="🎵 Bot Nhạc (Tự động xử lý lỗi 403)", color=0x1DB954)
    embed.add_field(name="!play <tên bài>", value="Tìm YouTube (khuyến nghị - ít lỗi nhất)", inline=False)
    embed.add_field(name="!play <link mp3>", value="Phát link trực tiếp (mp3, wav...)", inline=False)
    embed.add_field(name="!skip / !s", value="Bỏ qua bài", inline=False)
    embed.add_field(name="!queue / !q", value="Xem hàng đợi", inline=False)
    embed.add_field(name="!nowplaying / !np", value="Bài đang phát", inline=False)
    embed.add_field(name="!leave / !stop", value="Rời voice", inline=False)
    embed.set_footer(text="Mẹo: Dùng tên bài thay vì link để tránh lỗi 403")
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} đã online!")
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening,
        name="Nhạc hay 🎵"
    ))

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))
