import os
import discord
import asyncio
from datetime import datetime
from discord.ext import commands
import google.generativeai as genai
from dotenv import load_dotenv
from aiohttp import web
import aiohttp
import threading
import json

load_dotenv()

# -----------------------
# Configure Discord bot
# -----------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# -----------------------
# Configure Gemini API
# -----------------------
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')
backup_model = genai.GenerativeModel('gemini-1.5-flash')

# -----------------------
# Server rules and guidelines
# -----------------------
SERVER_RULES = """
 1. Core Identity

| Key | Value |
|-----|-------|
| Server Name | Reddit Tasks |
| Purpose | Paid Reddit interaction tasks: posts, comments, upvotes, reports, polls |
| Moderator | <@703280080213901342> and <@772380971940184064> |
| Currency | USD — paid via UPI or Crypto (USDT BEP20 only) |

---

 2. Roles

| Role         | Color      | Description |
|--------------|------------|-------------|
| @mod     | Pink/Red   | Full permissions (task distribution, verification, payouts) |
| <@&1381564210277912667> | Green      | Given after Reddit verification; unlocks full access |
| (No @unverified) | — | New users don't have a role but can still see onboarding channels |

---

 3. Channel Visibility

| Channel            | Emoji | Visible To             | Notes |
|--------------------|-------|------------------------|-------|
| `#modlog`          | 🔒     | Mods only              | moderation logs |
| <#1382588462372356286> | 📜     | Verified               | Full rules |
| <#1378979634351439872> | 📢     | Verified               | Task alerts & payout updates |
| <#1379815484056277044> | 💬     | Verified               | Chat and support |
| `#📊-polls`         | 📊     | Verified               | Server votes |
| `#💡-suggestions`   | 💡     | Verified               | Community input |
| `#❗-warnings`       | ❗     | Verified               | Lists user infractions |
| `#❓-faqs`           | ❓     | Verified               | Common beginner questions |
| `#🛠️-support`       | 🛠️     | Verified               | Task help/disputes |
| `#ℹ️-info`          | ℹ️     | Verified               | Guides, how-tos |
| <#1382657321641181236> | 📁     | Verified               | Task winner names and rates |
| `#📁-rep-posts`     | 📁     | Verified               | Tasked user logs |
| `#📁-comment-task-1`| 📁     | Verified               | OneTimeSecret comment feed |
| `#📁-comment-task-2`| 📁     | Verified               | Alternate stream |
| `#📁-post-task`     | 📁     | Verified               | OneTimeSecret post feed |
| `#📁-voting-task`   | 📁     | Verified               | Vote/report/poll actions |
| `#👋-start-here`     | 👋     | New users (no role)    | Welcome message & steps |
| `#✅-verify-here`   | ✅     | New users (no role)    | Post Reddit profile for access |
| <#1379449977587236927> | 💵     | New users (no role)    | Payout proofs + payment notes |

---

 4. Verification Process

1. New users see only:  
   - `#👋start-here`  
   - `#✅verify-here`  
   - `#💵payments`

2. They post their Reddit profile URL:
```
https://www.reddit.com/user/yourusername
```

3. Requirements:
   - ≥ 50 total Reddit karma
   - Unsuspended Reddit account

4. If approved, Mods reacts ✅ → user gets <@&1381564210277912667> and unlocks full server

## 5. Task Types & Limits

| Task Type       | Payout     | Per Day (Per Account) |
|-----------------|------------|------------------------|
| 📝 Post Task     | $0.30–$0.50| 1                      |
| 💬 Comment Task  | $0.20      | 3                      |
| 🔼 Voting/Report | $0.05–$0.10| No fixed limit         |

Rules:
- Content must be copy-pasted exactly
- Do not edit or paraphrase task instructions
- Join subreddit and wait 30 seconds before posting
- Use Reddit in browser mode, even on mobile
- Track tasks in a Google Sheet

 6. Task Assignment Methods

| Method | Description |
|--------|-------------|
| Tally Form | Link posted in <#1382657321641181236> ; closes when full |
| Giveaway Bot | React to join, bot DMs winners |
| OneTimeSecret | First user to click the link sees the task |

⚠️ All tasks are first-come, first-serve

 7. Proof Submission

- Send permalink of your Reddit comment/post to <@703280080213901342>
- Or upload it into your Google Sheet (if requested)
- For voting/reporting tasks, a screenshot is required
- Removed/flagged content = no payment

 8. Payment System

| Item          | Details                     |
|---------------|-----------------------------|
| Methods   | UPI (India), USDT (BEP20 only) |
| Min Amount| UPI: none, Crypto: $2       |
| Payout Day| Every Monday (IST)      |
| Submit Records | DM <@703280080213901342> on Saturday/Sunday |
| Proof     | Post screenshot in `#💵payments` |

❌ No PayPal supported

 9. Warning System

| Event                     | Result                        |
|---------------------------|-------------------------------|
| 1st–5th warning           | Logged in `#❗-warnings`       |
| After 5th warning         | Every warning = 1-day mute|
| Serious violations        | Possible ban                  |

Muted users cannot do tasks during timeout.

10. Bot Answering Guidelines

When this server's AI bot responds to questions, it should:

- Pull accurate data from this file
- Never give out forms or task links directly
- Never promise payments or exceptions
- Redirect users to <@703280080213901342> or <@772380971940184064> for disputes
- Mention task limits where relevant
- Use friendly and concise language with emojis
"""

