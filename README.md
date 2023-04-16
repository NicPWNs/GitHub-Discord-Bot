# GitHub Bot for Discord

## To-Do

- [x] Initial POC
- [x] Store Device Codes
- [x] Move auth to DM
- [ ] Sub to More Events
- [ ] Check if Owner
- [ ] Fix Discord Webhook Avatar
- [ ] Better RegEx
- [ ] Run Test
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
