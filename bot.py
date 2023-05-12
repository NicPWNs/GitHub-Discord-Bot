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

    return device_code, message


async def get_oauth_token(ctx, interaction):

    oauth_token = ""

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
    else:
        oauth_token = data['Item']['oauth_token']
        return oauth_token

    headers = {
        "Accept": "application/json"
    }

    data = {
        "client_id": os.getenv('GITHUB_CLIENT'),
        "device_code": device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code"
    }

    interval = 5

    while not oauth_token:
        time.sleep(interval)
        r = requests.post(
            url="https://github.com/login/oauth/access_token", data=data, headers=headers).json()
        if "slow_down" in r:
            interval = int(r['interval'])
        elif "access_token" in r:
            oauth_token = r['access_token']

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

    table.put_item(
    Item={
        'id': str(ctx.user.id),
        'username': str(ctx.user.name),
        'oauth_token': str(oauth_token)
    })

    return oauth_token


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
                 repository: discord.Option(str, description="GitHub Repo", required=True),
                 events: discord.Option(str, description="Events to Subscribe to", required=True, choices=choices),
                 interaction=""):

        repo_search = re.search(
            'github.com\/*([\w.-]+)\/([\w.-]+)\/*', repository)

        if repo_search:
            owner = repo_search.group(1)
            repo = repo_search.group(2)

        embed = discord.Embed(
            color=0xffffff,
            title="GitHub",
            description=f"<#{ctx.channel.id}> Subscribing to {events}\nat [`{owner}/{repo}`](https://github.com/{owner}/{repo})"
        ).set_thumbnail(url="https://github.githubassets.com/images/modules/open_graph/github-logo.png")
        if interaction == "":
            interaction = await ctx.respond(embed=embed)
        else:
            await interaction.edit_original_response(embed=embed)

        oauth_token = await get_oauth_token(ctx, interaction)

        # Create Discord Webhook
        webhook = await ctx.channel.create_webhook(name="GitHub")

        # Create Github Webook
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + oauth_token,
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

        r = requests.post(
            f"https://api.github.com/repos/{owner}/{repo}/hooks", headers=headers, json=data).json()

        # Invalid Authentication
        if "config" not in r:
            await webhook.delete()
            table.delete_item(Key={'id': str(ctx.user.id)})
            await gh(ctx, repository, events, interaction)

            return

        embed = discord.Embed(
            color=0xffffff,
            title="GitHub",
            description=f"<#{ctx.channel.id}>\nSubscribed to {events}\nat [`{owner}/{repo}`](https://github.com/{owner}/{repo})"
        ).set_thumbnail(url=f"https://github.com/{owner}.png")
        await interaction.edit_original_response(embed=embed)

        return

    bot.run(os.getenv('DISCORD_TOKEN'))
