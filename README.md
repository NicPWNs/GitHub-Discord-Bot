# GitHub Bot for Discord

Work in Progress 🚧

## To-Do

- [x] Initial POC
- [x] Store Auth Tokens
- [x] Move auth to DM
- [x] Handle expired/invalid auth
- [x] Better RegEx
- [x] Encrypt tokens
- [x] Remove stray Interaction option
- [x] Sub to More Events
- [x] Handle not finding repo
- [x] Check if Owner
- [x] Exit wait for auth after some time
- [x] Fix Discord Webhook Avatar
- [x] Fix recursion
- [x] Account for max 15 webhooks (per channel), max 20 (for stars), etc.
- [x] Migrate to Lambda
- [x] Fix bad repo input
- [x] User's linked GitHub?
- [x] Check timeout
- [ ] Duplicate subscriptions
- [x] Rename command to `/github`
- [ ] Formalize README
- [ ] Migrate to SAM

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
