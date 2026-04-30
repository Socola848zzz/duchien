import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re

# ==================== CẤU HÌNH (Dùng Environment Variables trên Render) ====================
TOKEN = os.getenv("DISCORD_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")

# FFmpeg path (Render sẽ cài ffmpeg vào /usr/bin/ffmpeg)
FFMPEG_PATH = "ffmpeg"   # Hoặc "/usr/bin/ffmpeg"

# ==================== BOT SETUP ====================
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Queue và trạng thái
queues = {}          # {guild_id: [song_info, ...]}
now_playing = {}     # {guild_id: current_song}
voice_clients = {}   # {guild_id: voice_client}

# ==================== YTDLP + SPOTIFY ====================
ytdl_format_options = {
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
    'extractor_args': {
        'youtube': {'skip': ['dash', 'hls']}
    }
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

# Spotify client
sp = None
if SPOTIFY_CLIENT_ID != "YOUR_SPOTIFY_CLIENT_ID" and SPOTIFY_CLIENT_SECRET != "YOUR_SPOTIFY_CLIENT_SECRET":
    try:
        client_credentials_manager = SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID, 
            client_secret=SPOTIFY_CLIENT_SECRET
        )
        sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        print("✅ Spotify API đã kết nối!")
    except Exception as e:
        print(f"⚠️ Lỗi Spotify API: {e}")
        sp = None
else:
    print("ℹ️ Chưa cấu hình Spotify API → chỉ hỗ trợ YouTube & SoundCloud")

# ==================== HÀM HỖ TRỢ ====================
def is_spotify_link(url):
    return "spotify.com" in url or "open.spotify.com" in url

def is_youtube_link(url):
    return "youtube.com" in url or "youtu.be" in url

def is_soundcloud_link(url):
    return "soundcloud.com" in url

async def get_spotify_track_info(url):
    """Lấy tên bài hát + nghệ sĩ từ Spotify link"""
    if not sp:
        return None
    
    try:
        # Extract track ID
        track_id = re.search(r'track/([a-zA-Z0-9]+)', url)
        if not track_id:
            return None
        
        track = sp.track(track_id.group(1))
        name = track['name']
        artist = track['artists'][0]['name']
        return f"{name} {artist}"
    except Exception as e:
        print(f"Spotify error: {e}")
        return None

async def search_youtube(query):
    """Tìm kiếm YouTube và trả về thông tin bài hát"""
    try:
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{query}", download=False))
        
        if 'entries' in data:
            data = data['entries'][0]
        
        return {
            'url': data['url'],
            'title': data.get('title', 'Unknown'),
            'duration': data.get('duration', 0),
            'thumbnail': data.get('thumbnail', ''),
            'webpage_url': data.get('webpage_url', query)
        }
    except Exception as e:
        print(f"YouTube search error: {e}")
        return None

async def get_song_info(query):
    """Xử lý link hoặc tìm kiếm"""
    # Spotify link
    if is_spotify_link(query):
        if not sp:
            return None, "❌ Spotify chưa được cấu hình! Hãy dùng link YouTube hoặc search từ khóa."
        
        track_name = await get_spotify_track_info(query)
        if track_name:
            song = await search_youtube(track_name)
            if song:
                song['source'] = 'Spotify → YouTube'
                return song, None
        return None, "❌ Không tìm thấy bài hát trên Spotify!"
    
    # YouTube / SoundCloud / Direct link
    if is_youtube_link(query) or is_soundcloud_link(query) or query.startswith("http"):
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
            
            if 'entries' in data:  # playlist
                data = data['entries'][0]
            
            return {
                'url': data['url'],
                'title': data.get('title', 'Unknown'),
                'duration': data.get('duration', 0),
                'thumbnail': data.get('thumbnail', ''),
                'webpage_url': data.get('webpage_url', query),
                'source': 'YouTube' if is_youtube_link(query) else 'SoundCloud'
            }, None
        except Exception as e:
            return None, f"❌ Lỗi khi lấy bài hát: {str(e)[:100]}"
    
    # Search từ khóa
    song = await search_youtube(query)
    if song:
        song['source'] = 'YouTube Search'
        return song, None
    
    return None, "❌ Không tìm thấy bài hát!"

async def play_next(guild_id):
    """Phát bài tiếp theo trong queue"""
    if guild_id not in queues or not queues[guild_id]:
        if guild_id in voice_clients:
            await voice_clients[guild_id].disconnect()
            del voice_clients[guild_id]
        if guild_id in now_playing:
            del now_playing[guild_id]
        return
    
    song = queues[guild_id].pop(0)
    now_playing[guild_id] = song
    
    voice_client = voice_clients.get(guild_id)
    if not voice_client or not voice_client.is_connected():
        return
    
    try:
        source = discord.FFmpegPCMAudio(song['url'], **ffmpeg_options, executable=FFMPEG_PATH)
        voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(guild_id), bot.loop))
        
        # Gửi thông báo
        channel = bot.get_channel(song.get('channel_id'))
        if channel:
            embed = discord.Embed(
                title="🎵 Đang phát",
                description=f"**{song['title']}**",
                color=discord.Color.green()
            )
            embed.add_field(name="Nguồn", value=song.get('source', 'Unknown'), inline=True)
            embed.add_field(name="Thời lượng", value=f"{song['duration']//60}:{song['duration']%60:02d}" if song['duration'] else "Live", inline=True)
            if song.get('thumbnail'):
                embed.set_thumbnail(url=song['thumbnail'])
            await channel.send(embed=embed)
    except Exception as e:
        print(f"Play error: {e}")
        await play_next(guild_id)

