from os import getenv
from json import loads
from boto3 import resource
from re import search, sub
from time import time, sleep
from base64 import b64encode
from requests import get, patch, post, delete
from dotenv import load_dotenv


# Load Secrets
load_dotenv()
DDB_TABLE = getenv("DDB_TABLE")
GITHUB_CLIENT = getenv("GITHUB_CLIENT")
DISCORD_TOKEN = getenv("DISCORD_TOKEN")


# Headers
discord_headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}
json_headers = {"Accept": "application/json"}


# Authentication Timeout
class TimeoutError(Exception):
    pass


# AWS DynamoDB Config
table = resource("dynamodb").Table(DDB_TABLE)


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
def get_device_code(dm_channel):

    data = {"client_id": GITHUB_CLIENT, "scope": "admin:repo_hook"}

    r = post(
        url="https://github.com/login/device/code", json=data, headers=json_headers
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
        url=f"https://discord.com/api/channels/{dm_channel}/messages",
        json=data,
        headers=discord_headers,
    ).json()["id"]

    return device_code, dm_message


# Get Access Token for GitHub Webhook Creation
def get_bearer_token(event, token):

    bearer_token = ""
    application = event["application_id"]
    channel = event["channel_id"]
    discord_user = event["member"]["user"]["global_name"]
    discord_user_id = event["member"]["user"]["id"]

    data = table.get_item(Key={"id": str(discord_user_id)})

    if int(data["ResponseMetadata"]["HTTPHeaders"]["content-length"]) < 5:
        data = {"recipient_id": discord_user_id}
        dm_channel = post(
            url="https://discord.com/api/users/@me/channels",
            json=data,
            headers=discord_headers,
        ).json()["id"]

        # Channel Auth Begin
        data = {
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
        }

        patch(
            url=f"https://discord.com/api/webhooks/{application}/{token}/messages/@original",
            json=data,
            headers=discord_headers,
        )

        device_code, dm_message = get_device_code(dm_channel)
    else:
        bearer_token = data["Item"]["bearer_token"]
        github_user = data["Item"]["github_user"]
        return bearer_token, github_user

    data = {
        "client_id": GITHUB_CLIENT,
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
            json=data,
            headers=json_headers,
        ).json()
        if "slow_down" in r:
            interval = int(r["interval"])
        elif "access_token" in r:
            bearer_token = r["access_token"]
        elif int(time() - start_time) > 300:
            data = {
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
            }

            patch(
                url=f"https://discord.com/api/webhooks/{application}/{token}/messages/@original",
                json=data,
                headers=discord_headers,
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

    patch(
        url=f"https://discord.com/api/channels/{dm_channel}/messages/{dm_message}",
        json=data,
        headers=discord_headers,
    )

    # Channel Auth Complete
    data = {
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
    }

    patch(
        url=f"https://discord.com/api/webhooks/{application}/{token}/messages/@original",
        json=data,
        headers=discord_headers,
    )

    # GitHub Username
    github_headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + bearer_token,
    }
    github_user = get(url="https://api.github.com/user", headers=github_headers).json()[
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

    return bearer_token, github_user


# Lambda Executes
def lambda_processor(event, context):

    # Deserialize SQS Event
    try:
        event = loads(event["Records"][0]["body"])
    except KeyError:
        pass

    # Interaction Context
    repository = event["data"]["options"][0]["value"]
    events = event["data"]["options"][1]["value"]
    discord_user_id = event["member"]["user"]["id"]
    channel = event["channel_id"]
    application = event["application_id"]
    token = event["token"]
    subscription = list(event_options.keys())[
        list(event_options.values()).index(events)
    ]

    # Extract Repo and Owner
    repo_search = search(r"[\/\/]*[github\.com]*[\/]*([\w.-]+)\/([\w.-]+)", repository)

    if repo_search:
        owner = repo_search.group(1)
        repo = repo_search.group(2)
    else:
        data = {
            "embeds": [
                {
                    "title": "Input Error",
                    "description": "Be sure to provide the GitHub repo URL or {USERNAME}/{REPO} format.",
                    "color": 0xBD2C00,
                    "thumbnail": {
                        "url": "https://github.githubassets.com/images/modules/open_graph/github-logo.png",
                    },
                }
            ]
        }

        patch(
            url=f"https://discord.com/api/webhooks/{application}/{token}/messages/@original",
            json=data,
            headers=discord_headers,
        )

    # Begin Process
    data = {
        "embeds": [
            {
                "title": "GitHub",
                "description": f"<#{channel}> Subscribing to **{subscription}**\nat [`{owner}/{repo}`](https://github.com/{owner}/{repo})",
                "color": 0xFFFFFF,
                "thumbnail": {
                    "url": "https://github.githubassets.com/images/modules/open_graph/github-logo.png",
                },
            }
        ]
    }

    patch(
        url=f"https://discord.com/api/webhooks/{application}/{token}/messages/@original",
        json=data,
        headers=discord_headers,
    )

    # Authenticate User
    bearer_token, github_user = get_bearer_token(event, token)

    # Clean Repo Name
    repo_clean = sub(r"(?i)discord", "disc*rd", repo)
    repo_clean = sub(r"(?i)clyde", "clyd*", repo)

    # Discord Webhook Avatar
    image = open("./github.png", "rb").read()
    base64 = b64encode(image).decode("utf-8")
    avatar = f"data:image/png;base64,{base64}"

    # Create Discord Webhook
    try:
        data = {"name": f"{repo_clean} GitHub {subscription}", "avatar": avatar}

        webhook = post(
            url=f"https://discord.com/api/channels/{channel}/webhooks",
            json=data,
            headers=discord_headers,
        ).json()
        webhook_id = webhook["id"]
        webhook_url = webhook["url"]
    except:
        data = {
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
        }

        patch(
            url=f"https://discord.com/api/webhooks/{application}/{token}/messages/@original",
            json=data,
            headers=discord_headers,
        )

        return

    # All Events
    if events == "all":
        event_list = list(event_options.values())
        event_list.remove("all")
    else:
        event_list = [events]

    # Create GitHub Webhook
    github_headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + bearer_token,
    }

    data = {
        "name": "web",
        "config": {"url": webhook_url + "/github", "content_type": "json"},
        "events": event_list,
        "active": True,
    }

    r = post(
        f"https://api.github.com/repos/{owner}/{repo}/hooks",
        headers=github_headers,
        json=data,
    ).json()

    # Invalid Authentication
    if "Bad credentials" in r.__str__():
        delete(url=f"https://discord.com/api/webhooks/{webhook_id}")
        table.delete_item(Key={"id": str(discord_user_id)})
        lambda_processor(event, context)
        return

    # GitHub Error
    if "Validation Failed" in r.__str__():
        delete(url=f"https://discord.com/api/webhooks/{webhook_id}")
        data = {
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
        }

        patch(
            url=f"https://discord.com/api/webhooks/{application}/{token}/messages/@original",
            json=data,
            headers=discord_headers,
        )

        return

    # Other Errors
    if "Not Found" in r.__str__():
        delete(url=f"https://discord.com/api/webhooks/{webhook_id}")
        # Nonexistent Repo
        if get(f"https://github.com/{owner}/{repo}").status_code == 404:
            data = {
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
            }

            patch(
                url=f"https://discord.com/api/webhooks/{application}/{token}/messages/@original",
                json=data,
                headers=discord_headers,
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
                            "description": f"GitHub user `{github_user}` can't create webhooks\non [`{owner}/{repo}`](https://github.com/{owner}/{repo})",
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
                json=data,
                headers=discord_headers,
            )

            return

    # GitHub Webhook Created
    if "created_at" in r.__str__():
        data = {
            "embeds": [
                {
                    "title": "GitHub",
                    "description": f"<#{channel}>\nSubscribed to **{subscription}**\nat [`{owner}/{repo}`](https://github.com/{owner}/{repo})",
                    "color": 0xFFFFFF,
                    "thumbnail": {
                        "url": f"https://github.com/{owner}.png",
                    },
                }
            ]
        }

        patch(
            url=f"https://discord.com/api/webhooks/{application}/{token}/messages/@original",
            json=data,
            headers=discord_headers,
        )

    return
