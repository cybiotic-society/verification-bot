import os
import secrets
import smtplib
import time
import asyncio
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("cybiotic-bot")

BOT_TOKEN = os.getenv("DISCORD_TOKEN")
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
STUDENT_ROLE_ID = int(os.getenv("STUDENT_ROLE_ID", 0))
ALLOWED_DOMAIN = os.getenv("ALLOWED_DOMAIN", "@student.hh.se")

EXPIRATION_SECONDS = 600
MAX_ATTEMPTS = 3

pending_verifications = {}

intents = discord.Intents.default()
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

def _dispatch_email(to_email: str, code: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your CyBiotic Society Verification Code"
    msg["From"] = formataddr(("CyBiotic Society", GMAIL_USER))
    msg["To"] = to_email

    text_content = (
        f"Hello,\n\n"
        f"Your verification code for CyBiotic Society is: {code}\n"
        f"This code will expire in 10 minutes.\n\n"
        f"To finish your verification, head back to Discord and type:\n"
        f"/confirm code:{code}\n\n"
        f"Best regards,\n"
        f"CyBiotic Society"
    )

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #222;">
        <h2>CyBiotic Society Verification</h2>
        <p>Hello,</p>
        <p>Your one-time verification code is:</p>
        <p style="font-size: 24px; font-weight: bold; letter-spacing: 4px; color: #1e40af;">{code}</p>
        <p>This code is valid for <strong>10 minutes</strong>.</p>
        <p>Enter it in Discord using:</p>
        <code>/confirm code:{code}</code>
        <br><br>
        <p>Best regards,<br><strong>CyBiotic Society</strong></p>
      </body>
    </html>
    """

    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        smtp.sendmail(GMAIL_USER, to_email, msg.as_string())

@client.event
async def on_ready():
    await tree.sync()
    logger.info(f"Authenticated as {client.user} (ID: {client.user.id})")

@tree.command(name="verify", description="Verify your membership using your student email")
@app_commands.describe(email="Your university email ending in @student.hh.se")
async def verify(interaction: discord.Interaction, email: str):
    await interaction.response.defer(ephemeral=True)

    email_clean = email.strip().lower()

    if not email_clean.endswith(ALLOWED_DOMAIN):
        await interaction.followup.send(
            f"Invalid email domain. Please provide an official `{ALLOWED_DOMAIN}` address.",
            ephemeral=True
        )
        return

    code = f"{secrets.randbelow(900000) + 100000}"
    pending_verifications[interaction.user.id] = {
        "code": code,
        "email": email_clean,
        "expires_at": time.time() + EXPIRATION_SECONDS,
        "attempts": 0
    }

    try:
        await asyncio.to_thread(_dispatch_email, email_clean, code)
        await interaction.followup.send(
            f"A 6-digit verification code has been dispatched to `{email_clean}`.\n"
            f"The code remains valid for 10 minutes.\n\n"
            f"Run `/confirm code:<your_code>` to complete verification.\n"
            f"*(If you do not see it in your inbox shortly, please check your junk or spam folder.)*",
            ephemeral=True
        )
    except Exception as err:
        logger.error(f"Failed to deliver verification email: {err}")
        await interaction.followup.send(
            "Unable to deliver the email right now. Please reach out to an administrator for assistance.",
            ephemeral=True
        )

@tree.command(name="confirm", description="Confirm your 6-digit verification code")
@app_commands.describe(code="The 6-digit code received via email")
async def confirm(interaction: discord.Interaction, code: str):
    await interaction.response.defer(ephemeral=True)

    uid = interaction.user.id
    input_code = code.strip()

    session = pending_verifications.get(uid)
    if not session:
        await interaction.followup.send(
            "No active verification request found. Start by running `/verify`.",
            ephemeral=True
        )
        return

    if time.time() > session["expires_at"]:
        pending_verifications.pop(uid, None)
        await interaction.followup.send(
            "Your code has expired. Please run `/verify` to request a fresh code.",
            ephemeral=True
        )
        return

    if input_code != session["code"]:
        session["attempts"] += 1
        remaining = MAX_ATTEMPTS - session["attempts"]

        if remaining <= 0:
            pending_verifications.pop(uid, None)
            await interaction.followup.send(
                "Too many invalid attempts. This session has been cancelled. Please run `/verify` again.",
                ephemeral=True
            )
            return

        await interaction.followup.send(
            f"Incorrect code. You have {remaining} attempt(s) remaining.",
            ephemeral=True
        )
        return

    role = interaction.guild.get_role(STUDENT_ROLE_ID)
    member = interaction.guild.get_member(uid)

    if not member:
        member = await interaction.guild.fetch_member(uid)

    if role and member:
        try:
            await member.add_roles(role)
            pending_verifications.pop(uid, None)
            logger.info(f"Verified member: {interaction.user} ({session['email']})")
            await interaction.followup.send(
                "Verification confirmed. The student role has been assigned to your account.",
                ephemeral=True
            )
        except discord.errors.Forbidden:
            logger.error("Missing permissions: bot cannot assign role (hierarchy issue).")
            await interaction.followup.send(
                "Role assignment failed due to permission settings. Please notify an administrator.",
                ephemeral=True
            )
    else:
        logger.warning(f"Could not locate role {STUDENT_ROLE_ID} or member {uid}.")
        await interaction.followup.send(
            "Could not locate the assigned role on this server. Check server role configuration.",
            ephemeral=True
        )

if __name__ == "__main__":
    client.run(BOT_TOKEN)