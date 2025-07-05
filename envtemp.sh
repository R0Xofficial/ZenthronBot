#!/bin/bash
# ZenthronBot - Environment file
# Copyright (C) 2025 R0X
# Licensed under the GNU General Public License v3.0
# See the LICENSE file for details.

# --------------------------
# --- REQUIRED VARIABLES ---
# --------------------------

# --- PTB Bot Configuration ---
# Set your BOT token here in "".
# To generate a BOT token, create your bot with @BotFather in Telegram.
export TELEGRAM_BOT_TOKEN="PASTE_HERE"

# Set your OWNER ID here in "".
# To get your account ID, you can use any bot that has the /info command, e.g. @MissRose_bot
export TELEGRAM_OWNER_ID="PASTE_HERE"


# --- Telethon User-Client Configuration ---
# These are required for the bot's advanced features (e.g., finding users by @username).
# Go to https://my.telegram.org -> "API development tools" to get them.
# IMPORTANT: These values belong to your personal user account, not the bot's account.

# Your personal API_ID from my.telegram.org
export TELEGRAM_API_ID="PASTE_HERE"

# Your personal API_HASH from my.telegram.org
export TELEGRAM_API_HASH="PASTE_HERE"


# --------------------------
# --- OPTIONAL VARIABLES ---
# --------------------------
# To enable an optional feature, remove the '#' from the line beginning with 'export'.

# Set your bot log ID chat/channel here in "".
# If you don't set it, the bot will send logs to the owner's PM.
#
# export LOG_CHAT_ID="PASTE_HERE"

# Set your TENOR API here so that gifs appear with the 4FUN commands.
# Go to https://developers.google.com/tenor/guides/quickstart to generate your key.
#
# export TENOR_API_KEY="PASTE_HERE"

# --------------------------------------------------------------------
# --- Google Gemini AI Configuration (OPTIONAL for /askai command) ---
# --------------------------------------------------------------------
# To enable the /askai command, you need a Gemini API key.
#
# How to get your API key:
# 1. Go to Google AI Studio: https://aistudio.google.com/
# 2. Log in with your Google Account.
# 3. Click the "Get API key" button in the top left.
# 4. Click "Create API key in new project".
# 5. Copy the generated key and paste it below.
#
# IMPORTANT: This key is not required for the bot to run, only for the AI features.
# To enable it, remove the '#' from the line below and paste your key.

# export GEMINI_API_KEY="PASTE_HERE"

# ----------------------------------
# --- Appeal Chat Configuration  ---
# ----------------------------------
# This variable stores the contact point for users who want to appeal a ban.
# It is REQUIRED for the bot to start.
#
# You can use one of three formats:
# 1. A username: @YourSupportChat
# 2. A public link: https://t.me/YourSupportChat
# 3. Any other text, e.g. "Contact the admin in the main group"
#
# The bot will display this text exactly as you write it.
#
# EXAMPLE:
# export APPEAL_CHAT_USERNAME="@ZenthronSupport"

export APPEAL_CHAT_USERNAME="PASTE_HERE"

# ID of the chat where the bot should have special permissions for blacklisted people.
# Use the /id command in this chat to find out. Remember the minus sign at the beginning for groups. 
export APPEAL_CHAT_ID="PASTE_HERE"


# -------------------------------------------------------------
echo "Environment variables set."
