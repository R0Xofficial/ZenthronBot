![ZenthronBot](https://github.com/R0Xofficial/ZenthronBot/blob/ZenthronBot/banner.png)

# ZenthronBot - An Advanced Moderation & Management Bot

Meet **ZenthronBot**, a powerful and feature-rich Telegram bot designed for advanced chat moderation and administration. It provides a comprehensive suite of tools for maintaining order, managing users, and ensuring chat security.

## Features

- **Comprehensive Moderation**: A full suite of commands including ban, mute, kick, and purge to effectively manage chat activity.
- **Advanced Security Layers**: Features like a global ban (gban) system and a personal blacklist to protect your communities from malicious users across all groups.
- **Multi-Level Administration**: A robust permission system with three levels: Owner, Developer Sudo, Support users (bot admins), and chat administrators, ensuring granular control over the bot's powerful features.
- **Detailed Information Retrieval**: Commands to get in-depth information about users, chats, and the bot's own operational status.
- **Fully Configurable**: Securely configured via environment variables, allowing for easy and safe deployment.

## Known Bugs
- **Groups with topics** Description: The bot works, but its functionality in the topics of a given group disappears. The bot cannot force a search using the user resolver. The target is always the user who created the topic. (It is recommended to use the bot on the General topic). 

## How to run

1.  **Clone the repository:**
    ```bash
    git clone --branch ZenthronBot-Modular https://github.com/R0Xofficial/ZenthronBot.git tgbot
    ```

2.  **Install requirements:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up your environment variables:**
    ```bash
    nano ~/tgbot/ZenthronBot/.env
    ```

4.  **Run the bot:**
    Navigate to the bot's directory and run it using the script:
    ```bash
    cd ~/tgbot && python3 -m ZenthronBot.main
    ```


# Official Links:
-   **Support Chat:** https://t.me/ZenthronSupport
-   **BOT Link:** https://t.me/ZenthronRoBot