# -----------------------
# Web Server for Health Checks
# -----------------------
class WebServer:
    def __init__(self):
        self.app = web.Application()
        self.setup_routes()
        self.start_time = datetime.now()
        
    def setup_routes(self):
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_head('/health', self.health_check_head)
        self.app.router.add_get('/favicon.ico', self.favicon)
        self.app.router.add_head('/favicon.ico', self.favicon_head)
        self.app.router.add_get('/status', self.status)
        
    async def index(self, request):
        return web.json_response({
            'status': 'online',
            'service': 'Discord Bot - Reddit Tasks Helper',
            'uptime': str(datetime.now() - self.start_time).split('.')[0],
            'timestamp': datetime.now().isoformat()
        })
    
    async def health_check(self, request):
        """Health check endpoint for uptime monitoring"""
        try:
            # Check if bot is connected
            bot_status = bot.is_ready() if bot else False
            
            health_data = {
                'status': 'healthy' if bot_status else 'degraded',
                'bot_ready': bot_status,
                'uptime': str(datetime.now() - self.start_time).split('.')[0],
                'timestamp': datetime.now().isoformat(),
                'servers': len(bot.guilds) if bot and bot.is_ready() else 0,
                'latency': round(bot.latency * 1000) if bot and bot.is_ready() else None
            }
            
            status_code = 200 if bot_status else 503
            return web.json_response(health_data, status=status_code)
            
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }, status=500)
    
    async def health_check_head(self, request):
        """Handle HEAD requests for health check"""
        try:
            bot_status = bot.is_ready() if bot else False
            status_code = 200 if bot_status else 503
            return web.Response(status=status_code)
        except Exception:
            return web.Response(status=500)
    
    async def favicon(self, request):
        """Handle favicon requests"""
        return web.Response(status=204)  # No Content
    
    async def favicon_head(self, request):
        """Handle HEAD requests for favicon"""
        return web.Response(status=204)  # No Content
    
    async def status(self, request):
        """Detailed status endpoint"""
        try:
            return web.json_response({
                'service': 'Discord Bot - Reddit Tasks Helper',
                'status': 'online',
                'bot_ready': bot.is_ready() if bot else False,
                'uptime': str(datetime.now() - self.start_time).split('.')[0],
                'servers': len(bot.guilds) if bot and bot.is_ready() else 0,
                'latency': f"{round(bot.latency * 1000)}ms" if bot and bot.is_ready() else None,
                'timestamp': datetime.now().isoformat(),
                'version': '1.0.0'
            })
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }, status=500)

