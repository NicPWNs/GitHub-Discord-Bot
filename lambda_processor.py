from os import getenv
from boto3 import resource
from re import search, sub
from time import time, sleep
from requests import get, patch, post, delete
from dotenv import load_dotenv


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


# Authorize OAuth App with Device Flow
async def get_device_code(dm_channel):

    headers = {"Accept": "application/json"}

    data = {"client_id": GITHUB, "scope": "admin:repo_hook"}

    r = post(
        url="https://github.com/login/device/code", data=data, headers=headers
    ).json()

    device_code = r["device_code"]

    # DM Auth Begin
    data = {
        "embeds": [
            {
                "title": "GitHub Authentication",
                "description": f"Enter Code:\n `{r['user_code']}`\n\n At [GitHub.com/Login/Device]({r['verification_uri']})",
                "color": 0xFFFFFF,
                "thumbnail": {
                    "url": "https://github.githubassets.com/images/modules/open_graph/github-logo.png",
                },
            }
        ]
    }

    dm_message = post(
        url=f"https://discord.com/api/channels/{dm_channel}/messages", data=data
    )

    return device_code, dm_message


# Get Access Token for GitHub Webhook Creation
async def get_bearer_token(event):

    bearer_token = ""
    application = event["application_id"]
    token = event["token"]
    channel = event["channel_id"]
    discord_user = event["member"]["user"]["global_name"]
    discord_user_id = event["member"]["user"]["id"]

    data = table.get_item(Key={"id": str(discord_user_id)})

    if int(data["ResponseMetadata"]["HTTPHeaders"]["content-length"]) < 5:
        data = {"recipient_id": discord_user_id}
        dm_channel = post(url="https://discord.com/api/users/@me/channels", data=data)

        # Channel Auth Begin
        data = {
            "type": 4,
            "data": {
                "embeds": [
                    {
                        "title": "GitHub Authentication",
                        "description": f"You Need to Authenticate with GitHub\n\nCheck <#{dm_channel}>",
                        "color": 0xFFFFFF,
                        "thumbnail": {
                            "url": "https://github.githubassets.com/images/modules/open_graph/github-logo.png",
                        },
                    }
                ]
            },
        }

        patch(
            url=f"https://discord.com/api/webhooks/{application}/{token}/messages/@original",
            data=data,
        )

        device_code, dm_message = await get_device_code(dm_channel)
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

    # User Authorization
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
            data = {
                "type": 4,
                "data": {
                    "embeds": [
                        {
                            "title": "Timeout Error",
                            "description": "You didn't authenticate within five minutes",
                            "color": 0xBD2C00,
                            "thumbnail": {
                                "url": "https://github.githubassets.com/images/modules/open_graph/github-logo.png",
                            },
                        }
                    ]
                },
            }

            patch(
                url=f"https://discord.com/api/webhooks/{application}/{token}/messages/@original",
                data=data,
            )

            raise TimeoutError

    # DM Auth Complete
    data = {
        "embeds": [
            {
                "title": "GitHub Authentication",
                "description": f"Authentication Successful ✅\n\nYou Can Return to <#{channel}>",
                "color": 0x77B255,
            }
        ]
    }

    patch(url=f"/channels/{dm_channel}/messages/{dm_message}", data=data)

    # Channel Auth Complete
    data = {
        "type": 4,
        "data": {
            "embeds": [
                {
                    "title": "GitHub Authentication",
                    "description": f"You're Authenticated!\n\nPlease Wait...",
                    "color": 0xFFFFFF,
                    "thumbnail": {
                        "url": "https://github.githubassets.com/images/modules/open_graph/github-logo.png",
                    },
                }
            ]
        },
    }

    patch(
        url=f"https://discord.com/api/webhooks/{application}/{token}/messages/@original",
        data=data,
    )

    # GitHub Username
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + bearer_token,
    }
    github_user = get(url="https://api.github.com/user", headers=headers).json()[
        "login"
    ]

    # Save Token
    table.put_item(
        Item={
            "id": str(discord_user_id),
            "discord_user": str(discord_user),
            "github_user": str(github_user),
            "bearer_token": str(bearer_token),
        }
    )

    return bearer_token, user


