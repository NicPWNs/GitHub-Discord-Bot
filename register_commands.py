from os import getenv
from requests import post
from dotenv import load_dotenv

# Load Secrets
load_dotenv()
DISCORD_APP_ID = getenv("APP_ID")
DISCORD_TOKEN = getenv("DISCORD_TOKEN")

# Discord Auth
headers = {"Authorization": f"Bot {DISCORD_TOKEN}"}

# /gh Command
json = {
    "name": "gh",
    "type": 1,
    "description": "Subscribe to a GitHub repository in this channel.",
    "options": [
        {
            "name": "repository",
            "description": "GitHub repo URL or USERNAME/REPO format.",
            "type": 3,
            "required": True,
        },
        {
            "name": "events",
            "description": "Event(s) to subscribe to.",
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
                {"name": "TEST", "value": "test"},
            ],
        },
    ],
}

# Register Commands
r = post(
    f"https://discord.com/api/v10/applications/{DISCORD_APP_ID}/commands",
    headers=headers,
    json=json,
)

# Status
if int(r.status_code) == 200:
    print("Commands Registration Succeeded!")
else:
    print(f"Command Registration Failed: {r.json()}")
