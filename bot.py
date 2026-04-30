import discord
from discord.ext import commands
import random
import datetime

# ==================== CẤU HÌNH ====================
# Thay YOUR_BOT_TOKEN bằng token thật của bot (lấy từ https://discord.com/developers/applications)
TOKEN = "YOUR_BOT_TOKEN_HERE"

# Prefix lệnh
PREFIX = "!"

# ==================== BOT SETUP ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Để lấy thông tin thành viên

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ==================== DANH SÁCH LỆNH (HELP) ====================
COMMANDS_LIST = """
**🎉 LỆNH VUI VẺ & TIỆN ÍCH (KHÔNG CÓ LỆNH MODERATION NHƯ KICK/BAN)**

`!ping` - Kiểm tra độ trễ bot
`!hello` / `!chào` - Bot chào bạn
`!info` - Thông tin bot
`!joke` / `!truyen` - Kể chuyện cười (tiếng Việt)
`!8ball` / `!hoi` - Hỏi 8ball (câu trả lời ngẫu nhiên)
`!roll` / `!xucxac` - Tung xúc xắc (1-6)
`!coin` / `!tungxu` - Tung đồng xu (Ngửa/Sấp)
`!random` / `!ngaunhien` - Số ngẫu nhiên từ 1-100
`!avatar` - Xem ảnh đại diện của bạn hoặc người khác
`!userinfo` / `!thongtin` - Thông tin người dùng
`!serverinfo` - Thông tin server
`!say` - Lặp lại lời bạn nói (dùng embed)
`!embed` - Tạo embed đẹp với tiêu đề + nội dung
`!meme` - Gửi meme ngẫu nhiên (link sẵn)
`!fact` / `!suthat` - Sự thật thú vị
`!love` / `!tinhyeu` - Tính % tình yêu giữa 2 người
`!rps` / `!keobuabao` - Chơi Kéo - Búa - Bao với bot

**Cách dùng:** Gõ lệnh + prefix `!` ví dụ: `!ping`

Bot được tạo bởi Grok AI - Không có lệnh kick, ban, mute hay bất kỳ lệnh quản trị nào!
"""

# ==================== SỰ KIỆN ====================
@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} đã online thành công!")
    print(f"📌 Prefix: {PREFIX}")
    print(f"🌐 Đang phục vụ {len(bot.guilds)} server(s)")
    await bot.change_presence(activity=discord.Game(name="Vui vẻ cùng bạn | !help"))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Lệnh không tồn tại! Gõ `!help` để xem danh sách lệnh.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Thiếu tham số! Hãy kiểm tra lại lệnh.")
    else:
        await ctx.send(f"⚠️ Có lỗi xảy ra: {error}")

# ==================== LỆNH CƠ BẢN ====================
@bot.command(aliases=["chào"])
async def hello(ctx):
    await ctx.send(f"👋 Xin chào {ctx.author.mention}! Chúc bạn một ngày vui vẻ nhé! ❤️")

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Độ trễ: **{latency}ms**")

@bot.command()
async def info(ctx):
    embed = discord.Embed(
        title="🤖 Thông tin Bot",
        description="Bot Discord vui vẻ - Không có lệnh quản trị!",
        color=discord.Color.blue()
    )
    embed.add_field(name="📌 Prefix", value=PREFIX, inline=True)
    embed.add_field(name="📚 Số lệnh", value="15+ lệnh vui", inline=True)
    embed.add_field(name="👨‍💻 Tác giả", value="Grok AI (xAI)", inline=True)
    embed.add_field(name="⏰ Uptime", value="Luôn online 24/7", inline=True)
    embed.set_footer(text="Cảm ơn bạn đã sử dụng bot!")
    await ctx.send(embed=embed)

@bot.command(aliases=["help", "trogiup"])
async def help_command(ctx):
    embed = discord.Embed(
        title="📖 DANH SÁCH LỆNH",
        description=COMMANDS_LIST,
        color=discord.Color.green()
    )
    embed.set_footer(text="Bot không có lệnh kick/ban/mute - An toàn cho mọi server!")
    await ctx.send(embed=embed)

