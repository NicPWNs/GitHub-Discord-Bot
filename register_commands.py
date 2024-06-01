from os import getenv
from requests import post
from dotenv import load_dotenv

# Load Secrets
load_dotenv()
DISCORD_APP_ID = getenv("APP_ID")
DISCORD_TOKEN = getenv("DISCORD_TOKEN")

# Discord Auth
headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}

# /github Command
json = {
    "name": "github",
    "description": "Manage subscriptions to GitHub repository events.",
    "options": [
        {
            "name": "status",
            "type": 2,
            "description": "Get status of GitHub Bot for Discord.",
            "options": [
                {
                    "name": "list",
                    "type": 1,
                    "description": "List GitHub repository subscriptions in this channel.",
                }
            ],
        },
        {
            "name": "subscription",
            "type": 2,
            "description": "List GitHub repository subscriptions in this channel.",
            "options": [
                {
                    "name": "create",
                    "type": 1,
                    "description": "Subscribe to GitHub repository events in this channel.",
                    "options": [
                        {
                            "name": "repo",
                            "description": "Repo URL or {USERNAME}/{REPO} format.",
                            "type": 3,
                            "required": True,
                        },
                        {
                            "name": "events",
                            "description": "Events to subscribe this channel to.",
                            "type": 3,
                            "required": True,
                            "choices": [
                                {"name": "All Events", "value": "all"},
                                {"name": "Branch Creations", "value": "create"},
                                {"name": "Branch Deletions", "value": "delete"},
                                {
                                    "name": "Code Scanning Alerts",
                                    "value": "code_scanning_alert",
                                },
                                {
                                    "name": "Dependabot Alerts",
                                    "value": "dependabot_alert",
                                },
                                {"name": "Deployments", "value": "deployment"},
                                {"name": "Discussions", "value": "discussion"},
                                {"name": "Forks", "value": "fork"},
                                {"name": "Issues", "value": "issues"},
                                {"name": "Labels", "value": "label"},
                                {"name": "Members", "value": "member"},
                                {"name": "Milestones", "value": "milestone"},
                                {"name": "Packages", "value": "package"},
                                {"name": "Pull Requests", "value": "pull_request"},
                                {"name": "Pushes", "value": "push"},
                                {"name": "Releases", "value": "release"},
                                {
                                    "name": "Secret Scanning Alerts",
                                    "value": "secret_scanning_alert",
                                },
                                {"name": "Stars", "value": "star"},
                                {"name": "Watch", "value": "watch"},
                                {"name": "Webhooks", "value": "meta"},
                                {"name": "Wikis", "value": "gollum"},
                            ],
                        },
                    ],
                },
                {
                    "name": "delete",
                    "type": 1,
                    "description": "Delete a subscription to GitHub repository events in this channel.",
                    "options": [
                        {
                            "name": "repo",
                            "description": "Repo URL or {USERNAME}/{REPO} format.",
                            "type": 3,
                            "required": True,
                        },
                        {
                            "name": "events",
                            "description": "Events to delete the subscription for in this channel.",
                            "type": 3,
                            "required": True,
                            "choices": [
                                {"name": "All Events", "value": "all"},
                                {"name": "Branch Creations", "value": "create"},
                                {"name": "Branch Deletions", "value": "delete"},
                                {
                                    "name": "Code Scanning Alerts",
                                    "value": "code_scanning_alert",
                                },
                                {
                                    "name": "Dependabot Alerts",
                                    "value": "dependabot_alert",
                                },
                                {"name": "Deployments", "value": "deployment"},
                                {"name": "Discussions", "value": "discussion"},
                                {"name": "Forks", "value": "fork"},
                                {"name": "Issues", "value": "issues"},
                                {"name": "Labels", "value": "label"},
                                {"name": "Members", "value": "member"},
                                {"name": "Milestones", "value": "milestone"},
                                {"name": "Packages", "value": "package"},
                                {"name": "Pull Requests", "value": "pull_request"},
                                {"name": "Pushes", "value": "push"},
                                {"name": "Releases", "value": "release"},
                                {
                                    "name": "Secret Scanning Alerts",
                                    "value": "secret_scanning_alert",
                                },
                                {"name": "Stars", "value": "star"},
                                {"name": "Watch", "value": "watch"},
                                {"name": "Webhooks", "value": "meta"},
                                {"name": "Wikis", "value": "gollum"},
                            ],
                        },
                    ],
                },
            ],
        },
    ],
}

# Register Commands
response = post(
    f"https://discord.com/api/applications/{DISCORD_APP_ID}/commands",
    headers=headers,
    json=json,
)

# Status
if int(response.status_code) == 200:
    print("Command Registration Succeeded!")
else:
    print(f"Command Registration Failed: {response.json()}")