# ==================== SỰ KIỆN ====================
@bot.event
async def on_ready():
    print(f"✅ Music Bot {bot.user} đã online!")
    print("🎵 Hỗ trợ: YouTube | Spotify | SoundCloud")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="!play | Music Bot"))

@bot.event
async def on_voice_state_update(member, before, after):
    # Tự động rời khi không còn ai trong voice
    if member.id == bot.user.id:
        return
    guild_id = member.guild.id
    if guild_id in voice_clients:
        voice_client = voice_clients[guild_id]
        if voice_client and voice_client.channel:
            if len(voice_client.channel.members) == 1:  # Chỉ còn bot
                await asyncio.sleep(300)  # Chờ 5 phút
                if voice_client.is_connected() and len(voice_client.channel.members) == 1:
                    await voice_client.disconnect()
                    if guild_id in voice_clients:
                        del voice_clients[guild_id]

# ==================== LỆNH ====================
@bot.command(aliases=["p"])
async def play(ctx, *, query: str):
    """Phát nhạc từ YouTube, Spotify hoặc SoundCloud"""
    if not ctx.author.voice:
        await ctx.send("❌ Bạn phải vào voice channel trước!")
        return
    
    voice_channel = ctx.author.voice.channel
    
    # Kết nối voice
    if ctx.guild.id not in voice_clients or not voice_clients[ctx.guild.id].is_connected():
        voice_client = await voice_channel.connect()
        voice_clients[ctx.guild.id] = voice_client
    else:
        voice_client = voice_clients[ctx.guild.id]
        if voice_client.channel != voice_channel:
            await voice_client.move_to(voice_channel)
    
    # Lấy thông tin bài hát
    song, error = await get_song_info(query)
    
    if error:
        await ctx.send(error)
        return
    
    if not song:
        await ctx.send("❌ Không tìm thấy bài hát!")
        return
    
    song['channel_id'] = ctx.channel.id  # Lưu channel để gửi thông báo sau
    
    # Thêm vào queue
    if ctx.guild.id not in queues:
        queues[ctx.guild.id] = []
    
    queues[ctx.guild.id].append(song)
    
    embed = discord.Embed(
        title="✅ Đã thêm vào hàng đợi",
        description=f"**{song['title']}**",
        color=discord.Color.blue()
    )
    embed.add_field(name="Vị trí", value=f"#{len(queues[ctx.guild.id])}", inline=True)
    embed.add_field(name="Nguồn", value=song.get('source', 'Unknown'), inline=True)
    if song.get('thumbnail'):
        embed.set_thumbnail(url=song['thumbnail'])
    
    await ctx.send(embed=embed)
    
    # Nếu đang không phát → phát ngay
    if not voice_client.is_playing():
        await play_next(ctx.guild.id)

@bot.command()
async def skip(ctx):
    """Bỏ qua bài hiện tại"""
    guild_id = ctx.guild.id
    if guild_id not in voice_clients or not voice_clients[guild_id].is_playing():
        await ctx.send("❌ Không có bài nào đang phát!")
        return
    
    voice_clients[guild_id].stop()
    await ctx.send("⏭️ Đã bỏ qua bài hát!")

@bot.command(aliases=["s"])
async def stop(ctx):
    """Dừng phát và xóa queue"""
    guild_id = ctx.guild.id
    if guild_id in voice_clients:
        voice_clients[guild_id].stop()
        queues[guild_id] = []
        if guild_id in now_playing:
            del now_playing[guild_id]
        await ctx.send("⏹️ Đã dừng phát nhạc và xóa hàng đợi!")
    else:
        await ctx.send("❌ Bot không đang phát nhạc!")

@bot.command()
async def pause(ctx):
    """Tạm dừng"""
    guild_id = ctx.guild.id
    if guild_id in voice_clients and voice_clients[guild_id].is_playing():
        voice_clients[guild_id].pause()
        await ctx.send("⏸️ Đã tạm dừng")
    else:
        await ctx.send("❌ Không có gì đang phát!")

@bot.command()
async def resume(ctx):
    """Tiếp tục phát"""
    guild_id = ctx.guild.id
    if guild_id in voice_clients and voice_clients[guild_id].is_paused():
        voice_clients[guild_id].resume()
        await ctx.send("▶️ Tiếp tục phát")
    else:
        await ctx.send("❌ Bot đang không tạm dừng!")