# ==================== LỆNH VUI VẺ ====================
JOKES = [
    "Tại sao con gà qua đường? Để sang bên kia đường!",
    "Con mèo đi đâu? Đi săn chuột chứ đi đâu!",
    "Tại sao bác sĩ không thích chơi bài? Vì họ sợ bị 'tim'!",
    "Con voi đi tắm bằng gì? Bằng vòi hoa sen chứ bằng gì!",
    "Tại sao sách bị ướt? Vì nó bị 'ướt át' quá!",
    "Con cá đi học về kể gì? 'Hôm nay con được 'cá' điểm 10!'",
    "Tại sao quả táo không bao giờ cô đơn? Vì nó có 'hạt'!",
    "Con vịt đi đâu? Đi 'vịt' chơi chứ đi đâu!",
    "Tại sao máy tính bị cảm cúm? Vì nó bị virus!",
    "Con chim đi tắm bằng gì? Bằng nước 'chim' chứ!"
]

@bot.command(aliases=["truyen", "cuoi"])
async def joke(ctx):
    joke = random.choice(JOKES)
    await ctx.send(f"😂 **Chuyện cười:**\n{joke}")

BALL_ANSWERS = [
    "✅ Có, chắc chắn rồi!",
    "❌ Không, đừng mơ!",
    "🤔 Có lẽ... nhưng không chắc lắm",
    "🌟 Rất có thể!",
    "💀 Không đời nào!",
    "✨ Tương lai sáng lạn đấy!",
    "😅 Hỏi lại sau đi...",
    "🔥 Đúng rồi, làm đi!",
    "💔 Không nên đâu bạn ơi",
    "🎉 Hoàn toàn đúng!"
]

@bot.command(aliases=["hoi", "ball"])
async def ball(ctx, *, question: str = None):
    if not question:
        await ctx.send("❓ Bạn hỏi gì đi! Ví dụ: `!8ball Tôi có giàu không?`")
        return
    answer = random.choice(BALL_ANSWERS)
    embed = discord.Embed(
        title="🎱 8-Ball Dự Đoán",
        description=f"**Câu hỏi:** {question}\n\n**Trả lời:** {answer}",
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed)

@bot.command(aliases=["xucxac"])
async def roll(ctx, sides: int = 6):
    if sides < 2:
        await ctx.send("❌ Xúc xắc phải có ít nhất 2 mặt!")
        return
    result = random.randint(1, sides)
    await ctx.send(f"🎲 Bạn tung xúc xắc {sides} mặt → Kết quả: **{result}**")

@bot.command(aliases=["tungxu"])
async def coin(ctx):
    result = random.choice(["🪙 Ngửa", "🪙 Sấp"])
    await ctx.send(f"💰 Kết quả tung đồng xu: **{result}**")

@bot.command(aliases=["ngaunhien"])
async def random_num(ctx, min_num: int = 1, max_num: int = 100):
    if min_num >= max_num:
        await ctx.send("❌ Số tối thiểu phải nhỏ hơn số tối đa!")
        return
    result = random.randint(min_num, max_num)
    await ctx.send(f"🎰 Số ngẫu nhiên từ {min_num} đến {max_num}: **{result}**")

# ==================== LỆNH THÔNG TIN ====================
@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(
        title=f"🖼️ Ảnh đại diện của {member.display_name}",
        color=discord.Color.random()
    )
    embed.set_image(url=member.avatar.url if member.avatar else member.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command(aliases=["thongtin"])
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(
        title=f"👤 Thông tin của {member.display_name}",
        color=discord.Color.blue()
    )
    embed.add_field(name="🆔 ID", value=member.id, inline=True)
    embed.add_field(name="📅 Tham gia Discord", value=member.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="📅 Tham gia Server", value=member.joined_at.strftime("%d/%m/%Y") if member.joined_at else "N/A", inline=True)
    embed.add_field(name="🎭 Vai trò cao nhất", value=member.top_role.name, inline=True)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(
        title=f"🏰 Thông tin Server: {guild.name}",
        color=discord.Color.green()
    )
    embed.add_field(name="👑 Chủ server", value=guild.owner, inline=True)
    embed.add_field(name="👥 Thành viên", value=guild.member_count, inline=True)
    embed.add_field(name="📅 Tạo ngày", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="🆔 Server ID", value=guild.id, inline=True)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    await ctx.send(embed=embed)

# ==================== LỆNH KHÁC ====================
@bot.command()
async def say(ctx, *, message: str):
    embed = discord.Embed(
        description=message,
        color=discord.Color.random()
    )
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    await ctx.send(embed=embed)

@bot.command()
async def embed(ctx, title: str, *, description: str):
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)

