import os
import sqlite3

import disnake
from disnake.ext import commands

ROLE_ID = 1547935758579404891

bot = commands.InteractionBot()


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
