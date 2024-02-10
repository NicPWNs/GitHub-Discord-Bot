#!/usr/bin/env python3
from os import getenv
from boto3 import resource
from re import search, sub
from time import time, sleep
from requests import get, post
from dotenv import load_dotenv
from discord import ApplicationContext, Bot, Embed, Option


# Load Secrets
load_dotenv()
TABLE = getenv("DDB_TABLE")
GITHUB = getenv("GITHUB_CLIENT")
DISCORD = getenv("DISCORD_TOKEN")


# Authentication Timeout
class TimeoutError(Exception):
    pass


# AWS DynamoDB Config
table = resource("dynamodb").Table(TABLE)


# Authorize OAuth App with Device Flow
async def get_device_code(ctx):

    headers = {"Accept": "application/json"}

    data = {"client_id": GITHUB, "scope": "admin:repo_hook"}

    r = post(
        url="https://github.com/login/device/code", data=data, headers=headers
    ).json()

    device_code = r["device_code"]

    embed = Embed(
        color=0xFFFFFF,
        title="GitHub Authentication",
        description=f"Enter Code:\n `{r['user_code']}`\n\n At [GitHub.com/Login/Device]({r['verification_uri']})",
    ).set_thumbnail(
        url="https://github.githubassets.com/images/modules/open_graph/github-logo.png"
    )

    channel = await ctx.user.create_dm()
    message = await channel.send(embed=embed)

    return device_code, message


# Get Access Token for GitHub Webhook Creation
async def get_bearer_token(ctx, interaction):

    bearer_token = ""

    data = table.get_item(Key={"id": str(ctx.user.id)})

    if int(data["ResponseMetadata"]["HTTPHeaders"]["content-length"]) < 5:
        channel = await ctx.user.create_dm()
        embed = Embed(
            color=0xFFFFFF,
            title="GitHub Authentication",
            description=f"You Need to Authenticate with GitHub\n\nCheck <#{channel.id}>",
        ).set_thumbnail(
            url="https://github.githubassets.com/images/modules/open_graph/github-logo.png"
        )
        await interaction.edit_original_response(embed=embed)
        device_code, message = await get_device_code(ctx)
    else:
        bearer_token = data["Item"]["bearer_token"]
        user = data["Item"]["github_user"]
        return bearer_token, user

    headers = {"Accept": "application/json"}

    data = {
        "client_id": GITHUB,
        "device_code": device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
    }

    interval = 5
    start_time = time()

    # Wait for user to authorize
    while not bearer_token:
        sleep(interval)
        r = post(
            url="https://github.com/login/oauth/access_token",
            data=data,
            headers=headers,
        ).json()
        if "slow_down" in r:
            interval = int(r["interval"])
        elif "access_token" in r:
            bearer_token = r["access_token"]
        elif int(time() - start_time) > 300:
            embed = Embed(
                color=0xBD2C00,
                title="Timeout Error",
                description=f"You didn't authenticate within five minutes",
            ).set_thumbnail(
                url="https://github.githubassets.com/images/modules/open_graph/github-logo.png"
            )
            await interaction.edit_original_response(embed=embed)
            raise TimeoutError

    # GitHub Username
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + bearer_token,
    }
    user = get(url="https://api.github.com/user", headers=headers).json()["login"]

    embed = Embed(
        color=0x77B255,
        title="GitHub Authentication",
        description=f"Authentication Successful ✅\n\nYou Can Return to <#{ctx.channel.id}>",
    )
    await message.edit(embed=embed)

    embed = Embed(
        color=0xFFFFFF,
        title="GitHub Authentication",
        description=f"You're Authenticated!\n\nPlease Wait...",
    ).set_thumbnail(
        url="https://github.githubassets.com/images/modules/open_graph/github-logo.png"
    )
    await interaction.edit_original_response(embed=embed)

    # Save access token for future requests
    table.put_item(
        Item={
            "id": str(ctx.user.id),
            "discord_user": str(ctx.user.name),
            "github_user": str(user),
            "bearer_token": str(bearer_token),
        }
    )

    return bearer_token, user


