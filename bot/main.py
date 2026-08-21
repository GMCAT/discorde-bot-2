import asyncio
import logging
import os
import re

import discord
from discord import app_commands
from dotenv import load_dotenv

from bot.contracts import ServiceRequest
from bot.services import AdminService, ContactService


load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)
MESSAGE_LIMIT = 2_000


def split_message(message: str) -> list[str]:
    chunks = []
    while len(message) > MESSAGE_LIMIT:
        cut = message.rfind("\n", 0, MESSAGE_LIMIT)
        cut = cut if cut > 0 else MESSAGE_LIMIT
        chunks.append(message[:cut])
        message = message[cut:].lstrip("\n")
    if message:
        chunks.append(message)
    return chunks


class DiscordContactsBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.contacts = ContactService()
        admin_ids = {item.strip() for item in os.getenv("DISCORD_ADMIN_USER_IDS", "").split(",") if item.strip()}
        self.admin = AdminService(admin_ids)
        self.prefixes = tuple(item.strip() for item in os.getenv("DISCORD_TRIGGER_PREFIXES", "บอท,bot,!").split(",") if item.strip())

    async def setup_hook(self):
        guild_id = os.getenv("DISCORD_GUILD_ID", "").strip()
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def execute(self, service, command: str, interaction_or_message) -> list[str]:
        request = ServiceRequest(
            "discord", str(interaction_or_message.channel_id if isinstance(interaction_or_message, discord.Interaction) else interaction_or_message.channel.id),
            str(interaction_or_message.user.id if isinstance(interaction_or_message, discord.Interaction) else interaction_or_message.author.id),
            command, {"platform": "discord"},
        )
        try:
            response = await asyncio.to_thread(service.handle, request)
            messages = response.message if isinstance(response.message, list) else [response.message]
            return [chunk for message in messages for chunk in split_message(message)]
        except Exception:
            logger.exception("Service %s failed", service.name)
            return ["ขออภัยครับ ระบบฐานข้อมูลไม่พร้อมใช้งานชั่วคราว"]

    async def on_message(self, message: discord.Message):
        if message.author.bot or not self.user:
            return
        text = message.content.strip()
        if message.guild:
            mention = re.compile(rf"^<@!?{self.user.id}>\s*")
            if mention.match(text):
                text = mention.sub("", text, count=1).strip()
            else:
                prefix = next((item for item in self.prefixes if text.lower().startswith(item.lower())), None)
                if not prefix:
                    return
                text = text[len(prefix):].strip()
        service = self.contacts if text == "ติดต่อฉุกเฉิน" or text.startswith("ติดต่อ ") else self.admin if text in {"ข้อมูลทั้งหมด", "ตรวจฐานข้อมูล", "เพิ่มติดต่อ"} or text.startswith("เพิ่มติดต่อ\n") else None
        if not service:
            return
        for reply in await self.execute(service, text, message):
            await message.channel.send(reply, allowed_mentions=discord.AllowedMentions.none())


bot = DiscordContactsBot()


async def send_interaction(interaction, service, command, ephemeral=False):
    await interaction.response.defer(thinking=True, ephemeral=ephemeral)
    replies = await bot.execute(service, command, interaction)
    for reply in replies:
        await interaction.followup.send(reply, ephemeral=ephemeral, allowed_mentions=discord.AllowedMentions.none())


@bot.tree.command(name="contact", description="ค้นหาผู้ติดต่อ")
async def contact(interaction: discord.Interaction, query: str):
    await send_interaction(interaction, bot.contacts, f"ติดต่อ {query}")


@bot.tree.command(name="emergency", description="ดูผู้ติดต่อฉุกเฉิน")
async def emergency(interaction: discord.Interaction):
    await send_interaction(interaction, bot.contacts, "ติดต่อฉุกเฉิน")


@bot.tree.command(name="add-contact", description="เพิ่มผู้ติดต่อ (เฉพาะแอดมิน)")
async def add_contact(interaction: discord.Interaction, name: str, organization: str, phone: str | None = None, email: str | None = None, position: str | None = None, contact_type: str = "ทั่วไป", role: str = "สำรอง", available_24h: bool = False):
    values = {"ชื่อ": name, "หน่วยงาน": organization, "เบอร์": phone, "อีเมล": email, "ตำแหน่ง": position, "ประเภท": contact_type, "บทบาท": role, "24ชม": "ใช่" if available_24h else "ไม่"}
    command = "เพิ่มติดต่อ\n" + "\n".join(f"{key}: {value}" for key, value in values.items() if value is not None)
    await send_interaction(interaction, bot.admin, command, True)


@bot.tree.command(name="database-status", description="ตรวจฐานข้อมูล (เฉพาะแอดมิน)")
async def database_status(interaction: discord.Interaction):
    await send_interaction(interaction, bot.admin, "ตรวจฐานข้อมูล", True)


@bot.tree.command(name="all-contacts", description="ดูผู้ติดต่อทั้งหมด (เฉพาะแอดมิน)")
async def all_contacts(interaction: discord.Interaction):
    await send_interaction(interaction, bot.admin, "ข้อมูลทั้งหมด", True)


def main():
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("กรุณาตั้ง DISCORD_BOT_TOKEN")
    bot.run(token)


if __name__ == "__main__":
    main()
