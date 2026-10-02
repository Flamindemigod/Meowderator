from disnake.ext import commands
from typing import Optional
import disnake
import os
import sqlite3

ROLE_ID = 1547935758579404891
ESO_CONTENT = 809610729497165865
ESO_CONTENT_BACKUP = 1360246602895200407

intents = disnake.Intents.default()
intents.message_content = True

bot = commands.InteractionBot(intents=intents)


db = sqlite3.connect("temprl.db")
db.execute(
    """
    CREATE TABLE IF NOT EXISTS channel_users (
        channel_id INTEGER PRIMARY KEY,
        user_id INTEGER NOT NULL
    )
    """
)
db.commit()

async def backup_message(message: disnake.Message):
    source_channel = message.channel
    source_category: Optional[str] = source_channel.category.name if source_channel.category else None
    target_category: Optional[disnake.CategoryChannel] = None
    target_guild = bot.get_guild(ESO_CONTENT_BACKUP)
    if source_category:
        target_category = disnake.utils.get(target_guild.categories, name=source_category)
        if not target_category:
            target_category = await target_guild.create_category(source_category)
    # Handle threads
    if isinstance(source_channel, disnake.Thread):
        parent_channel: disnake.TextChannel = source_channel.parent
        target_parent: Optional[disnake.TextChannel] = disnake.utils.get(
            target_guild.text_channels,
            name=parent_channel.name,
            category=target_category
        )
        if not target_parent:
            target_parent = await target_guild.create_text_channel(
                parent_channel.name,
                category=target_category
            )
        target_thread: Optional[disnake.Thread] = disnake.utils.get(
            target_parent.threads,
            name=source_channel.name
        )
        if not target_thread:
            target_thread = await target_parent.create_thread(
                name=source_channel.name,
                type=source_channel.type
            )
        destination_channel = target_thread
    elif isinstance(source_channel, disnake.ForumChannel):
        target_forum: Optional[disnake.ForumChannel] = disnake.utils.get(
            target_guild.forums,
            name=source_channel.name,
            category=target_category
        )
        if not target_forum:
            target_forum = await target_guild.create_forum(
                source_channel.name,
                category=target_category
            )
        target_thread: Optional[disnake.Thread] = disnake.utils.get(
            target_forum.threads,
            name=source_channel.name
        )
        if not target_thread:
            target_thread = await target_forum.create_post(
                name=f"{source_channel.name} «{source.author.display_name}»",
                type=source_channel.type
            )
        destination_channel = target_thread
    else:
        target_channel: Optional[disnake.TextChannel] = disnake.utils.get(target_guild.text_channels, name=source_channel.name, category=target_category)
        if not target_channel:
            target_channel = await target_guild.create_text_channel(source_channel.name, category=target_category)
        destination_channel = target_channel
    if message.embeds[0]:
        embed = message.embeds[0]
    else:
        embed = disnake.Embed(description = message.content, color=disnake.Color.blue())
    embed.set_author(name=f"{message.author.display_name} «{message.author.id}»", icon_url=message.author.display_avatar.url)
    embed.set_footer(text=f"{message.id}")
    files: list[disnake.File] = [
        await attachment.to_file() for attachment in message.attachments
    ]
    if message.reference:
        original_message = message.reference.resolved
        if original_message:
            embed.add_field(
                name="Reply to",
                value=f"[{original_message.author.display_name}](https://discord.com/channels/{message.guild.id}/{message.channel.id}/{original_message.id}): {original_message.content[:100]}",
                inline=False
            )
    await destination_channel.send(embed=embed, files=files)

@bot.event
async def on_message(message: disnake.Message):
    if message.guild and message.guild.id == ESO_CONTENT:
        await backup_message(message)

async def find_backup_message(destination_channel: disnake.TextChannel, original_message_id: int):
    async for msg in destination_channel.history(limit=100):
        if msg.embeds and msg.embeds[0].footer.text == str(original_message_id):
            return msg
    return None

