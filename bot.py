#!/usr/bin/env python3
import os
import discord
import requests
from dotenv import load_dotenv


if __name__ == "__main__":

    load_dotenv()

    bot = discord.Bot()

    # Event Listeners
    @bot.listen('on_ready')
    async def on_ready():
        return

    # Slash Commands
    @bot.slash_command(name="gh", description="Subscribe to a GitHub Repository.")
    async def gh(ctx):

        headers = {
            "Accept": "application/json"
        }

        data = {
            "client_id": "fd91b7ae85eac5311a8f",
            "scope": "admin:repo_hook"
        }

        r = requests.post(
            url="https://github.com/login/device/code", data=data, headers=headers).json

        print(r)

        return

    bot.run(os.getenv('DISCORD_TOKEN'))