if __name__ == "__main__":

    bot = Bot()

    # Event Options
    event_options = {
        "All Events": "all",
        "Branch Creations": "create",
        "Branch Deletions": "delete",
        "Code Scanning Alerts": "code_scanning_alert",
        "Dependabot Alerts": "dependabot_alert",
        "Deployments": "deployment",
        "Discussions": "discussion",
        "Forks": "fork",
        "Issues": "issues",
        "Labels": "label",
        "Members": "member",
        "Milestones": "milestone",
        "Packages": "package",
        "Pull Requests": "pull_request",
        "Pushes": "push",
        "Releases": "release",
        "Secret Scanning Alerts": "secret_scanning_alert",
        "Stars": "star",
        "Watch": "watch",
        "Webhooks": "meta",
        "Wikis": "gollum",
    }

    # Register Slash Command
    @bot.slash_command(
        name="gh", description="Subscribe to a GitHub repository in this channel."
    )
    async def gh(
        ctx: ApplicationContext,
        repository: Option(
            input_type=str,
            description="GitHub Repo URL or Username/Repo format.",
            required=True,
        ),  # type: ignore
        events: Option(
            input_type=str,
            description="Event(s) to Subscribe to.",
            required=True,
            choices=list(event_options.keys()),
        ),  # type: ignore
    ):

        # Extract Repo and Owner
        repo_search = search(
            r"[\/\/]*[github\.com]*[\/]*([\w.-]+)\/([\w.-]+)", repository
        )

        if repo_search:
            owner = repo_search.group(1)
            repo = repo_search.group(2)

        embed = Embed(
            color=0xFFFFFF,
            title="GitHub",
            description=f"<#{ctx.channel.id}> Subscribing to {events}\nat [`{owner}/{repo}`](https://github.com/{owner}/{repo})",
        ).set_thumbnail(
            url="https://github.githubassets.com/images/modules/open_graph/github-logo.png"
        )

        # Recursive Fork
        if "interaction" not in globals():
            global interaction
            interaction = await ctx.respond(embed=embed)
        else:
            await interaction.edit_original_response(embed=embed)

        # Authenticate User
        bearer_token, user = await get_bearer_token(ctx, interaction)

        # Clean repos with "discord" in the name
        repo_clean = sub(r"(?i)discord", "disc*rd", repo)

        # Discord Webhook Avatar
        with open("github.png", "rb") as image:
            avatar = bytearray(image.read())

        # Create Discord Webhook
        try:
            webhook = await ctx.channel.create_webhook(
                name=f"{repo_clean} GitHub {events}",
                avatar=avatar,
                reason="Created by GitHub Bot for Discord",
            )
        except:
            embed = Embed(
                color=0xBD2C00,
                title="Discord Error",
                description=f"Discord channel <#{ctx.channel.id}> can only have 15 webhooks.",
            ).set_thumbnail(
                url="https://assets-global.website-files.com/6257adef93867e50d84d30e2/636e0a6cc3c481a15a141738_icon_clyde_white_RGB.png"
            )
            await interaction.edit_original_response(embed=embed)
            return

        # All Events
        if events == "All Events":
            event_list = list(event_options.values())
            event_list.remove("all")
        else:
            event_list = [event_options[events]]

        # Create GitHub Webhook
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + bearer_token,
        }

        data = {
            "name": "web",
            "config": {"url": webhook.url + "/github", "content_type": "json"},
            "events": event_list,
            "active": True,
        }

        r = post(
            f"https://api.github.com/repos/{owner}/{repo}/hooks",
            headers=headers,
            json=data,
        ).json()

        # Invalid Authentication
        if "Bad credentials" in r.__str__():
            await webhook.delete()
            table.delete_item(Key={"id": str(ctx.user.id)})
            await gh(ctx, repository, events)
            return

        # GitHub Error
        if "Validation Failed" in r.__str__():
            await webhook.delete()
            embed = Embed(
                color=0xBD2C00,
                title="GitHub Error",
                description=f"{r['errors'][0]['message']}\n\n[Check your GitHub Repo's Webhook Settings](https://github.com/{owner}/{repo}/settings/hooks)",
            ).set_thumbnail(
                url="https://github.githubassets.com/images/modules/open_graph/github-logo.png"
            )
            await interaction.edit_original_response(embed=embed)
            return

        # Other Errors
        if "Not Found" in r.__str__():
            await webhook.delete()
            # Nonexistent Repo
            if get(f"https://github.com/{owner}/{repo}").status_code == 404:
                embed = Embed(
                    color=0xBD2C00,
                    title="Access Error",
                    description=f"Repo [`{owner}/{repo}`](https://github.com/{owner}/{repo})\nis inaccessible or does not exist",
                ).set_thumbnail(
                    url="https://github.githubassets.com/images/modules/open_graph/github-logo.png"
                )
                await interaction.edit_original_response(embed=embed)
                return

            # Permissions Error
            else:
                embed = Embed(
                    color=0xBD2C00,
                    title="Permission Error",
                    description=f"GitHub user `{user}` can't create webhooks\non [`{owner}/{repo}`](https://github.com/{owner}/{repo})",
                ).set_thumbnail(
                    url="https://github.githubassets.com/images/modules/open_graph/github-logo.png"
                )
                await interaction.edit_original_response(embed=embed)
                return

        # GitHub Webhook Created
        if "created_at" in r.__str__():
            embed = Embed(
                color=0xFFFFFF,
                title="GitHub",
                description=f"<#{ctx.channel.id}>\nSubscribed to {events}\nat [`{owner}/{repo}`](https://github.com/{owner}/{repo})",
            ).set_thumbnail(url=f"https://github.com/{owner}.png")
            await interaction.edit_original_response(embed=embed)

        del interaction

        return

    # Start Bot
    bot.run(DISCORD)
