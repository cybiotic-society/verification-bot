# cybiotic-verification-bot

Discord bot for CyBiotic Society that verifies Halmstad University students before granting them access to the server.

The bot confirms that a user owns an active `@student.hh.se` email address by dispatching a one-time verification code.

## How It Works

1. A user runs `/verify email:username@student.hh.se` in Discord.
2. The bot validates the domain and emails a 6-digit code to the student address.
3. The code remains valid for 10 minutes (maximum 3 attempts before the session resets).
4. The user runs `/confirm code:123456` in Discord.
5. The bot checks the code and automatically assigns the student role.

All bot responses in Discord are ephemeral (only visible to the user running the command).

## Tech Stack

- Python 3
- discord.py
- Brevo API (handles email delivery over HTTPS)
- Railway (hosting and deployment)

## Environment Variables

Create a `.env` file in the root directory (or set them in Railway under Variables):

```env
DISCORD_TOKEN=your_discord_token
STUDENT_ROLE_ID=your_student_role_id
ALLOWED_DOMAIN=@student.hh.se
BREVO_API_KEY=your_brevo_api_key
GMAIL_USER=your@email.com

# Local Setup

Clone the repository:  
`git clone https://github.com/your-username/cybiotic-verification-bot.git`  
`cd cybiotic-verification-bot`  

Create and activate a virtual environment:  
`python -m venv venv`  

Windows:  
`.\venv\Scripts\activate`  

Linux/macOS:  
`source venv/bin/activate`  

Install dependencies:  
`pip install -r requirements.txt`  

Start the bot:  
`python bot.py`  

# Discord Role Hierarchy Note

The bot's own role on the Discord server must be placed higher in the role list than the role it assigns (STUDENT_ROLE_ID). Otherwise, Discord's permission system prevents the bot from granting the role.