async def backup_message_deleted(message: disnake.Message):
    source_channel = message.channel
    source_category: Optional[str] = source_channel.category.name if source_channel.category else None
    target_category: Optional[disnake.CategoryChannel] = None
    target_guild = bot.get_guild(ESO_CONTENT_BACKUP)
    if source_category:
        target_category = disnake.utils.get(target_guild.categories, name=source_category)
        if not target_category:
            return None
    if isinstance(source_channel, disnake.Thread):
        parent_channel: disnake.TextChannel = source_channel.parent
        target_parent: Optional[disnake.TextChannel] = disnake.utils.get(
            target_guild.text_channels,
            name=parent_channel.name,
            category=target_category
        )
        if not target_parent:
            return None
        target_thread: Optional[disnake.Thread] = disnake.utils.get(
            target_parent.threads,
            name=source_channel.name
        )
        if not target_thread:
            return None
        destination_channel = target_thread
    elif isinstance(source_channel, disnake.ForumChannel):
        target_forum: Optional[disnake.ForumChannel] = disnake.utils.get(
            target_guild.forums,
            name=source_channel.name,
            category=target_category
        )
        if not target_forum:
            return None
        target_thread: Optional[disnake.Thread] = disnake.utils.get(
            target_forum.threads,
            name=source_channel.name
        )
        if not target_thread:
            return None
        destination_channel = target_thread
    else:
        target_channel: Optional[disnake.TextChannel] = disnake.utils.get(target_guild.text_channels, name=source_channel.name, category=target_category)
        if not target_channel:
            target_channel = await target_guild.create_text_channel(source_channel.name, category=target_category)
        destination_channel = target_channel

    backup_message: Optional[disnake.Message] = await find_backup_message(destination_channel, message.id)
    if backup_message:
        old_embed = backup_message.embeds[0]
        old_embed.color = disnake.Color.red()
        old_embed.add_field(
            name="Deleted",
            value=f"**at <t:{int(disnake.utils.utcnow().timestamp())}:f>**",
            inline=False
        )
        await backup_message.edit(embed=old_embed)


@bot.event
async def on_message_delete(message: disnake.Message):
    if message.guild and message.guild.id == ESO_CONTENT:
        await backup_message_deleted(message)

async def remove_temprl_role(
    channel: disnake.abc.GuildChannel,
    reason: str,
):
    row = db.execute(
        "SELECT user_id FROM channel_users WHERE channel_id = ?",
        (channel.id,),
    ).fetchone()

    if row is None:
        return

    user_id = row[0]
    role = channel.guild.get_role(ROLE_ID)

    if role is not None:
        try:
            member = await channel.guild.fetch_member(user_id)
            await member.remove_roles(role, reason=reason)
        except disnake.NotFound:
            print(f"User {user_id} is no longer in the server.")
        except disnake.Forbidden:
            print("Could not remove the role. Check the bot's permissions.")

    db.execute(
        "DELETE FROM channel_users WHERE channel_id = ?",
        (channel.id,),
    )
    db.commit()

@bot.slash_command(
    name="temprl",
    description="Give a user temporary moderation access in this channel",
)
@commands.has_role("Admin")
async def temprl(
    inter: disnake.ApplicationCommandInteraction,
    user: disnake.Member = commands.Param(
        description="The user to give access to"
    ),
):
    if inter.guild is None:
        await inter.response.send_message(
            "This command can only be used in a server.",
            ephemeral=True,
        )
        return

    role = inter.guild.get_role(ROLE_ID)

    if role is None:
        await inter.response.send_message(
            "The configured role does not exist in this server.",
            ephemeral=True,
        )
        return

    try:
        await user.add_roles(
            role,
            reason=f"/temprl used by {inter.author}",
        )

        await inter.channel.set_permissions(
            user,
            overwrite=disnake.PermissionOverwrite(
                manage_channels=True,
                manage_messages=True,
                manage_permissions=True,
                manage_threads=True,
                send_polls=True,
                pin_messages=True,
                bypass_slowmode=True,
                mention_everyone=True,
            ),
            reason=f"/temprl used by {inter.author}",
        )

        db.execute(
            """
            INSERT INTO channel_users (channel_id, user_id)
            VALUES (?, ?)
            ON CONFLICT(channel_id)
            DO UPDATE SET user_id = excluded.user_id
            """,
            (inter.channel.id, user.id),
        )
        db.commit()

        await inter.response.send_message(
            f"Granted {user.mention} moderation access in this channel.",
            ephemeral=True,
        )

    except disnake.Forbidden:
        await inter.response.send_message(
            "I do not have permission to manage that role or channel.",
            ephemeral=True,
        )


@bot.event
async def on_guild_channel_update(
    before: disnake.abc.GuildChannel,
    after: disnake.abc.GuildChannel,
):
    if before.category_id != after.category_id:
        await remove_temprl_role(
            after,
            "Channel was moved to a different category",
        )

@bot.event
async def on_guild_channel_delete(
    channel: disnake.abc.GuildChannel,
):
    await remove_temprl_role(
        channel,
        "Temporary channel was deleted",
    )

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

bot.run(os.environ["DISCORD_TOKEN"])