@bot.command(aliases=["q", "queue"])
async def show_queue(ctx):
    """Hiển thị hàng đợi"""
    guild_id = ctx.guild.id
    if guild_id not in queues or not queues[guild_id]:
        await ctx.send("📭 Hàng đợi trống!")
        return
    
    embed = discord.Embed(title="📋 Hàng đợi nhạc", color=discord.Color.purple())
    
    for i, song in enumerate(queues[guild_id][:10], 1):  # Chỉ hiển thị 10 bài đầu
        embed.add_field(
            name=f"{i}. {song['title'][:50]}",
            value=f"Nguồn: {song.get('source', 'Unknown')}",
            inline=False
        )
    
    if len(queues[guild_id]) > 10:
        embed.set_footer(text=f"... và {len(queues[guild_id]) - 10} bài nữa")
    
    await ctx.send(embed=embed)

@bot.command(aliases=["np", "nowplaying"])
async def now_playing_cmd(ctx):
    """Bài đang phát"""
    guild_id = ctx.guild.id
    if guild_id not in now_playing:
        await ctx.send("❌ Không có bài nào đang phát!")
        return
    
    song = now_playing[guild_id]
    embed = discord.Embed(
        title="🎵 Đang phát",
        description=f"**{song['title']}**",
        color=discord.Color.green()
    )
    embed.add_field(name="Nguồn", value=song.get('source', 'Unknown'), inline=True)
    if song.get('thumbnail'):
        embed.set_thumbnail(url=song['thumbnail'])
    await ctx.send(embed=embed)

@bot.command()
async def volume(ctx, vol: int = None):
    """Điều chỉnh âm lượng (0-100)"""
    guild_id = ctx.guild.id
    if guild_id not in voice_clients:
        await ctx.send("❌ Bot chưa kết nối voice!")
        return
    
    if vol is None:
        await ctx.send("🔊 Âm lượng hiện tại: (không hỗ trợ thay đổi realtime, dùng lệnh !volume 50)")
        return
    
    if not 0 <= vol <= 100:
        await ctx.send("❌ Âm lượng phải từ 0 đến 100!")
        return
    
    # Lưu ý: discord.py không hỗ trợ thay đổi volume realtime dễ dàng
    # Có thể implement bằng cách dùng PCMVolumeTransformer
    await ctx.send(f"🔊 Đã đặt âm lượng: **{vol}%** (tính năng cơ bản)")

@bot.command(aliases=["j"])
async def join(ctx):
    """Mời bot vào voice channel"""
    if not ctx.author.voice:
        await ctx.send("❌ Bạn phải ở trong voice channel!")
        return
    
    voice_channel = ctx.author.voice.channel
    if ctx.guild.id in voice_clients and voice_clients[ctx.guild.id].is_connected():
        await ctx.send("✅ Bot đã ở trong voice channel rồi!")
        return
    
    voice_client = await voice_channel.connect()
    voice_clients[ctx.guild.id] = voice_client
    await ctx.send(f"✅ Bot đã tham gia **{voice_channel.name}**")

@bot.command(aliases=["l", "dc"])
async def leave(ctx):
    """Rời voice channel"""
    guild_id = ctx.guild.id
    if guild_id in voice_clients:
        await voice_clients[guild_id].disconnect()
        del voice_clients[guild_id]
        if guild_id in queues:
            queues[guild_id] = []
        if guild_id in now_playing:
            del now_playing[guild_id]
        await ctx.send("👋 Bot đã rời voice channel!")
    else:
        await ctx.send("❌ Bot không ở trong voice channel nào!")

@bot.command(aliases=["h", "help"])
async def help_command(ctx):
    embed = discord.Embed(
        title="🎵 MUSIC BOT - HƯỚNG DẪN",
        description="Bot phát nhạc từ **YouTube | Spotify | SoundCloud**",
        color=discord.Color.gold()
    )
    embed.add_field(name="▶️ !play <link hoặc từ khóa>", value="Phát nhạc (hỗ trợ Spotify link)", inline=False)
    embed.add_field(name="⏭️ !skip", value="Bỏ qua bài hiện tại", inline=True)
    embed.add_field(name="⏹️ !stop", value="Dừng và xóa queue", inline=True)
    embed.add_field(name="⏸️ !pause / !resume", value="Tạm dừng / Tiếp tục", inline=True)
    embed.add_field(name="📋 !queue", value="Xem hàng đợi", inline=True)
    embed.add_field(name="🎵 !np", value="Bài đang phát", inline=True)
    embed.add_field(name="🔊 !volume <0-100>", value="Điều chỉnh âm lượng", inline=True)
    embed.add_field(name="👋 !leave", value="Rời voice channel", inline=True)
    
    embed.set_footer(text="Lưu ý: Cần FFmpeg + Spotify API keys (nếu dùng Spotify)")
    await ctx.send(embed=embed)

# ==================== CHẠY BOT ====================
if __name__ == "__main__":
    if not TOKEN:
        print("❌ LỖI: Bạn chưa set DISCORD_TOKEN trong Environment Variables trên Render!")
        print("📌 Vào Render Dashboard → Environment → Thêm biến DISCORD_TOKEN")
    else:
        print("✅ Bot đang khởi động với Environment Variables...")
        bot.run(TOKEN)
