# GitHub Bot for Discord

Subscribe a Discord Channel to Events in your GitHub Repositories. [Try it now!](https://discord.com/api/oauth2/authorize?client_id=1096576031093174334&permissions=536870912&scope=bot)

![Banner](https://github.com/NicPWNs/GitHub-Discord-Bot/assets/23003787/49c595ee-8b4b-47d1-9eb9-74c69a5ee94a)

[![Discord Bot](https://img.shields.io/badge/Get%20the%20Bot-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/api/oauth2/authorize?client_id=1096576031093174334&permissions=536870912&scope=bot)
[![AWS Lambda](https://img.shields.io/badge/Serverless-FF9900?style=for-the-badge&logoColor=white&logo=awslambda)](https://aws.amazon.com/lambda/)
[![Python 3.11](https://img.shields.io/badge/Python%203.11-3776AB?style=for-the-badge&logoColor=white&logo=python)](https://www.python.org/downloads/release/python-3117/)
[![Developer Program](https://img.shields.io/badge/Developer%20Program-181717?style=for-the-badge&logoColor=white&logo=github)](https://docs.github.com/en/get-started/exploring-integrations/github-developer-program)
[![Slash Commands](https://img.shields.io/badge/Slash%20Commands-5865F2?style=for-the-badge&logoColor=white&logo=slashdot)](https://discord.com/blog/slash-commands-are-here)

> Like this bot? Give it a [⭐ on GitHub!](https://github.com/NicPWNs/github-discord-bot)

## Getting Started

First, [add the bot](https://discord.com/api/oauth2/authorize?client_id=1096576031093174334&permissions=536870912&scope=bot) to your Discord server. Use the commands below in a text channel to subscribe to specific GitHub events.

## Commands

> Type or Copy into Discord!

### Subscribe

```bash
/github subscribe repo: events:
```

### Status

```bash
/github status
```

## Examples

Subscribe to **All Events** in _this_ repo:

```bash
/github subscribe repo:NicPWNs/GitHub-Discord-Bot events:All Events
```

![image](https://github.com/NicPWNs/GitHub-Discord-Bot/assets/23003787/9a787c88-5717-40a5-adfb-034c064a5a0e)

Subscribe to **Stars** in _this_ repo:

```bash
/github subscribe repo:https://github.com/NicPWNs/GitHub-Discord-Bot events:Stars
```

![image](https://github.com/NicPWNs/GitHub-Discord-Bot/assets/23003787/4605785c-c0e3-457f-bfc2-4af92b0f4498)

> GitHub URLs or Owner/Repo formats work!

## Issues

Found a bug, ran into an issue, or have an idea? [Submit an issue](https://github.com/NicPWNs/GitHub-Discord-Bot/issues/new/choose)!

## Permissions

This bot requires specific permissions to function properly. The bot only requests the minimum necessary permissions for its intended functionality, prioritizing user privacy and security.

1. **Discord - [_Manage Webhooks_](https://discord.com/developers/docs/topics/permissions#permissions)**: The bot requires this permission to create and manage webhooks in your Discord server. Webhooks are used to deliver GitHub-related events to your specified channels.
2. **GitHub - [_Repository Webhooks_](https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps#repository-permissions-for-webhooks)**: The bot needs permission to create and manage webhooks in your GitHub repositories.

## Maintainer

[Nic Jones, (@NicPWNs)](https://github.com/NicPWNs)

## License

This project is licensed under the [MIT License](./LICENSE).

## Disclaimer

This bot is not officially created or endorsed by GitHub, Inc. It is an independent project developed by [NicPWNs](https://github.com/NicPWNs) for enhancing GitHub integration under the [GitHub Developer Program](https://docs.github.com/en/get-started/exploring-integrations/github-developer-program).

GitHub and the GitHub and Octocat logo are trademarks of GitHub, Inc. The use of the GitHub name and logo is for identification and reference purposes only and does not imply any association with the GitHub brand.
