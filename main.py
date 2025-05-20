import discord
from discord.ext import commands
import json, os, aiohttp, io
from PIL import Image, ImageDraw, ImageFont, ImageOps
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        exit(1)

# Load config
config = load_config()

# Bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# MongoDB setup
try:
    client = AsyncIOMotorClient(config["mongodb_uri"])
    db = client["levelbot"]
    levels_collection = db["levels"]
    settings_collection = db["settings"]
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    exit(1)

async def get_guild_settings(guild_id: int) -> dict:
    settings = await settings_collection.find_one({"guild_id": guild_id})
    if not settings:
        settings = {
            "guild_id": guild_id,
            "level_channel_id": None
        }
        await settings_collection.insert_one(settings)
    return settings

def generate_rank_card(username, level, xp, max_xp, avatar_img):
    try:
        # Card dimensions and setup
        card_width = 934
        card_height = 282
        card = Image.open("assets/background.png").convert("RGBA")
        card = card.resize((card_width, card_height))
        draw = ImageDraw.Draw(card)

        # Font setup with larger sizes
        font_username = ImageFont.truetype("assets/font.ttf", 60)
        font_stats = ImageFont.truetype("assets/font.ttf", 40)

        # Avatar setup with larger size
        avatar_size = 200
        avatar_img = avatar_img.resize((avatar_size, avatar_size)).convert("RGBA")
        
        # Create circular mask for avatar
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        avatar_img.putalpha(mask)
        
        # Position avatar
        avatar_x = 40
        avatar_y = (card_height - avatar_size) // 2
        card.paste(avatar_img, (avatar_x, avatar_y), avatar_img)

        # Text positioning with better spacing
        text_x = avatar_x + avatar_size + 50
        username_y = 50
        level_y = username_y + 70
        xp_y = level_y + 55

        # Draw text elements
        draw.text((text_x, username_y), username, font=font_username, fill="white")
        draw.text((text_x, level_y), f"Level: {level} / {config['max_level']}", font=font_stats, fill="white")
        draw.text((text_x, xp_y), f"XP: {xp} / {max_xp}", font=font_stats, fill="white")

        # Progress bar with improved size
        bar_width = 550
        bar_height = 30
        bar_x = text_x
        bar_y = xp_y + 50

        # Draw progress bar
        draw.rectangle(
            [bar_x, bar_y, bar_x + bar_width, bar_y + bar_height],
            fill=(80, 80, 80, 255)
        )
        
        fill = int((xp / max_xp) * bar_width)
        draw.rectangle(
            [bar_x, bar_y, bar_x + fill, bar_y + bar_height],
            fill=(0, 200, 255, 255)
        )

        buffer = io.BytesIO()
        card.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"Error generating rank card: {e}")
        return None

def get_required_xp(level):
    return 100 + (level * 5)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await bot.change_presence(
        status=discord.Status.dnd,
        activity=discord.Activity(type=discord.ActivityType.watching, name=config["bot_status"])
    )

@bot.command()
@commands.has_permissions(administrator=True)
async def setlevelchannel(ctx, channel: discord.TextChannel):
    """Set the channel for level up notifications"""
    await settings_collection.update_one(
        {"guild_id": ctx.guild.id},
        {"$set": {"level_channel_id": channel.id}},
        upsert=True
    )
    await ctx.send(f"Level channel set to {channel.mention}")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    try:
        user_data = await levels_collection.find_one({
            "guild_id": message.guild.id,
            "user_id": message.author.id
        })

        if not user_data:
            user_data = {
                "guild_id": message.guild.id,
                "user_id": message.author.id,
                "xp": 0,
                "level": 1
            }
            await levels_collection.insert_one(user_data)

        new_xp = user_data.get("xp", 0) + config["xp_per_message"]
        current_level = user_data.get("level", 1)
        required_xp = get_required_xp(current_level)
        leveled_up = False

        while new_xp >= required_xp and current_level < config["max_level"]:
            new_xp -= required_xp
            current_level += 1
            leveled_up = True
            required_xp = get_required_xp(current_level)

        await levels_collection.update_one(
            {"guild_id": message.guild.id, "user_id": message.author.id},
            {"$set": {"xp": new_xp, "level": current_level}}
        )

        if leveled_up:
            settings = await get_guild_settings(message.guild.id)
            level_channel_id = settings.get("level_channel_id")
            
            if level_channel_id:
                level_channel = bot.get_channel(level_channel_id)
                if level_channel:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(str(message.author.display_avatar.url)) as resp:
                            if resp.status == 200:
                                avatar_data = await resp.read()
                                avatar_img = Image.open(io.BytesIO(avatar_data))

                                buffer = generate_rank_card(
                                    str(message.author),
                                    current_level,
                                    new_xp,
                                    get_required_xp(current_level),
                                    avatar_img
                                )
                                if buffer:
                                    file = discord.File(buffer, filename="rank.png")
                                    await level_channel.send(
                                        f"{message.author.mention} leveled up to **Level {current_level}**!",
                                        file=file
                                    )

    except Exception as e:
        print(f"Error in on_message: {e}")

    await bot.process_commands(message)

@bot.command()
async def rank(ctx):
    """Show your current rank"""
    try:
        user_data = await levels_collection.find_one({
            "guild_id": ctx.guild.id,
            "user_id": ctx.author.id
        })

        if not user_data:
            await ctx.send("You don't have any XP yet!")
            return

        async with aiohttp.ClientSession() as session:
            async with session.get(str(ctx.author.display_avatar.url)) as resp:
                if resp.status == 200:
                    avatar_data = await resp.read()
                    avatar_img = Image.open(io.BytesIO(avatar_data))

                    buffer = generate_rank_card(
                        str(ctx.author),
                        user_data["level"],
                        user_data["xp"],
                        get_required_xp(user_data["level"]),
                        avatar_img
                    )
                    if buffer:
                        file = discord.File(buffer, filename="rank.png")
                        await ctx.send(file=file)

    except Exception as e:
        print(f"Error in rank command: {e}")
        await ctx.send("An error occurred while generating your rank card.")

if __name__ == "__main__":
    try:
        bot.run(config["token"])
    except Exception as e:
        print(f"Error starting bot: {e}")