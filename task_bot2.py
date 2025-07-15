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
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables with fallbacks
try:
    load_dotenv()
except Exception as e:
    logger.warning(f"Could not load .env file: {e}")

# -----------------------
# Environment Variables with Fallbacks
# -----------------------
def get_env_var(key, default=None, required=False):
    """Get environment variable with fallback and validation"""
    try:
        value = os.getenv(key, default)
        if required and not value:
            logger.error(f"Required environment variable {key} is not set")
            if key == 'DISCORD_TOKEN':
                raise ValueError(f"Required environment variable {key} is missing")
        return value
    except Exception as e:
        logger.error(f"Error getting environment variable {key}: {e}")
        return default

DISCORD_TOKEN = get_env_var('DISCORD_TOKEN', required=True)
GEMINI_API_KEY = get_env_var('GEMINI_API_KEY')
GEMINI_BACKUP_API_KEY = get_env_var('GEMINI_BACKUP_API_KEY')
PORT = int(get_env_var('PORT', '10000'))

# -----------------------
# Configure Discord bot with fallbacks
# -----------------------
try:
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='!', intents=intents)
    logger.info("Discord bot configured successfully")
except Exception as e:
    logger.error(f"Error configuring Discord bot: {e}")
    # Create a minimal bot instance as fallback
    try:
        intents = discord.Intents.default()
        bot = commands.Bot(command_prefix='!', intents=intents)
        logger.info("Discord bot configured with minimal intents")
    except Exception as e2:
        logger.critical(f"Failed to create Discord bot instance: {e2}")
        raise

# -----------------------
# Configure Gemini API with fallbacks
# -----------------------
model = None
backup_model = None

def configure_gemini():
    """Configure Gemini API with fallback handling"""
    global model, backup_model
    
    try:
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Primary Gemini model configured successfully")
        else:
            logger.warning("GEMINI_API_KEY not provided")
    except Exception as e:
        logger.error(f"Error configuring primary Gemini model: {e}")
        model = None
    
    try:
        if GEMINI_BACKUP_API_KEY:
            backup_model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Backup Gemini model configured successfully")
        else:
            logger.warning("GEMINI_BACKUP_API_KEY not provided")
    except Exception as e:
        logger.error(f"Error configuring backup Gemini model: {e}")
        backup_model = None

