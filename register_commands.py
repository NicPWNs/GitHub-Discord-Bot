from os import getenv
from requests import post
from dotenv import load_dotenv

# Load Secrets
load_dotenv()
DISCORD_APP_ID = getenv("APP_ID")
DISCORD_TOKEN = getenv("DISCORD_TOKEN")

# Discord Auth
headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}

# `/github {repo} {events}` Command
json = {
    "name": "github",
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
                {"name": "Code Scanning Alerts", "value": "code_scanning_alert"},
                {"name": "Dependabot Alerts", "value": "dependabot_alert"},
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
                {"name": "Secret Scanning Alerts", "value": "secret_scanning_alert"},
                {"name": "Stars", "value": "star"},
                {"name": "Watch", "value": "watch"},
                {"name": "Webhooks", "value": "meta"},
                {"name": "Wikis", "value": "gollum"},
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
