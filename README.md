# GitHub Bot for Discord

Work in Progress 🚧

## To-Do

- [x] Initial POC
- [x] Store Auth Tokens
- [x] Move auth to DM
- [x] Handle expired/invalid auth
- [x] Better RegEx
- [ ] Encrypt tokens
- [ ] Sub to More Events
- [ ] Check if Owner
- [ ] Exit wait for auth after some time
- [ ] Account for max 15 webhooks (per channel), max 20 (for stars), etc.
- [ ] Fix Discord Webhook Avatar
- [ ] Run Test Webhook Command
- [ ] Migrate to Lambda

## Logic

- Is user authenticated (has device code)?
- Yes
  - Get Device Code
  - Request Token
  - Is token expired?
  - No
    - Complete requests
  - Yes
    - Follow remaining steps
- No
  - Authenticate with Code (in DM)
  - Store Device Code
  - Request Token
  - Complete Requests
