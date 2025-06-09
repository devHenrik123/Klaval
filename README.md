# Klaval - A Klavia bot for Discord
I got bored, so I decided to write a Discord bot for Klavia.  
Available commands, example images and short documentation can be found below.

## Commands:  
The following commands are currently supported:  
| Command            | Parameters            | Description |
|--------------------|-----------------------| ------------|
| /setup             | <welcome_channel> <message_author> <message_icon_url> | Should be used immediately after adding bot to server. Runs setup tasks, creates roles, sets the welcome channel, message author and icon. |
| /find_racer        | <klavia_name>         | Searches for Klavia account and returns id, display name and username. |
| /verify            | <klavia_name>         | Verifies account, links it to the Klavia account and updates their server profile. |
| /force_verify      | <member> <klavia_id>  | Can be used by admins to verify other users or themselves immediately. |
| /unverify          |                       | Unverifies the user who's using the command. |
| /force_unverify    | <member> <klavia_id>  | Can be used by admins to unverify other users or themselves immediately. |
| /sync              |                       | Synchronizes the server profile and Klavia account. Updates server profile. |
| /garage            | [klavia_name]         | Displays some information about the users garage. |
| /stats             | [klavia_name]         | Displays some statistics of the given user. |
| /quests            | [klavia_name]         | Displays the users current quests. |

<> = Required Parameter  
[ ] = Optional Parameter  

## Currently working on:
### More commands  
I am planning to add more commands for team stats, comparisons, etc. Also your team will obviously be linked to your profile through your linked Klavia account.

## Development Environment
1. Python 3.12  
   This bot has been written in Python 3.12, because unfortunately py-cord does not support 3.13, yet.
2. .env file  
   You must provide a .env file in the project root directory containing your Klavia credentials and Discord bot token.  
   Example .env file:  
    ```
    klavia_username_or_mail=<enter-your-klavia-mail-here>
    klavia_password=<enter-your-klavia-password-here>
    discord_bot_token=<enter-your-bot-token-here>
    ```
3. Discord server setup:  
   Make sure to give the bot sufficient permissions. It needs to do the following things:
   - Create, edit and assign server roles.
   - Edit user profiles.
   - Send messages.
     
   To avoid conflict with other bots, all roles have a prefix. These roles will be automatically created, once you run the setup command:
   - HK Unverified
   - HK Verification Pending
   - HK Verified

## Examples:
![verification](readme/verification.png)
![garage](readme/garage.png)
![quests](readme/quests.png)
