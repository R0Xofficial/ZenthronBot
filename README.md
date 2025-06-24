![ZenthronBot](https://github.com/R0Xofficial/ZenthronBot/blob/ZenthronBot/banner.png)

# ZenthronBot - An Advanced Moderation & Management Bot

Meet **ZenthronBot**, a powerful and feature-rich Telegram bot designed for advanced chat moderation and administration. It provides a comprehensive suite of tools for maintaining order, managing users, and ensuring chat security.

## Features

- **Comprehensive Moderation**: A full suite of commands including ban, mute, kick, and purge to effectively manage chat activity.
- **Advanced Security Layers**: Features like a global ban (gban) system and a personal blacklist to protect your communities from malicious users across all groups.
- **Multi-Level Administration**: A robust permission system with three levels: Owner, Sudo users (bot admins), and chat administrators, ensuring granular control over the bot's powerful features.
- **Detailed Information Retrieval**: Commands to get in-depth information about users, chats, and the bot's own operational status.
- **Fully Configurable**: Securely configured via environment variables, allowing for easy and safe deployment.

## How to run

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/R0Xofficial/ZenthronBot zenthron
    ```

2.  **Install requirements:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up your environment variables:**
    Copy the template file:
    ```bash
    cp ~/zenthron/envtemp.sh ~/zenthron/env.sh
    ```
    Then, edit the file to add your tokens and IDs:
    ```bash
    nano ~/zenthron/env.sh
    ```

4.  **Run the bot:**
    Navigate to the bot's directory and run it using the script:
    ```bash
    cd ~/zenthron && . ./env.sh && python zenthron.py
    ```

---

## Command List<br>

### Bot Commands<br>
- **/start**: Shows the welcome message.<br>
- **/help**: Shows the help message.<br>
- **/github**: Get the link to the source code.<br>
- **/owner**: Info about the bot owner.<br>
- **/sudocmds**: List sudo commands.<br>

### User Commands<br>
- **/info <ID/@user/reply>**: Get info about a user.<br>
- **/chatstat**: Get basic stats about the current chat.<br>
- **/kickme**: Kick yourself from the chat.<br>
- **/listadmins**: Show the list of administrators in the current chat. (Alias: `/admins`)<br>

### Management Commands<br>
- **/ban <ID/@user/reply> [Time] [Reason]**: Ban a user from the chat.<br>
- **/unban <ID/@user/reply>**: Unban a user from the chat.<br>
- **/mute <ID/@user/reply> [Time] [Reason]**: Mute a user in the chat.<br>
- **/unmute <ID/@user/reply>**: Unmute a user in the chat.<br>
- **/kick <ID/@user/reply> [Reason]**: Kick a user from the chat.<br>
- **/promote <ID/@user/reply> [Title]**: Promote a user to administrator.<br>
- **/demote <ID/@user/reply>**: Demote an administrator to a regular member.<br>
- **/pin <loud|notify>**: Pin the replied-to message.<br>
- **/unpin**: Unpin the replied-to message.<br>
- **/purge <silent>**: Deletes messages up to the replied-to message.<br>
- **/report <ID/@user/reply> [reason]**: Report a user to the administrators.<br>

### Security<br>
- **/enforcegban <yes/no>**: Enable/disable Global Ban enforcement in this chat (Chat Creator only).<br>

### 4FUN Commands
- **/kill <@user/reply>**: Metaphorically eliminate someone.<br>
- **/punch <@user/reply>**: Deliver a textual punch.<br>
- **/slap <@user/reply>**: Administer a swift slap.<br>

### Sudo Commands<br>
- **/status**: Show bot status.<br>
- **/cinfo [Optional chat ID]**: Get detailed info about the current or specified chat.<br>
- **/say [Optional chat ID] [Your text]**: Send a message as the bot.<br>
- **/blist <ID/@user/reply> [Reason]**: Add a user to the blacklist.<br>
- **/unblist <ID/@user/reply>**: Remove a user from the blacklist.<br>
- **/gban <ID/@user/reply> [Reason]**: Ban a user globally.<br>
- **/ungban <ID/@user/reply>**: Unban a user globally.<br>
> *Note: Sudo users can use management commands like /ban, /mute, etc., even if they are not chat administrators.*<br>

### Owner Commands<br>
- **/leave [Optional chat ID]**: Make the bot leave a chat.<br>
- **/speedtest**: Perform an internet speed test.<br>
- **/listsudo**: List all users with sudo privileges.<br>
- **/addsudo <ID/@user/reply>**: Grant SUDO (bot admin) permissions to a user.<br>
- **/delsudo <ID/@user/reply>**: Revoke SUDO (bot admin) permissions from a user.<br>
