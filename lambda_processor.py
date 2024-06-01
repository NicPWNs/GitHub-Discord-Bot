from os import getenv
from json import loads
from boto3 import resource
from re import search, sub
from time import time, sleep
from base64 import b64encode
from dotenv import load_dotenv
from requests import get, patch, post, delete


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
    exit


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
def get_bearer_token(event):

    bearer_token = ""
    application = event["application_id"]
    channel = event["channel_id"]
    token = event["token"]
    discord_user = event["member"]["user"]["username"]
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
                    "description": f"You Need to Authenticate with GitHub\n\nCheck DM <#{dm_channel}>",
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
            # Channel Timeout Error
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

            # DM Timeout Error
            data = {
                "embeds": [
                    {
                        "title": "Timeout Error",
                        "description": f"You didn't authenticate within five minutes. Try again in <#{channel}>",
                        "color": 0xBD2C00,
                        "thumbnail": {
                            "url": "https://github.githubassets.com/images/modules/open_graph/github-logo.png",
                        },
                    }
                ]
            }

            patch(
                url=f"https://discord.com/api/channels/{dm_channel}/messages/{dm_message}",
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


def subscription_create(event):
    # Interaction Context
    repository = event["data"]["options"][0]["options"][0]["value"]
    events = event["data"]["options"][0]["options"][1]["value"]
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

        return data

    # Filter Non-Repos
    if owner == "m":
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

        return data

    # Begin Process
    data = {
        "embeds": [
            {
                "title": "Subscribing",
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
    bearer_token, github_user = get_bearer_token(event)

    # Clean Repo Name
    repo_clean = sub(r"(?i)discord", "discоrd", repo)
    repo_clean = sub(r"(?i)clyde", "clydе", repo_clean)

    # Discord Webhook Avatar
    image = open("./images/github.png", "rb").read()
    base64 = b64encode(image).decode("utf-8")
    avatar = f"data:image/png;base64,{base64}"

    # Create Discord Webhook
    try:
        # Current Webhooks
        webhooks = get(
            url=f"https://discord.com/api/channels/{channel}/webhooks",
            headers=discord_headers,
        ).json()
        webhooks_list = [name["name"] for name in webhooks]

        # All Webhook Name
        all_webhook_name = f"{owner}/{repo_clean} GitHub All Events"

        # New Webhook Name
        webhook_name = f"{owner}/{repo_clean} GitHub {subscription}"

        # Check Duplicates
        if webhook_name in webhooks_list:
            data = {
                "embeds": [
                    {
                        "title": "Input Error",
                        "description": f"Discord channel <#{channel}> is already subscribed to **{subscription}** at [`{owner}/{repo}`](https://github.com/{owner}/{repo})",
                        "color": 0xBD2C00,
                        "thumbnail": {
                            "url": "https://github.githubassets.com/images/modules/open_graph/github-logo.png",
                        },
                    }
                ]
            }

            return data

        # Check All Events
        elif all_webhook_name in webhooks_list:
            data = {
                "embeds": [
                    {
                        "title": "Input Error",
                        "description": f"Discord channel <#{channel}> is already subscribed to **All Events** at [`{owner}/{repo}`](https://github.com/{owner}/{repo})",
                        "color": 0xBD2C00,
                        "thumbnail": {
                            "url": "https://github.githubassets.com/images/modules/open_graph/github-logo.png",
                        },
                    }
                ]
            }

            return data

        # Create Discord Webhook
        else:
            data = {"name": webhook_name, "avatar": avatar}

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

        return data

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
        subscription_create(event)
        return

    # OAuth App Restrictions
    if "OAuth App access restrictions" in r.__str__():
        delete(url=f"https://discord.com/api/webhooks/{webhook_id}")
        data = {
            "embeds": [
                {
                    "title": "GitHub Error",
                    "description": f"The GitHub organization [`{owner}`](https://github.com/{owner}) has enabled OAuth App access restrictions. [Click here](https://docs.github.com/articles/restricting-access-to-your-organization-s-data/) for more information on these restrictions, including how to enable this app.",
                    "color": 0xBD2C00,
                    "thumbnail": {
                        "url": "https://github.githubassets.com/images/modules/open_graph/github-logo.png",
                    },
                }
            ]
        }

        return data

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

        return data

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

            return data

        # Permission Error
        else:
            print(f"PERMISSION ERROR: {r}")
            data = {
                "embeds": [
                    {
                        "title": "Permission Error",
                        "description": f"GitHub user [`{github_user}`](https://github.com/{github_user}) can't create webhooks\non [`{owner}/{repo}`](https://github.com/{owner}/{repo})",
                        "color": 0xBD2C00,
                        "thumbnail": {
                            "url": "https://github.githubassets.com/images/modules/open_graph/github-logo.png",
                        },
                    }
                ]
            }

            return data

    # GitHub Webhook Created
    if "created_at" in r.__str__():
        data = {
            "embeds": [
                {
                    "title": "Subscription Complete",
                    "description": f"<#{channel}>\nSubscribed to **{subscription}**\nat [`{owner}/{repo}`](https://github.com/{owner}/{repo})",
                    "color": 0xFFFFFF,
                    "thumbnail": {
                        "url": f"https://github.com/{owner}.png",
                    },
                }
            ]
        }

        return data

    print(
        f"[ERROR] Exited without result:\nGitHub User: {github_user}\nDiscord User: {discord_user_id}\nResponse: {r}"
    )

    exit(1)


def subscription_delete(event):
    # Interaction Context
    repository = event["data"]["options"][0]["options"][0]["value"]
    events = event["data"]["options"][0]["options"][1]["value"]
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

        return data

    # Filter Non-Repos
    if owner == "m":
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

        return data

    # Begin Process
    data = {
        "embeds": [
            {
                "title": "Deleting",
                "description": f"<#{channel}> Deleting subscription to **{subscription}**\nat [`{owner}/{repo}`](https://github.com/{owner}/{repo})",
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

    # Clean Repo Name
    repo_clean = sub(r"(?i)discord", "discоrd", repo)
    repo_clean = sub(r"(?i)clyde", "clydе", repo_clean)

    # Current Webhooks
    webhooks = get(
        url=f"https://discord.com/api/channels/{channel}/webhooks",
        headers=discord_headers,
    ).json()
    webhooks_list = [name["name"] for name in webhooks]

    # Webhook to Delete Name
    webhook_name = f"{owner}/{repo_clean} GitHub {subscription}"

    # Delete Webhook
    if webhook_name in webhooks_list:
        # Get Webhook ID
        for webhook in webhooks_list:
            if webhook["name"] == webhook_name:
                webhook_id = webhook["id"]

        # Delete Webhook Based on ID
        delete(url=f"https://discord.com/api/webhooks/{webhook_id}")

        data = {
            "embeds": [
                {
                    "title": "Deletion Complete",
                    "description": f"<#{channel}>\nSubscription to **{subscription}**\nat [`{owner}/{repo}`](https://github.com/{owner}/{repo}) successfully deleted!",
                    "color": 0xFFFFFF,
                    "thumbnail": {
                        "url": f"https://github.com/{owner}.png",
                    },
                }
            ]
        }

        return data

    # Webhook Not Found
    else:
        data = {
            "embeds": [
                {
                    "title": "Input Error",
                    "description": f"Discord channel <#{channel}> is not subscribed to **{subscription}** at [`{owner}/{repo}`](https://github.com/{owner}/{repo})",
                    "color": 0xBD2C00,
                    "thumbnail": {
                        "url": "https://github.githubassets.com/images/modules/open_graph/github-logo.png",
                    },
                }
            ]
        }

        return data


def status_list(event):

    # Interaction Context
    channel = event["channel_id"]

    # Current Webhooks
    webhooks = get(
        url=f"https://discord.com/api/channels/{channel}/webhooks",
        headers=discord_headers,
    ).json()
    webhooks_list = [name["name"] for name in webhooks]

    # String List of Webhooks
    subscriptions = ""
    for webhook in webhooks_list:
        # Parse Owner and Repo Names
        repo_search = search(r"(\S*)\/(\S*)", webhook)

        if repo_search:
            owner = repo_search.group(1)
            repo = repo_search.group(2)
        else:
            continue

        # Reverse Clean Repo Name
        repo = sub(r"(?i)discоrd", "discord", repo)
        repo = sub(r"(?i)clydе", "clyde", repo)

        # Craft String
        subscriptions += f"• [{webhook}](https://github.com/{owner}/{repo})\n"

    # No Subscriptions
    if subscriptions == "":
        subscriptions = "Nothing!"

    data = {
        "embeds": [
            {
                "title": "Subscription Status",
                "description": f"**<#{channel}> is subscribed to:**\n\n{subscriptions}",
                "color": 0xFFFFFF,
                "thumbnail": {
                    "url": "https://github.githubassets.com/images/modules/open_graph/github-logo.png",
                },
            }
        ]
    }

    return data


# Lambda Executes
def lambda_processor(event, context):

    # Deserialize SQS Event
    try:
        event = loads(event["Records"][0]["body"])
    except KeyError:
        pass

    # Get Response Criteria
    command = event["data"]["options"][0]["name"]
    # subcommand = event["data"]["options"][0]["name"][0]["name"]
    application = event["application_id"]
    token = event["token"]

    print(event["data"])

    # Parse Subcommands\
    if command == "status":
        if subcommand == "list":
            data = status_list(event)
    if command == "subscriptions":
        if subcommand == "create":
            data = subscription_create(event)
        elif subcommand == "delete":
            data = subscription_delete(event)

    # Final Command Response
    patch(
        url=f"https://discord.com/api/webhooks/{application}/{token}/messages/@original",
        json=data,
        headers=discord_headers,
    )
    return