# Lambda Executes
def lambda_processor(event, context):

    # Interaction Context
    repository = event["data"]["options"][0]["value"]
    events = repository = event["data"]["options"][1]["value"]
    subscription = event_options.index(events)
    interaction = event["data"]["id"]
    application = event["application_id"]
    token = event["token"]
    channel = event["channel_id"]
    discord_user = event["member"]["user"]["global_name"]
    discord_user_id = event["member"]["user"]["id"]

    # Extract Repo and Owner
    repo_search = search(r"[\/\/]*[github\.com]*[\/]*([\w.-]+)\/([\w.-]+)", repository)

    if repo_search:
        owner = repo_search.group(1)
        repo = repo_search.group(2)

    # Begin Process
    data = {
        "type": 4,
        "data": {
            "embeds": [
                {
                    "title": "GitHub",
                    "description": f"<#{channel}> Subscribing to {subscription}\nat [`{owner}/{repo}`](https://github.com/{owner}/{repo})",
                    "color": 0xFFFFFF,
                    "thumbnail": {
                        "url": "https://github.githubassets.com/images/modules/open_graph/github-logo.png",
                    },
                }
            ]
        },
    }

    patch(
        url=f"https://discord.com/api/webhooks/{application}/{token}/messages/@original",
        data=data,
    )

    # Authenticate User
    bearer_token, user = get_bearer_token(
        discord_user, discord_user_id, channel, interaction
    )

    # Clean Repo Name
    repo_clean = sub(r"(?i)discord", "disc*rd", repo)

    # Discord Webhook Avatar
    with open("github.png", "rb") as image:
        avatar = bytearray(image.read())

    # Create Discord Webhook
    try:
        data = {"name": f"{repo_clean} GitHub {events}", "avatar": avatar}

        webhook = post(
            url=f"https://discord.com/api/channels/{channel}/webhooks", data=data
        )

    except:
        data = {
            "type": 4,
            "data": {
                "embeds": [
                    {
                        "title": "Discord Error",
                        "description": f"Discord channel <#{channel}> can only have 15 webhooks.",
                        "color": 0xBD2C00,
                        "thumbnail": {
                            "url": "https://assets-global.website-files.com/6257adef93867e50d84d30e2/636e0a6cc3c481a15a141738_icon_clyde_white_RGB.png",
                        },
                    }
                ]
            },
        }

        patch(
            url=f"https://discord.com/api/webhooks/{application}/{token}/messages/@original",
            data=data,
        )

        return

    # All Events
    if events == "all":
        event_list = list(event_options.values())
        event_list.remove("all")
    else:
        event_list = [events]

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
        delete(url=f"https://discord.com/api/webhooks/{webhook}")
        table.delete_item(Key={"id": str(discord_user_id)})
        lambda_handler(event, context)
        return

    # GitHub Error
    if "Validation Failed" in r.__str__():
        delete(url=f"https://discord.com/api/webhooks/{webhook}")
        data = {
            "type": 4,
            "data": {
                "embeds": [
                    {
                        "title": "GitHub Error",
                        "description": f"{r['errors'][0]['message']}\n\n[Check your GitHub Repo's Webhook Settings](https://github.com/{owner}/{repo}/settings/hooks)",
                        "color": 0xBD2C00,
                        "thumbnail": {
                            "url": "https://github.githubassets.com/images/modules/open_graph/github-logo.png",
                        },
                    }
                ]
            },
        }

        patch(
            url=f"https://discord.com/api/webhooks/{application}/{token}/messages/@original",
            data=data,
        )

        return

    # Other Errors
    if "Not Found" in r.__str__():
        delete(url=f"https://discord.com/api/webhooks/{webhook}")
        # Nonexistent Repo
        if get(f"https://github.com/{owner}/{repo}").status_code == 404:
            data = {
                "type": 4,
                "data": {
                    "embeds": [
                        {
                            "title": "Access Error",
                            "description": f"Repo [`{owner}/{repo}`](https://github.com/{owner}/{repo})\nis inaccessible or does not exist",
                            "color": 0xBD2C00,
                            "thumbnail": {
                                "url": "https://github.githubassets.com/images/modules/open_graph/github-logo.png",
                            },
                        }
                    ]
                },
            }

            patch(
                url=f"https://discord.com/api/webhooks/{application}/{token}/messages/@original",
                data=data,
            )

            return

        # Permission Error
        else:
            data = {
                "type": 4,
                "data": {
                    "embeds": [
                        {
                            "title": "Permission Error",
                            "description": f"GitHub user `{user}` can't create webhooks\non [`{owner}/{repo}`](https://github.com/{owner}/{repo})",
                            "color": 0xBD2C00,
                            "thumbnail": {
                                "url": "https://github.githubassets.com/images/modules/open_graph/github-logo.png",
                            },
                        }
                    ]
                },
            }

            patch(
                url=f"https://discord.com/api/webhooks/{application}/{token}/messages/@original",
                data=data,
            )

            return

    # GitHub Webhook Created
    if "created_at" in r.__str__():
        data = {
            "type": 4,
            "data": {
                "embeds": [
                    {
                        "title": "GitHub",
                        "description": f"<#{channel}>\nSubscribed to {events}\nat [`{owner}/{repo}`](https://github.com/{owner}/{repo})",
                        "color": 0xFFFFFF,
                        "thumbnail": {
                            "url": f"https://github.com/{owner}.png",
                        },
                    }
                ]
            },
        }

        patch(
            url=f"https://discord.com/api/webhooks/{application}/{token}/messages/@original",
            data=data,
        )

    return
