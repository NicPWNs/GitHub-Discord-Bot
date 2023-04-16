#!/usr/bin/env python3
import os
import re
import time
import boto3
import discord
import requests
from dotenv import load_dotenv


TABLE = "discord-github"
DDB = boto3.resource('dynamodb')
table = DDB.Table(TABLE)


async def get_device_code(ctx):
    headers = {
        "Accept": "application/json"
    }

    data = {
        "client_id": os.getenv('GITHUB_CLIENT'),
        "scope": "admin:repo_hook"
    }

    r = requests.post(
        url="https://github.com/login/device/code", data=data, headers=headers).json()

    device_code = r['device_code']

    embed = discord.Embed(
        color=0xffffff,
        title="GitHub Authentication",
        description=f"Enter Code `{r['user_code']}`\n\n At [GitHub.com/Login/Device]({r['verification_uri']})"
    ).set_thumbnail(url="https://github.githubassets.com/images/modules/open_graph/github-logo.png")
    channel = await ctx.user.create_dm()
    message = await channel.send(embed=embed)

    table.put_item(
        Item={
            'id': str(ctx.user.id),
            'device_code': str(device_code),
            'expires': str(time.time() + int(r['expires_in']))
        })

    return device_code, message


async def get_bearer_token(ctx, interaction):

    expired = True
    data = table.get_item(Key={'id': str(ctx.user.id)})

    if int(data['ResponseMetadata']
            ['HTTPHeaders']['content-length']) < 5:
        channel = await ctx.user.create_dm()
        embed = discord.Embed(
            color=0xffffff,
            title="GitHub Authentication",
            description=f"You Need to Authenticate with GitHub\n\nCheck <#{channel.id}>"
        ).set_thumbnail(url="https://github.githubassets.com/images/modules/open_graph/github-logo.png")
        await interaction.edit_original_response(embed=embed)
        device_code, message = await get_device_code(ctx)

    elif time.time() > float(data['Item']['expires']):
        channel = await ctx.user.create_dm()
        embed = discord.Embed(
            color=0xffffff,
            title="GitHub Authentication",
            description=f"Your Authentication Expired\n\nCheck <#{channel.id}>"
        ).set_thumbnail(url="https://github.githubassets.com/images/modules/open_graph/github-logo.png")
        await interaction.edit_original_response(embed=embed)
        device_code, message = await get_device_code(ctx)

    else:
        device_code = data['Item']['device_code']
        expired = False

    headers = {
        "Accept": "application/json"
    }

    data = {
        "client_id": os.getenv('GITHUB_CLIENT'),
        "device_code": device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
    }

    bearer_token = ""
    interval = 5

    while not bearer_token:
        time.sleep(interval)
        r = requests.post(
            url="https://github.com/login/oauth/access_token", data=data, headers=headers).json()
        if "slow_down" in r:
            interval = int(r['interval'])
        elif "access_token" in r:
            bearer_token = r['access_token']

    if expired:
        embed = discord.Embed(
            color=0x77b255,
            title="GitHub Authentication",
            description=f"Authentication Successful ✅\n\nYou Can Return to <#{ctx.channel.id}>")
        await message.edit(embed=embed)

    embed = discord.Embed(
        color=0xffffff,
        title="GitHub Authentication",
        description=f"You're Authenticated!\n\nPlease Wait..."
    ).set_thumbnail(url="https://github.githubassets.com/images/modules/open_graph/github-logo.png")
    await interaction.edit_original_response(embed=embed)

    return bearer_token


if __name__ == "__main__":

    load_dotenv()
    bot = discord.Bot()

    payloads = {
        "Everything": "everything",
        "Forks": "fork",
        "Issues": "issues",
        "Packages": "package",
        "Pull Requests": "pull_request",
        "Pushes": "push",
        "Releases": "release",
        "Stars": "star",
    }

    choices = list(payloads.keys())

    @bot.slash_command(name="gh", description="Subscribe to a GitHub Repository in this channel.")
    async def gh(ctx: discord.ApplicationContext,
                 repo: discord.Option(str, description="GitHub Repo", required=True),
                 events: discord.Option(str, description="Events to Subscribe to", required=False, choices=choices)):

        repo_search = re.search(
            'github.com\/*([\w.-]+)\/([\w.-]+)\/*', repo)

        if repo_search:
            owner = repo_search.group(1)
            repo = repo_search.group(2)

        embed = discord.Embed(
            color=0xffffff,
            title="GitHub",
            description=f"<#{ctx.channel.id}> Subscribing to {events}\nat [`{owner}/{repo}`](https://github.com/{owner}/{repo})"
        ).set_thumbnail(url="https://github.githubassets.com/images/modules/open_graph/github-logo.png")
        interaction = await ctx.respond(embed=embed)

        bearer_token = await get_bearer_token(ctx, interaction)

        # Create Discord Webhook
        webhook = await ctx.channel.create_webhook(name="GitHub")

        # Create Github Webook
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + bearer_token,
        }

        data = {
            "name": "web",
            "config": {
                "url": webhook.url + "/github",
                "content_type": "json",
            },
            "events": [payloads[events]],
            "active": True,
        }

        webhook = requests.post(
            f"https://api.github.com/repos/{owner}/{repo}/hooks", headers=headers, json=data).json()

        embed = discord.Embed(
            color=0xffffff,
            title="GitHub",
            description=f"<#{ctx.channel.id}>\nSubscribed to {events}\nat [`{owner}/{repo}`](https://github.com/{owner}/{repo})"
        ).set_thumbnail(url=f"https://github.com/{owner}.png")
        await interaction.edit_original_response(embed=embed)

        return

    bot.run(os.getenv('DISCORD_TOKEN'))