# -----------------------
# Bot Cog
# -----------------------
class DiscordBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now()

    @discord.app_commands.command(name="info", description="Get information about the bot")
    async def info(self, interaction: discord.Interaction):
        """Display bot information"""
        uptime = datetime.now() - self.start_time
        uptime_str = str(uptime).split('.')[0]

        embed = discord.Embed(
            title="🤖 Bot Information",
            color=0x58b9ff,
            timestamp=datetime.now()
        )
        embed.add_field(name="Bot Name", value="Reddit Tasks - Helper", inline=True)
        embed.add_field(name="Version", value="1.0.0", inline=True)
        embed.add_field(name="Creator", value="<@788580226401566791>", inline=True)
        embed.add_field(name="Uptime", value=uptime_str, inline=True)
        embed.add_field(name="Servers", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Ping", value=f"{round(self.bot.latency*1000)}ms", inline=True)
        embed.add_field(
            name="What I Do",
            value="• Answer your questions in simple terms\n"
                  "• Help you understand server rules\n"
                  "• Provide clear step-by-step guidance\n"
                  "• Available 24/7 to help!",
            inline=False
        )
        embed.add_field(
            name="Commands",
            value="`/info` - Show this information\n"
                  "`/askquestion` - Ask any question",
            inline=False
        )
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")

        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="askquestion", description="Ask any question and get an AI-powered answer")
    async def ask_question(self, interaction: discord.Interaction, question: str):
        """Handle user questions using Gemini API"""
        await interaction.response.defer()
        prompt = f"""
You are a Discord server assistant bot. Your ONLY job is to help users understand server rules and procedures based on the provided information.

CRITICAL INSTRUCTIONS:
1. ONLY answer based on the server rules provided below
2. If the question is NOT covered in the server rules, say "I don't have specific information about that in our server rules. Please ask in <#1379815484056277044> or ping <@703280080213901342> for help."
3. NEVER make up information, dates, prices, or procedures not mentioned in the rules
4. NEVER assume or guess about policies
5. If unsure about any detail, direct users to ask moderators

SERVER RULES AND INFORMATION:
{SERVER_RULES}

USER QUESTION: {question}

RESPONSE GUIDELINES:
- Answer ONLY what's explicitly stated in the server rules above
- Use simple, beginner-friendly language
- Give step-by-step instructions when the rules provide them
- If the question asks about something not in the rules, respond with: "I don't have that information in our server rules. Please ask in <#1379815484056277044> or DM <@703280080213901342> for help."
- For rule violations, explain what the rule says and why it exists
- Keep responses under 300 words
- Never mention payment amounts, dates, or procedures unless they're exactly as written in the rules

FORBIDDEN ACTIONS:
- Do NOT create new rules or procedures
- Do NOT give specific dates unless mentioned in rules
- Do NOT provide technical Discord help not related to server rules
- Do NOT guess about moderator decisions
- Do NOT provide general life advice unrelated to server operations

If the question is completely unrelated to server rules or operations, respond: "I'm designed to help with server rules and procedures only. For other questions, please ask in <#1379815484056277044>."
"""
        try:
            response = model.generate_content(prompt)
            answer = response.text.strip()
            # Basic validation
            if not answer or len(answer) < 10:
                raise ValueError("Empty or too-short response")
            # Detect too-generic replies
            generic_phrases = ["i don't know", "i'm not sure", "it depends", "generally speaking"]
            if any(phrase in answer.lower() for phrase in generic_phrases) and "server rules" not in answer.lower():
                answer = "I don't have specific information about that in our server rules. Please ask in <#1379815484056277044> or DM <@703280080213901342> for help."
        except Exception as primary_error:
            print(f"Primary API failed: {primary_error}")
            # Fallback to backup
            try:
                backup_key = os.getenv('GEMINI_BACKUP_API_KEY')
                if backup_key:
                    genai.configure(api_key=backup_key)
                    backup_resp = backup_model.generate_content(prompt)
                    answer = backup_resp.text.strip() or \
                             "I couldn't generate a proper response. Please ask in <#1379815484056277044> or DM <@703280080213901342> for help."
                else:
                    answer = "I'm having trouble with my AI service. Please ask in <#1379815484056277044> or DM <@703280080213901342> for help."
            except Exception as backup_error:
                print(f"Backup API failed: {backup_error}")
                answer = "❌ I'm having trouble connecting to my AI service right now. Please ask in <#1379815484056277044> or DM <@703280080213901342> for help!"

        # Send answer in an embed
        answer_embed = discord.Embed(
            title="📝 Your Answer",
            description=answer,
            color=0x58b9ff,
            timestamp=datetime.now()
        )
        answer_embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        await interaction.followup.send(embed=answer_embed)

    @ask_question.error
    async def ask_question_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """Handle errors for the ask_question command"""
        if isinstance(error, discord.app_commands.MissingPermissions):
            if interaction.response.is_done():
                await interaction.followup.send("❌ You don't have permission to use this command.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        else:
            if interaction.response.is_done():
                await interaction.followup.send("❌ An error occurred while processing your command.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ An error occurred while processing your command.", ephemeral=True)

# -----------------------
# Bot event handlers & startup
# -----------------------
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} servers')
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} commands')
    except Exception as e:
        print(f'Failed to sync commands: {e}')

@bot.event
async def on_guild_join(guild):
    print(f'Joined new server: {guild.name} (ID: {guild.id})')

@bot.event
async def on_guild_remove(guild):
    print(f'Left server: {guild.name} (ID: {guild.id})')

@bot.event
async def on_error(event, *args, **kwargs):
    print(f'An error occurred in {event}: {args}, {kwargs}')

# -----------------------
# Main function
# -----------------------
async def run_web_server():
    """Run the web server for health checks"""
    try:
        web_server = WebServer()
        port = int(os.getenv('PORT', 10000))
        
        print(f"Starting web server on port {port}")
        runner = web.AppRunner(web_server.app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        print(f"Web server started on http://0.0.0.0:{port}")
        
        # Keep the server running
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        print(f"Error starting web server: {e}")

async def run_discord_bot():
    """Run the Discord bot"""
    try:
        await bot.add_cog(DiscordBot(bot))
        
        discord_token = os.getenv('DISCORD_TOKEN')
        if not discord_token:
            print("Error: DISCORD_TOKEN environment variable not set")
            return
            
        await bot.start(discord_token)
        
    except Exception as e:
        print(f"Error starting Discord bot: {e}")

async def main():
    """Main function to run both web server and Discord bot"""
    try:
        # Run both the web server and Discord bot concurrently
        await asyncio.gather(
            run_web_server(),
            run_discord_bot(),
            return_exceptions=True
        )
    except KeyboardInterrupt:
        print("Shutting down...")
    except Exception as e:
        print(f"Error in main: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Fatal error: {e}")