configure_gemini()

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
# Web Server with comprehensive fallbacks
# -----------------------
class WebServer:
    def __init__(self):
        try:
            self.app = web.Application()
            self.setup_routes()
            self.start_time = datetime.now()
            logger.info("Web server initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing web server: {e}")
            # Create minimal app as fallback
            try:
                self.app = web.Application()
                self.app.router.add_get('/ping', self.ping)
                self.start_time = datetime.now()
                logger.info("Web server initialized with minimal routes")
            except Exception as e2:
                logger.critical(f"Failed to create web server: {e2}")
                raise
        
    def setup_routes(self):
        """Setup all web server routes with error handling"""
        try:
            self.app.router.add_get('/', self.index)
            self.app.router.add_get('/health', self.health_check)
            self.app.router.add_head('/health', self.health_check_head)
            self.app.router.add_get('/ping', self.ping)
            self.app.router.add_head('/ping', self.ping_head)
            self.app.router.add_get('/favicon.ico', self.favicon)
            self.app.router.add_head('/favicon.ico', self.favicon_head)
            self.app.router.add_get('/status', self.status)
            logger.info("All web server routes configured successfully")
        except Exception as e:
            logger.error(f"Error setting up routes: {e}")
            # Setup minimal routes as fallback
            try:
                self.app.router.add_get('/ping', self.ping)
                logger.info("Minimal routes configured successfully")
            except Exception as e2:
                logger.error(f"Failed to setup minimal routes: {e2}")

    async def ping(self, request):
        """Ping endpoint that returns 'Bot is Online❇️'"""
        try:
            return web.Response(text="Bot is Online❇️", status=200)
        except Exception as e:
            logger.error(f"Error in ping endpoint: {e}")
            return web.Response(text="Bot is Online❇️", status=200)

    async def ping_head(self, request):
        """Handle HEAD requests for ping"""
        try:
            return web.Response(status=200)
        except Exception:
            return web.Response(status=200)
        
    async def index(self, request):
        """Main index endpoint"""
        try:
            uptime = str(datetime.now() - self.start_time).split('.')[0] if self.start_time else "unknown"
            return web.json_response({
                'status': 'online',
                'service': 'Discord Bot - Reddit Tasks Helper',
                'uptime': uptime,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Error in index endpoint: {e}")
            return web.json_response({
                'status': 'online',
                'service': 'Discord Bot - Reddit Tasks Helper',
                'error': 'partial_failure'
            })
    
    async def health_check(self, request):
        """Health check endpoint for uptime monitoring"""
        try:
            # Safe bot status check
            bot_status = False
            latency = None
            servers = 0
            
            try:
                if bot:
                    bot_status = bot.is_ready()
                    if bot_status:
                        latency = round(bot.latency * 1000)
                        servers = len(bot.guilds)
            except Exception as e:
                logger.warning(f"Error checking bot status: {e}")
            
            uptime = str(datetime.now() - self.start_time).split('.')[0] if self.start_time else "unknown"
            
            health_data = {
                'status': 'healthy' if bot_status else 'degraded',
                'bot_ready': bot_status,
                'uptime': uptime,
                'timestamp': datetime.now().isoformat(),
                'servers': servers,
                'latency': latency
            }
            
            status_code = 200 if bot_status else 503
            return web.json_response(health_data, status=status_code)
            
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            return web.json_response({
                'status': 'error',
                'error': 'health_check_failed',
                'timestamp': datetime.now().isoformat()
            }, status=500)
    
    async def health_check_head(self, request):
        """Handle HEAD requests for health check"""
        try:
            bot_status = False
            try:
                if bot:
                    bot_status = bot.is_ready()
            except Exception:
                pass
            
            status_code = 200 if bot_status else 503
            return web.Response(status=status_code)
        except Exception:
            return web.Response(status=500)
    
    async def favicon(self, request):
        """Handle favicon requests"""
        try:
            return web.Response(status=204)
        except Exception:
            return web.Response(status=204)
    
    async def favicon_head(self, request):
        """Handle HEAD requests for favicon"""
        try:
            return web.Response(status=204)
        except Exception:
            return web.Response(status=204)
    
    async def status(self, request):
        """Detailed status endpoint"""
        try:
            # Safe data collection
            bot_ready = False
            servers = 0
            latency = None
            
            try:
                if bot:
                    bot_ready = bot.is_ready()
                    if bot_ready:
                        servers = len(bot.guilds)
                        latency = f"{round(bot.latency * 1000)}ms"
            except Exception as e:
                logger.warning(f"Error getting bot status: {e}")
            
            uptime = str(datetime.now() - self.start_time).split('.')[0] if self.start_time else "unknown"
            
            return web.json_response({
                'service': 'Discord Bot - Reddit Tasks Helper',
                'status': 'online',
                'bot_ready': bot_ready,
                'uptime': uptime,
                'servers': servers,
                'latency': latency,
                'timestamp': datetime.now().isoformat(),
                'version': '1.0.0'
            })
        except Exception as e:
            logger.error(f"Error in status endpoint: {e}")
            return web.json_response({
                'service': 'Discord Bot - Reddit Tasks Helper',
                'status': 'error',
                'error': 'status_check_failed',
                'timestamp': datetime.now().isoformat()
            }, status=500)

# -----------------------
# Bot Cog with comprehensive error handling
# -----------------------
class DiscordBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now()
        logger.info("Discord bot cog initialized")

    @discord.app_commands.command(name="info", description="Get information about the bot")
    async def info(self, interaction: discord.Interaction):
        """Display bot information with fallback handling"""
        try:
            # Safe data collection
            uptime = "unknown"
            servers = 0
            latency = 0
            
            try:
                if self.start_time:
                    uptime = str(datetime.now() - self.start_time).split('.')[0]
            except Exception:
                pass
            
            try:
                if self.bot:
                    servers = len(self.bot.guilds)
                    latency = round(self.bot.latency * 1000)
            except Exception:
                pass

            embed = discord.Embed(
                title="🤖 Bot Information",
                color=0x58b9ff,
                timestamp=datetime.now()
            )
            embed.add_field(name="Bot Name", value="Reddit Tasks - Helper", inline=True)
            embed.add_field(name="Version", value="1.0.0", inline=True)
            embed.add_field(name="Creator", value="<@788580226401566791>", inline=True)
            embed.add_field(name="Uptime", value=uptime, inline=True)
            embed.add_field(name="Servers", value=servers, inline=True)
            embed.add_field(name="Ping", value=f"{latency}ms", inline=True)
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
            
            try:
                embed.set_footer(text=f"Requested by {interaction.user.display_name}")
            except Exception:
                embed.set_footer(text="Requested by user")

            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in info command: {e}")
            try:
                # Fallback simple message
                await interaction.response.send_message(
                    "🤖 **Reddit Tasks - Helper Bot**\n"
                    "Version: 1.0.0\n"
                    "Status: Online\n"
                    "Use `/askquestion` to ask questions about server rules!",
                    ephemeral=True
                )
            except Exception as e2:
                logger.error(f"Failed to send fallback info message: {e2}")

    @discord.app_commands.command(name="askquestion", description="Ask any question and get an AI-powered answer")
    async def ask_question(self, interaction: discord.Interaction, question: str):
        """Handle user questions with comprehensive fallback system"""
        try:
            # Immediate response to prevent timeout
            await interaction.response.defer()
            
            # Input validation
            if not question or len(question.strip()) < 3:
                await interaction.followup.send(
                    "❌ Please provide a valid question with at least 3 characters.",
                    ephemeral=True
                )
                return
            
            # Get AI response with multiple fallbacks
            answer = await self.get_ai_response_with_fallbacks(question)
            
            # Send response with error handling
            await self.send_answer_safely(interaction, answer)
            
        except discord.NotFound:
            logger.warning(f"Interaction expired for user {getattr(interaction.user, 'display_name', 'unknown')}")
            return
        except Exception as e:
            logger.error(f"Error in ask_question command: {e}")
            await self.send_error_message(interaction, "An error occurred while processing your question.")

    async def get_ai_response_with_fallbacks(self, question):
        """Get AI response with multiple fallback levels"""
        fallback_responses = [
            "I don't have specific information about that in our server rules. Please ask in <#1379815484056277044> or DM <@703280080213901342> for help.",
            "For questions about server rules and procedures, please check <#1382588462372356286> or ask in <#1379815484056277044>.",
            "I'm having trouble accessing my knowledge base. Please contact <@703280080213901342> or <@772380971940184064> for help.",
            "Service temporarily unavailable. Please try again later or contact moderators."
        ]
        
        # Try primary AI model
        try:
            if model:
                answer = await self.query_ai_model(model, question)
                if answer and len(answer.strip()) > 10:
                    return answer
        except Exception as e:
            logger.warning(f"Primary AI model failed: {e}")
        
        # Try backup AI model
        try:
            if backup_model and GEMINI_BACKUP_API_KEY:
                genai.configure(api_key=GEMINI_BACKUP_API_KEY)
                answer = await self.query_ai_model(backup_model, question)
                if answer and len(answer.strip()) > 10:
                    return answer
        except Exception as e:
            logger.warning(f"Backup AI model failed: {e}")
        
        # Rule-based fallback
        try:
            answer = self.get_rule_based_answer(question)
            if answer:
                return answer
        except Exception as e:
            logger.warning(f"Rule-based fallback failed: {e}")
        
        # Return appropriate fallback response
        return fallback_responses[0]

    async def query_ai_model(self, ai_model, question):
        """Query AI model with timeout and validation"""
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
            # Set timeout for API call
            response = await asyncio.wait_for(
                asyncio.create_task(asyncio.to_thread(ai_model.generate_content, prompt)),
                timeout=10.0
            )
            
            if response and hasattr(response, 'text'):
                answer = response.text.strip()
                if len(answer) > 10:
                    return answer
            
        except asyncio.TimeoutError:
            logger.warning("AI model query timed out")
        except Exception as e:
            logger.warning(f"AI model query failed: {e}")
        
        return None

    def get_rule_based_answer(self, question):
        """Simple rule-based fallback for common questions"""
        question_lower = question.lower()
        
        # Common question patterns
        if any(word in question_lower for word in ['verify', 'verification', 'how to join']):
            return "To get verified:\n1. Go to <#1382588462372356286>\n2. Post your Reddit profile URL\n3. You need ≥50 karma and an unsuspended account\n4. Wait for mod approval with ✅ reaction"
        
        if any(word in question_lower for word in ['payment', 'payout', 'money']):
            return "Payments are made every Monday (IST) via UPI (India) or USDT (BEP20 only). Submit your records to <@703280080213901342> on Saturday/Sunday."
        
        if any(word in question_lower for word in ['task', 'tasks', 'work']):
            return "Tasks include: Post tasks ($0.30-$0.50, 1/day), Comment tasks ($0.20, 3/day), Voting/Reports ($0.05-$0.10, no limit). Check <#1382657321641181236> for available tasks."
        
        if any(word in question_lower for word in ['rules', 'guidelines']):
            return "Please check <#1382588462372356286> for complete server rules, or ask specific questions in <#1379815484056277044>."
        
        return None

    async def send_answer_safely(self, interaction, answer):
        """Send answer with error handling"""
        try:
            # Create embed with fallback
            try:
                embed = discord.Embed(
                    title="📝 Your Answer",
                    description=answer,
                    color=0x58b9ff,
                    timestamp=datetime.now()
                )
                embed.set_footer(text=f"Requested by {interaction.user.display_name}")
                await interaction.followup.send(embed=embed)
            except Exception:
                # Fallback to simple message
                await interaction.followup.send(f"📝 **Your Answer**\n\n{answer}")
                
        except discord.NotFound:
            logger.warning("Interaction expired while sending answer")
        except Exception as e:
            logger.error(f"Error sending answer: {e}")
            await self.send_error_message(interaction, "Could not send response. Please try again.")

    async def send_error_message(self, interaction, error_msg):
        """Send error message with fallback handling"""
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ {error_msg}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ {error_msg}", ephemeral=True)
        except discord.NotFound:
            logger.warning("Could not send error message - interaction expired")
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")

    @ask_question.error
    async def ask_question_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """Handle command-specific errors"""
        logger.error(f"Command error: {error}")
        error.handled = True  # Mark as handled
        
        try:
            if isinstance(error.original, discord.NotFound):
                return
            
            error_message = "❌ An error occurred while processing your command."
            if isinstance(error, discord.app_commands.MissingPermissions):
                error_message = "❌ You don't have permission to use this command."
            
            await self.send_error_message(interaction, error_message)
        except Exception as e:
            logger.error(f"Error in error handler: {e}")

# -----------------------
# Bot event handlers with error handling
# -----------------------
@bot.event
async def on_ready():
    """Bot ready event with error handling"""
    try:
        logger.info(f'{bot.user} has connected to Discord!')
        logger.info(f'Bot is in {len(bot.guilds)} servers')
        
        try:
            synced = await bot.tree.sync()
            logger.info(f'Synced {len(synced)} commands')
        except Exception as e:
            logger.error(f'Failed to sync commands: {e}')
            
    except Exception as e:
        logger.error(f'Error in on_ready event: {e}')

@bot.event
async def on_guild_join(guild):
    """Handle guild join events"""
    try:
        logger.info(f'Joined new server: {guild.name} (ID: {guild.id})')
    except Exception as e:
        logger.error(f'Error in on_guild_join: {e}')

@bot.event
async def on_guild_remove(guild):
    """Handle guild remove events"""
    try:
        logger.info(f'Left server: {guild.name} (ID: {guild.id})')
    except Exception as e:
        logger.error(f'Error in on_guild_remove: {e}')

@bot.event
async def on_error(event, *args, **kwargs):
    """Handle general bot errors"""
    logger.error(f'Bot error in {event}: {args}')
    logger.error(f'Exception: {traceback.format_exc()}')

@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Global error handler for app commands"""
    if hasattr(error, 'handled'):
        return
    
    logger.error(f"Global app command error: {error}")
    
    try:
        if isinstance(error.original, discord.NotFound):
            return
        
        error_message = "❌ An unexpected error occurred. Please try again."
        
        if not interaction.response.is_done():
            await interaction.response.send_message(error_message, ephemeral=True)
        else:
            await interaction.followup.send(error_message, ephemeral=True)
            
    except Exception as e:
        logger.error(f"Error in global error handler: {e}")

# -----------------------
# Main functions with comprehensive error handling
# -----------------------
async def run_web_server():
    """Run the web server with error handling"""
    try:
        web_server = WebServer()
        
        logger.info(f"Starting web server on port {PORT}")
        runner = web.AppRunner(web_server.app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        logger.info(f"==> Web server started successfully on http://0.0.0.0:{PORT}")
        logger.info(f"==> Health check available at http://0.0.0.0:{PORT}/health")
        logger.info(f"==> Ping endpoint available at http://0.0.0.0:{PORT}/ping")
        
        # Keep the server running
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Error starting web server: {e}")
        # Try to start minimal server as fallback
        try:
            logger.info("Attempting to start minimal web server...")
            minimal_app = web.Application()
            minimal_app.router.add_get('/ping', lambda req: web.Response(text="Bot is Online❇️", status=200))
            minimal_app.router.add_get('/health', lambda req: web.json_response({'status': 'minimal_mode'}, status=200))
            
            minimal_runner = web.AppRunner(minimal_app)
            await minimal_runner.setup()
            minimal_site = web.TCPSite(minimal_runner, '0.0.0.0', PORT)
            await minimal_site.start()
            logger.info(f"==> Minimal web server started on port {PORT}")
            
            while True:
                await asyncio.sleep(1)
        except Exception as e2:
            logger.critical(f"Failed to start minimal web server: {e2}")
            raise

async def run_discord_bot():
    """Run the Discord bot with error handling"""
    try:
        # Add cog with error handling
        try:
            await bot.add_cog(DiscordBot(bot))
            logger.info("Discord bot cog added successfully")
        except Exception as e:
            logger.error(f"Error adding Discord bot cog: {e}")
            # Bot can still run without the cog, just with limited functionality
        
        # Validate token
        if not DISCORD_TOKEN:
            logger.error("DISCORD_TOKEN environment variable not set")
            raise ValueError("DISCORD_TOKEN is required")
        
        # Start bot
        await bot.start(DISCORD_TOKEN)
        
    except discord.LoginFailure:
        logger.error("Invalid Discord token provided")
        raise
    except discord.PrivilegedIntentsRequired:
        logger.error("Bot requires privileged intents that are not enabled")
        raise
    except Exception as e:
        logger.error(f"Error starting Discord bot: {e}")
        raise

async def main():
    """Main function to run both web server and Discord bot"""
    logger.info("Starting Discord bot with web server...")
    
    try:
        # Run both services concurrently
        tasks = [
            asyncio.create_task(run_web_server()),
            asyncio.create_task(run_discord_bot())
        ]
        
        # Wait for both tasks, handle exceptions
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check for exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                service_name = ["Web Server", "Discord Bot"][i]
                logger.error(f"{service_name} failed: {result}")
                
                # If Discord bot fails, try to keep web server running
                if i == 1:  # Discord bot failed
                    logger.info("Discord bot failed, keeping web server running...")
                    # Keep only web server running
                    try:
                        await run_web_server()
                    except Exception as e3:
                        logger.critical(f"Web server also failed: {e3}")
                        raise
                else:
                    raise result
        
    except KeyboardInterrupt:
        logger.info("Shutting down due to keyboard interrupt...")
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
    finally:
        # Cleanup
        try:
            if bot:
                await bot.close()
                logger.info("Discord bot closed")
        except Exception as e:
            logger.error(f"Error closing Discord bot: {e}")

def run_with_fallbacks():
    """Run the application with comprehensive fallback handling"""
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Starting application (attempt {attempt + 1}/{max_retries})")
            asyncio.run(main())
            break
        except KeyboardInterrupt:
            logger.info("Application stopped by user")
            break
        except Exception as e:
            logger.error(f"Application failed on attempt {attempt + 1}: {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                asyncio.run(asyncio.sleep(retry_delay))
            else:
                logger.critical("All attempts failed, starting emergency mode...")
                # Emergency mode - just run a basic web server
                try:
                    emergency_main()
                except Exception as e2:
                    logger.critical(f"Emergency mode failed: {e2}")
                    raise

def emergency_main():
    """Emergency mode - minimal web server only"""
    logger.info("Starting emergency mode - minimal web server only")
    
    async def emergency_server():
        try:
            app = web.Application()
            
            # Essential endpoints only
            async def ping_handler(request):
                return web.Response(text="Bot is Online❇️", status=200)
            
            async def health_handler(request):
                return web.json_response({
                    'status': 'emergency_mode',
                    'message': 'Discord bot unavailable, web server running',
                    'timestamp': datetime.now().isoformat()
                }, status=503)
            
            app.router.add_get('/ping', ping_handler)
            app.router.add_get('/health', health_handler)
            app.router.add_get('/', health_handler)
            
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', PORT)
            await site.start()
            
            logger.info(f"Emergency web server started on port {PORT}")
            logger.info(f"Ping endpoint: http://0.0.0.0:{PORT}/ping")
            
            # Keep running
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.critical(f"Emergency server failed: {e}")
            raise
    
    asyncio.run(emergency_server())

if __name__ == "__main__":
    try:
        run_with_fallbacks()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        logger.critical(f"Traceback: {traceback.format_exc()}")
        
        # Last resort - print error and exit gracefully
        print("CRITICAL ERROR: Application failed to start")
        print(f"Error: {e}")
        print("Please check your environment variables and try again")
        exit(1)
