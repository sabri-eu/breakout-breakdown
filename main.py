import discord
from bot import StockBot
import config
intents = discord.Intents.default()
intents.typing = False
intents.presences = False

client = discord.Client(intents=intents)
bot = StockBot()

@client.event
async def on_ready():
    print(f'Logged in as {client.user.name}')
    await bot.start_stock_analysis(client)

client.run(config.TOKEN)
