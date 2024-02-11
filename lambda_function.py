from os import getenv
from json import dumps
from re import search, sub
from requests import get, post
from dotenv import load_dotenv
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError


# Load Secrets
load_dotenv()
TABLE = getenv("DDB_TABLE")
GITHUB = getenv("GITHUB_CLIENT")
DISCORD = getenv("DISCORD_TOKEN")
PUBLIC_KEY = getenv("PUBLIC_KEY")


# Signature Verification
def verify_signature(event):
    verify_key = VerifyKey(bytes.fromhex(PUBLIC_KEY))

    signature = event["params"]["header"]["x-signature-ed25519"]
    timestamp = event["params"]["header"]["x-signature-timestamp"]
    body = event["rawBody"]

    verify_key.verify(f"{timestamp}{body}".encode(), bytes.fromhex(signature))


# Lambda Executes
def lambda_handler(event, context):

    # Signature Headers
    try:
        verify_signature(event)
    except:
        raise Exception("401: Invalid Request Signature")

    # Ping Messages
    body = event.get("body-json")
    if body["type"] == 1:
        return {"type": 1}

    # Application Command Context
    channel = body["channel_id"]
    interaction = body["data"]["id"]
    token = body["token"]

    # Get Options
    repository = body["data"]["options"][0]["value"]
    events = body["data"]["options"][1]["name"]

    # Extract Repo and Owner
    repo_search = search(r"[\/\/]*[github\.com]*[\/]*([\w.-]+)\/([\w.-]+)", repository)

    if repo_search:
        owner = repo_search.group(1)
        repo = repo_search.group(2)

    embeds = [
        {
            "type": "rich",
            "title": "GitHub",
            "description": f"<#{channel}> Subscribing to {events}\nat [`{owner}/{repo}`](https://github.com/{owner}/{repo})",
            "color": 0xFFFFFF,
            "thumbnail": {
                "url": "https://github.githubassets.com/images/modules/open_graph/github-logo.png"
            },
        }
    ]

    return {"type": 4, "data": {"embeds": embeds}}