MEMES = [
    "https://i.imgur.com/3oX3f5K.jpg",
    "https://i.imgur.com/8Q5vK9L.jpg",
    "https://i.imgur.com/2pXvL3M.jpg",
    "https://i.imgur.com/9R4tN2P.jpg",
    "https://i.imgur.com/5vK8mL2.jpg"
]

@bot.command()
async def meme(ctx):
    meme_url = random.choice(MEMES)
    embed = discord.Embed(title="😂 Meme ngẫu nhiên", color=discord.Color.orange())
    embed.set_image(url=meme_url)
    await ctx.send(embed=embed)

FACTS = [
    "🦒 Hươu cao cổ có lưỡi dài 50cm và có thể liếm tai mình!",
    "🐙 Bạch tuộc có 3 trái tim và máu màu xanh!",
    "🌍 Trái Đất là hành tinh duy nhất có nước ở dạng lỏng!",
    "🐼 Gấu trúc con sinh ra chỉ nặng khoảng 100 gram!",
    "⚡ Sét nóng hơn bề mặt mặt trời gấp 5 lần!"
]

@bot.command(aliases=["suthat"])
async def fact(ctx):
    fact_text = random.choice(FACTS)
    await ctx.send(f"📚 **Sự thật thú vị:**\n{fact_text}")

@bot.command(aliases=["tinhyeu"])
async def love(ctx, person1: str = None, person2: str = None):
    if not person1 or not person2:
        await ctx.send("💕 Dùng: `!love Tên1 Tên2` ví dụ: `!love Minh Lan`")
        return
    percent = random.randint(10, 100)
    if percent > 80:
        msg = "💖 Tình yêu hoàn hảo! Cưới nhau đi!"
    elif percent > 50:
        msg = "💕 Tình yêu khá tốt đấy!"
    else:
        msg = "💔 Chưa đủ duyên... thử lại sau nhé!"
    await ctx.send(f"💘 **Tình yêu giữa {person1} và {person2}:** {percent}%\n{msg}")

@bot.command(aliases=["keobuabao", "rps"])
async def rps(ctx, choice: str = None):
    if not choice:
        await ctx.send("✊ Dùng: `!rps kéo` hoặc `búa` hoặc `bao`")
        return
    
    choices = ["kéo", "búa", "bao"]
    user_choice = choice.lower()
    
    if user_choice not in choices:
        await ctx.send("❌ Chỉ được chọn: kéo, búa hoặc bao!")
        return
    
    bot_choice = random.choice(choices)
    result = ""
    
    if user_choice == bot_choice:
        result = "🤝 Hòa!"
    elif (user_choice == "kéo" and bot_choice == "bao") or \
         (user_choice == "búa" and bot_choice == "kéo") or \
         (user_choice == "bao" and bot_choice == "búa"):
        result = "🎉 Bạn thắng!"
    else:
        result = "😢 Bot thắng!"
    
    await ctx.send(f"✊ **Bạn chọn:** {user_choice}\n🤖 **Bot chọn:** {bot_choice}\n\n**Kết quả:** {result}")

# ==================== CHẠY BOT ====================
if __name__ == "__main__":
    if TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("⚠️ VUI LÒNG THAY 'YOUR_BOT_TOKEN_HERE' BẰNG TOKEN THẬT CỦA BẠN!")
        print("📌 Cách lấy token: https://discord.com/developers/applications → New Application → Bot → Token")
    else:
        bot.run(TOKEN)
