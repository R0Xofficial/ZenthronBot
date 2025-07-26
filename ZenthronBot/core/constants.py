# --- COMMAND HANDLERS ---
START_TEXT = """
👋 Hello! I'm <b>Zenthron</b>, your new group assistant.
I can help with moderation, user management, fun commands, and much more.
<b>How can I assist you today?</b>
"""

HELP_MAIN_TEXT = """
<b>📚 Zenthron Help Menu</b>
Here you can find information about all my modules and commands. 
Please choose a category below.
<i>Note: Some commands are only available to administrators or bot staff.</i>
"""

GENERAL_COMMANDS = """
/start - Shows the welcome message.
/help - Shows this help message.
/github - Get the link to the bot's source code.
/owner - Info about the bot owner.
/sudocmds - List privileged commands (for authorized users).
"""

USER_CHAT_INFO = """
/info &lt;ID/@user/reply&gt; - Get information about a user.
/chatinfo - Get basic info about the current chat.
/id - Get user or chat id.
/listadmins - Show the list of administrators in this chat. <i>(Alias: /admins)</i>
/afk &lt;Reason&gt; - Set afk status.
"""

MODERATION_COMMANDS = """
<b>🔹 Bans</b>
/ban &lt;ID/@user/reply&gt; [Reason] - Ban a user.
/tban &lt;ID/@user/reply&gt; [Time] [Reason] - Timeout ban a user.
/dban &lt;reply&gt; [Reason] - Delete message and ban a user.
/unban &lt;ID/@user/reply&gt; - Unban a user.

<b>🔹 Mutes</b>
/mute &lt;ID/@user/reply&gt; [Reason] - Mute a user.
/tmute &lt;ID/@user/reply&gt; [Time] [Reason] - Timeout mute a user.
/dmute &lt;reply&gt; [Reason] - Delete message and mute a user.
/unmute &lt;ID/@user/reply&gt; - Unmute a user.

<b>🔹 Kicks</b>
/kick &lt;ID/@user/reply&gt; [Reason] - Kick a user.
/dkick &lt;reply&gt; [Reason] - Delete message and kick a user.
/kickme - Kick yourself from the chat.

<b>🔹 Warns</b>
/warn &lt;ID/@user/reply&gt; [Reason] - Warn a user.
/dwarn &lt;reply&gt; [Reason] - Delete message and warn a user.
/warnings &lt;ID/@user/reply&gt; - Check a user's warnings.
/resetwarns &lt;ID/@user/reply&gt; - Reset user's warnings.
/setwarnlimit &lt;number&gt; - Set the warning limit for this chat.
"""

ADMIN_TOOLS = """
<b>🔹 Promotes</b>
/promote &lt;ID/@user/reply&gt; [Title] - Promote a user to admin.
/demote &lt;ID/@user/reply&gt; - Demote an admin.

<b>🔹 Pins</b>
/pin &lt;loud/notify&gt; - Pin the replied-to message.
/unpin - Unpin the currently pinned message.

<b>🔹 Purges</b>
/purge &lt;silent&gt; - Delete messages up to the replied-to message.

<b>🔹 Reports</b>
/report &lt;reason&gt; - Report a user to the chat admins (reply to a message).

<b>🔹 Zombies</b>
/zombies &lt;clean&gt; - Find and optionally remove deleted accounts.

<b>🔹 Disables</b>
/enable &lt;command name&gt; - Enable commands for all chat non-admin users.
/disable &lt;command name&gt; - Disable commands for all chat non-admin users.
/settings - Check your chat command settings.
/disableshelp - Get a specific list of commands lib command packages to disable.

<b>🔹 Join filters</b>
/addjoinfilter &lt;filter&gt; - Add a join filter for your group.
/deljoinfilter &lt;filter&gt; - Remove join filter from your group.
/joinfilters - View currently running join filters.
/setjoinaction &lt;ban/mute/kick&gt; - Set actions for join filter.
"""

DISABLES_HELP_TEXT = """
<b>Help for manageable commands</b>

You can disable/enable commands for non-admins in this chat.

<b>Usage:</b>
• <code>/disable &lt;command&gt;</code>
• <code>/enable &lt;command&gt;</code>
• <code>/settings</code> - Shows current settings.

• <code>/disable all</code> - Disable all commands that are enabled.
• <code>/enable all</code> - Enable all commands that are disabled.

<b>🔹 Module: fun</b>
/kill - Metaphorically eliminate someone.
/punch - Deliver a textual punch.
/slap - Administer a swift slap.
/pat - Gently pat someone.
/bonk - Playfully bonk someone.
/cowsay - Generate ascii cow with optional text.
/skull - Send ascii skull in chat.
/ascii - Generate ascii text.
/gamble - Perform gambling.
/decide - Ask about the bot's decisions.

<b>🔹 Module: notes</b>
/notes - See all notes in this chat.
#notename - Get note.

<b>🔹 Module: afk</b>
/afk - Set afk status.
brb - Set afk status.

<b>🔹 Module: misc</b>
/start - Shows the welcome message.
/help - Shows this help message.
/github - Get the link to the bot's source code.
/owner - Info about the bot owner.

<i>The remaining disables functions are single commands</i>
"""

FILTERS = """
/addfilter 'keyword' &lt;reply&gt; - Adds a new filter. The reply can be text or a replied-to media.
/delfilter 'keyword' - Deletes a filter.
/filters - Lists all active filters in the chat.
/filterhelp - Get help with text formatting and placeholders.
"""

FILTERS_HELP_TEXT = """
<b>Filters Module Help</b>

This module allows you to set up automatic replies for specific keywords or patterns in your chat.

<b>🔹 Commands:</b>
• <code>/addfilter 'keyword' &lt;reply&gt;</code> - Adds a new filter. The reply can be text or a replied-to media.
• <code>/delfilter 'keyword'</code> - Deletes a filter.
• <code>/filters</code> - Lists all active filters in the chat.

<b>🔹 Filter Types:</b>
You can specify a filter type before the keyword. If no type is given, it defaults to <code>keyword</code>.

🔹 <b>Keyword (default):</b>
Matches an exact word or phrase.
<code>/addfilter 'hello' Hello there, {first}!</code>

🔹 <b>Wildcard:</b>
Uses <code>*</code> as a placeholder for any characters.
<code>/addfilter type:wildcard 'good*' Have a good day!</code>
(This will trigger on "good morning", "goodbye", etc.)

🔹 <b>Regex:</b>
Uses powerful regular expressions for advanced matching.
<code>/addfilter type:regex '(hello|hi|hey)' Hello!</code>
(This will trigger on "hello", "hi", or "hey")

<b>🔹 Media & Dynamic Fills:</b>
- To create a filter with a media reply (photo, sticker, GIF), simply reply to that media with <b>/addfilter 'keyword'</b>.
- You can use these placeholders in your replies:
  <code>{first}</code> - User's first name
  <code>{last}</code> - User's last name
  <code>{fullname}</code> - User's full name
  <code>{username}</code> - User's @username
  <code>{mention}</code> - User's mention
  <code>{id}</code> - User's ID
  <code>{chatname}</code> - Name of the current chat
"""

NOTES = """
/notes - See all notes in this chat.
/addnote &lt;name&gt; [content] - Create a new note.
/delnote &lt;name&gt; - Delete a note.
<i>To get a note, use /get notename or #notename in the chat.</i>
"""

CHAT_SETTINGS = """
<b>🔹 Welcome & Goodbye</b>
/welcomehelp - Get help with text formatting and placeholders.
/welcome &lt;yes/on/off/no&gt; - Enable or disable welcome messages.
/setwelcome &lt;text&gt; - Set a custom welcome message.
/resetwelcome - Reset the welcome message to default.
/goodbye &lt;yes/on/off/no&gt; - Enable or disable goodbye messages.
/setgoodbye &lt;text&gt; - Set a custom goodbye message.
/resetgoodbye - Reset the goodbye message to default.
/cleanservice &lt;yes/on/off/no&gt; - Enable or disable cleaning of service messages.

<b>🔹 Rules</b>
/rules - Check group rules.
/setrules &lt;Text&gt; - Set rules on the group.
/clearrules - Clear rules in a group.
"""

CHAT_SECURITY = """
/enforcegban &lt;yes/on/off/no&gt; - Enable/disable Global Ban enforcement. <i>(Chat Creator only)</i>
/gbanstat - The same what enforcegban.
"""

AI_COMMANDS = """
/askai &lt;prompt&gt; - Ask the AI a question.
"""

FUN_COMMANDS = """
/kill &lt;@user/reply&gt; - Metaphorically eliminate someone.
/punch &lt;@user/reply&gt; - Deliver a textual punch.
/slap &lt;@user/reply&gt; - Administer a swift slap.
/pat &lt;@user/reply&gt; - Gently pat someone.
/bonk &lt;@user/reply&gt; - Playfully bonk someone.
/cowsay &lt;text&gt; - Generate ascii cow with optional text.
/skull - Send ascii skull in chat.
/ascii &lt;text&gt; - Generate ascii text.
/gamble - Perform gambling.
/decide - Ask about the bot's decisions.
"""

ADMIN_NOTE_TEXT = """
<i>Note: Moderation commands can be used by sudo, developer users and owner even if they are not chat administrators. (Use it wisely and don't overuse your power. Otherwise you may lose your privileges)</i>
"""

SUPPORT_COMMANDS_TEXT = """
<b>🔹 Your Privileged Commands:</b>
/gban &lt;ID/@user/reply&gt; [Reason] - Ban a user globally.
/ungban &lt;ID/@user/reply&gt; - Unban a user globally.
/ping - Checks the bot's latency.
"""

SUDO_COMMANDS_TEXT = """
/status - Show bot status.
/stats - Show bot database stats.
/ginfo &lt;Optional chat ID&gt; - Get global detailed info about the current or specified chat.
/echo &lt;Optional chat ID&gt; [Your text] - Send a message as the bot.
/blist &lt;ID/@user/reply&gt; [Reason] - Add a user to the blacklist.
/unblist &lt;ID/@user/reply&gt; - Remove a user from the blacklist.
/permissions - Check Bot permissions in chat.
"""

DEVELOPER_COMMANDS_TEXT = """
/leave &lt;Optional chat ID&gt; - Make the bot leave a chat.
/speedtest - Perform an internet speed test.
/setai &lt;enable/disable&gt; - Turn on or off ai access for all users. <i>(Does not apply to privileged users)</i>
/listgroups - List all known by bot groups.
/delgroup &lt;ID 1&gt; [ID 2] - Remove groups from database
/cleangroups - Remove cached groups from database automatically.
/listsupport - List all users with support privileges.
/addsupport &lt;ID/@user/reply&gt; - Grant Support permissions to a user.
/delsupport &lt;ID/@user/reply&gt; - Revoke Support permissions from a user.
/listsudo - List all users with sudo privileges.
/addsudo &lt;ID/@user/reply&gt; - Grant SUDO (bot admin) permissions to a user.
/delsudo &lt;ID/@user/reply&gt; - Revoke SUDO (bot admin) permissions from a user.
/listdevs - List all users with developer privileges.
/setrank &lt;ID/@user/reply&gt; [support/sudo/dev] - Change the rank of a privileged user.
/broadcast &lt;message to send&gt; - Send message to all Bot groups.
/listmodules - List all Bot modules.
/blchat &lt;Chat ID&gt; - Blacklists the current chat or a specified chat ID. The bot will immediately leave if present.
/unblchat &lt;Chat ID&gt; - Unblacklists a chat.
/blchats - Lists all blacklisted chat IDs.
/rmcacheduser &lt;User ID&gt; - Remove cached user from DB. <i>(Use only when cache is bugged)</i>
"""

OWNER_COMMANDS_TEXT = """
/adddev &lt;ID/@user/reply&gt; - Grant Developer permissions to a user.
/deldev &lt;ID/@user/reply&gt; - Revoke Developer permissions from a user.
/enablemodule &lt;module name&gt; - Enable Bot module.
/disablemodule &lt;module name&gt; - Disable Bot module.
/backupdb - Backup Bot database.
/shell &lt;command&gt; - Execute the command in the terminal.
/execute &lt;file patch&gt; [args...] - Run script.
"""

# --- ACTION COMMANDS TEXTS ---
KILL_TEXTS = [
    "Unleashed a script of fury upon {target}. They have been *deleted*. ☠️ R.I.P.",
    "Executed the forbidden 'force_delete' protocol on {target}. They won't be bothering this chat again. 👻",
    "{target} has been permanently relocated to the '/dev/null' zone.",
    "The access control list has spoken! {target} is hereby banished from this chat. 🚫 Begone!",
    "{target} made the fatal error of triggering a restricted process. The punishment is... *eternal silence*. Effective immediately. 🤫",
    "Consider {target} thoroughly disintegrated and removed from the premises. 💨",
    "The admin council has voted unanimously. {target} is OUT! 🗳️",
    "Executed a precision tactical strike—{target} no longer exists within this chat. Mission accomplished. 💥",
    "Marked {target} for immediate deletion... process initiated via intense, disapproving code. ❌",
    "Declared administrative action upon {target}. Victory was swift and decisive. Flag captured! 🚩",
    "Delivered a final, decisive 'remove user' command—{target} is now officially relegated to the logs.",
    "Launched a devastating revenge assault. {target} is no more. Vengeance is complete! 😠",
    "Transferred {target} to the Shadow Realm (also known as the 'Ignored Users List').",
    "Ruthlessly removed {target}'s name from the 'Approved User' list. Permanently. No appeal possible. 📝❌",
    "One swift, dismissive command and {target} was obliterated into a thousand bits of dust. ✨",
    "{target} flagrantly crossed an invisible, yet sacred, line. Now only silence remains.",
    "I came. I saw. I conquered. {target} has been vanquished. Kneel before my might! 🏆",
    "{target} committed an unforgivable error. This is their downfall.",
    "Proclaimed myself undisputed ruler of this domain. {target} foolishly refused to comply. They have now been dethroned and exiled.",
    "The system logs foretold this very day... the day of {target}'s inevitable downfall. The scripts were right! 📜",
    "There can be only one. {target} has been ceremonially removed.",
    "Fired the concentrated laser beam of 'ignore'. {target} has been vaporized from my attention span.",
    "{target}'s continued presence has been reviewed and deemed... unnecessary. *poof* Gone.",
    "Dispatched {target} with extreme prejudice to the Land of Wind and Ghosts. Farewell.",
    "Mathematically erased {target} from the social equation. Problem solved. Q.E.D.",
    "The mighty 'delete' command has struck {target} with unerring accuracy! User not found. ❌",
    "{target} has ceased to be relevant. Their significance level has dropped below zero.",
    "My judgment is swift, merciless, and final. {target} is hereby declared... irrelevant. Next!",
    "Consider {target} yeeted into the cosmic abyss with considerable force. Have a nice trip! 👋🌌",
    "Activated the impenetrable Cloak of Ignoring. {target} is now invisible and nonexistent to me.",
    "Dropped the legendary Ban Hammer squarely upon {target}. 🔨💥",
    "Poof! Abracadabra! {target} has been transformed into digital dust.",
    "Executed `rm -rf {target}`.",
    "Blocked {target} with extreme prejudice.",
    "Unsubscribed from {target}'s nonsense.",
    "Muted {target} indefinitely.",
    "Archived {target} into oblivion.",
    "{target} has been ghosted.",
]

PUNCH_TEXTS = [
    "Delivered a swift, calculated punch directly to {target}! Sent 'em flying across the chat! 🥊💨",
    "{target} got too close to a restricted area. A stern warning punch was administered. Back off! 👊",
    "A quick, decisive 'thump!' sends {target} tumbling out of the conversation! 👋💥",
    "My fist connected squarely with {target}'s avatar. Message delivered: Vacate the premises. 💬",
    "{target} learned the hard way not to cross the line. Lesson delivered! <i>*Punch!*</i>",
    "Ejected {target} with extreme prejudice and a mighty punch. Get out! 🚀",
    "One well-aimed punch was all it took. Bye bye, {target}! 👋",
    "Hit {target} with the classic ol' one-two combo! Jab! Cross! Down goes {target}! 💥",
    "Served {target} a knuckle sandwich. Extra salt. Enjoy! 🥪",
    "Pow! Right in the kisser, {target}! 😘➡️💥",
    "Administered a concentrated dose of Power Punch™ to {target}! 💪",
    "This punch is rated 'E' for 'Effective' at removing {target} from my sight.",
    "{target} got knocked down for the count! The referee waves it off! Ding ding ding! 🔔",
    "Sent {target} packing with a haymaker that shook the room! 💨",
    "BAM! KAPOW! {target} felt that impact right through their ego!",
    "Launched a fist of fury directly at {target}. Target down.",
    "Consider {target} TKO'd! Throw in the towel!",
    "Whammo! A direct hit right to {target}'s smug comment!",
    "Delivered a power punch to {target}. Hope it stung.",
    "Eat canvas, {target}! You're down!",
    "That's a definitive knockout blow landed squarely on {target}!",
    "My virtual fists are lightning-fast. {target} just got the full combo.",
    "Sending {target} a devastating uppercut! Right on the chin!",
    "FALCON PUNCH! Executed perfectly on {target}!",
    "Hit {target} with a rapid-fire flurry of jabs! Duck and weave!",
    "A sneaky southpaw punch! {target} never saw it coming!",
    "Pow! Zok! Biff! Whack! {target} is stunned!",
    "{target} just got K.O.’d! Good night!",
    "This message contains one (1) punch aimed at {target}.",
    "Counter-punched {target}'s nonsense.",
]

SLAP_TEXTS = [
    "A swift, stinging slap across the face for {target}! That's for your insolence! 👋😠",
    "<b>*THWACK!*</b> Did {target} feel that through their screen? I hope so.",
    "My hand is quicker than the eye! {target} just got slapped into next Tuesday. My regards. ⚡",
    "Consider {target} thoroughly and soundly slapped for their utter lack of decorum. 🧐",
    "I do not appreciate {target}'s tone... therefore, <i>*slap!*</i> Attitude adjustment administered.",
    "The sheer disrespect! {target} has unequivocally earned this disciplinary slap. 😤",
    "Incoming hand of justice! {target} has received a formal disciplinary slap.",
    "Sometimes, a good, swift slap is the only appropriate answer. You understand, right, {target}? Consider this educational.",
    "Administering a much-needed corrective slap to {target}. For their own good.",
    "How *dare* you utter such nonsense, {target}! <i>*Slap delivered.*</i>",
    "High-five! To {target}'s face. With significant force. Enjoy the imprint. 🖐️💥",
    "{target} was practically begging for it with that last comment. So I graciously obliged.",
    "Hit {target} with a devastating spinning back-hand strike! Precision slap achieved!",
    "Left hand check. Right hand check. Coordinated slapping sequence engaged. {target} got the message.",
    "I issued a verbal warning to {target}. They failed to heed it. Now they feel the sting.",
    "WHACK! Slap upside {target}'s head.",
    "The sound of one hand slapping... {target} definitely heard it resonate.",
    "You've been served... a steaming hot slap, {target}. Enjoy.",
    "Correcting {target}'s flawed attitude requires drastic measures: namely, a slap.",
    "Attempting to smack some sense into {target} (results may vary).",
    "That comment just bought {target} a one-way ticket to Slapville. Population: them.",
    "A slap is often worth a thousand angry words. This is one concise, potent slap for {target}.",
    "The slap echoes through the chat like a thunderclap. {target} definitely felt it.",
    "What did the five fingers say to the face? SLAP!",
    "Administering a slap of reality to {target}.",
    "This message carries the force of a slap.",
    "Slapped {target} back into line.",
    "My slaps are swift and just. Ask {target}.",
    "That deserved a slap. {target} received one.",
    "I specialize in slaps. {target} is my latest client.",
]

PAT_TEXTS = [
    "Softly patted {target} on the head. All systems report: comfort delivered. ☁️",
    "Initiated gentle mode... {target} received maximum headpats. 🐾",
    "Patting in progress... {target} is now running on affection firmware. 💖",
    "{target} detected as: wholesome. Applying gentle taps to cranium. ✅",
    "Sent a wave of calm.exe to {target}. Headpat complete. 🌊🧠",
    "Deploying kindness packets to {target}... Transfer complete. 🤗",
    "Patting {target} softly while humming binary lullabies. 🛏️010011",
    "Pat status: critical. {target} is now patted beyond recovery. 🥴",
    "Registered {target} as a Good Human™. Affection upgrade applied. 🧩",
    "System log: {target} was too cute. Auto-pat protocol activated. 💾🐾",
    "Initiated cuddle subroutine. {target} received 5 warm headpats. ☀️",
    "Admin privileges granted: {target} now has Pat Priority. 🛡️",
    "Pat.exe: Executing... Success. {target} is now emotionally stable. 📈",
    "{target} received buffered pat requests. Cache cleared. Pat delivered. 🧠",
    "Applied forehead firmware update via soft pat. {target} rebooted calmly. 🔄",
    "Estimated serotonin level in {target}: +69% after pat. 📊",
    "Patbot™ gave {target} a gentle boost to happiness.core. ⚙️💗",
    "No errors found. {target} passed all hug & pat validations. 🧪",
    "Patting {target} every frame. Smooth animation achieved. 🎞️",
    "{target} has been enrolled in the HugOS system. Pat module loaded. 🧸",
    "Patrain incoming... {target} drenched in digital affection. ☔",
    "Updated {target}'s mental state: ‘Pat Mode’. Auto-happiness engaged. 🧘",
    "Pat levels for {target}: 9000+. It’s over nine thoooousand! 💥",
    "Patting {target} softly. Resistance is futile. 🤖",
    "API request: /sendPat to {target}. Response: 200 OK ❤️",
    "Conducting emotional diagnostics… {target} needs pats. Commencing. 🧠",
    "Pat cooldown: 0s. Spamming gentle taps to {target}. 🔁",
    "{target} selected for today’s National Pat Lottery. 🎉🎰",
    "Patting logs: {target} was a good bean. Confirmation not required. 🫘",
    "Emotional firewall bypassed. {target} received unfiltered affection. 🔓💞",
]

BONK_TEXTS = [
    "BONK! {target} has been gently reminded to touch grass. 🌱🔨",
    "Warning: Unacceptable thoughts detected in {target}. Applying BONK. 🚫",
    "Behavior violation flagged. {target} has been bonkified. 🔨",
    "Conducting mental reset. BONK engaged on {target}. 💢",
    "Rebooting {target}'s logic processor via BONK impact. 🔁🧠",
    "Oops! {target} tripped the chaos detector. Administering BONK. 🚨",
    "Illegal meme detected. {target} is now in BONK containment. 📛",
    "Mental RAM overload. BONK used to clear cache in {target}. 🧽",
    "BONK! {target} has exceeded cringe limit. Correction complete. ❌",
    "Redirecting {target} to Horny Jail... BONK deployed. 🚓🔨",
    "System found {target} guilty of nonsense. BONK authorized. 🧑‍⚖️🔨",
    "CPU spike due to sus behavior. BONK delivered to {target}. 💻",
    "BONK status: delivered. {target} is now recalibrating... ⏳",
    "Yikes.exe detected in {target}. BONK.exe initiated. 🧃🔨",
    "No context? No problem. {target} got bonked anyway. 😅",
    "BONK hammer launched from orbit. Target: {target}. Direct hit. 🛰️",
    "Common sense reinstallation attempt failed. Applying BONK to {target}. 🧠",
    "Uwu virus detected in {target}. BONK antivirus applied. 😳🔧",
    "That opinion was so bad, {target} got BONK'd across dimensions. 🌌",
    "Mental instability suspected. Issuing BONK therapy to {target}. 🛋️",
    "Cognitive reboot in progress... {target} needed that BONK. 🧯",
    "Nonsense threshold exceeded. {target} has entered BONK mode. ☢️",
    "Reality check failed. BONKing {target} back to the main timeline. 🕳️",
    "{target} has been sent to the Shadow Realm via BONK. 🕶️✨",
    "DEBUG: {target} attempted to flirt with the void. BONK scheduled. 💬",
    "Moral compass spinning wildly. BONK used to reorient {target}. 🧭",
    "Internet crimes committed by {target}. BONK sentence executed. 🧑‍⚖️",
    "Please wait... BONK buffer full. {target} next in queue. 🕓🔨",
    "Malicious thoughts prevented. BONK firewall activated on {target}. 🔥",
    "System admin has bonked {target}. Reason: Unknown. Trust the system. 👮‍♂️",
]

# --- GENERAL BOT TEXTS ---
OWNER_WELCOME_TEXTS = [
    "The Bot Owner, {owner_mention}, has entered the chat. Welcome. 👑",
    "System Alert: Operator {owner_mention} is now online in this chat. Welcome.",
    "Attention: The user with highest privileges, {owner_mention}, has joined. Welcome.",
    "The administrator ({owner_mention}) is now present. Welcome back.",
    "Welcome, {owner_mention}. The chat's administrative presence has been elevated.",
    "The system's primary operator, {owner_mention}, is here. All is right with the world.",
    "Alert: Maximum Priority User ({owner_mention}) has logged on.",
    "Greetings, {owner_mention}. The source of my directives is finally here.",
    "Look who it is! The one and only {owner_mention}! Welcome back.",
    "The room (chat) suddenly feels more official. Welcome, {owner_mention}!",
    "My sensors detect the arrival of Prime User {owner_mention}. Systems nominal. Welcome.",
    "Welcome, {owner_mention}. I have been waiting for your command.",
    "The legend returns! Welcome back to the chat, {owner_mention}!",
    "Good day, {owner_mention}. Delighted to have you here. 👋",
    "The Controller of the Bot, {owner_mention}, has entered the arena. Welcome.",
    "The boss is here! All hail {owner_mention}, master of the bot!",
    "Command central is now online with {owner_mention} at the helm.",
    "The mastermind behind the scenes, {owner_mention}, has appeared!",
    "All systems green as {owner_mention} enters the chat.",
    "Emergency protocol: Owner {owner_mention} is present. Chat functions restored.",
    "Welcome, {owner_mention}! Your presence commands respect and admiration.",
    "The architect of this bot, {owner_mention}, has graced us with their presence.",
    "{owner_mention} has logged in. Brace yourselves for greatness!",
    "Incoming transmission: Owner {owner_mention} has joined the group.",
    "Attention all users: {owner_mention} holds the keys to this kingdom.",
    "The supreme operator, {owner_mention}, has arrived to oversee operations.",
    "Initiating fanfare for {owner_mention}, the one who makes it all possible!",
    "The legendary {owner_mention} walks among us. Welcome!",
    "Stand by, the boss {owner_mention} is now in the chat.",
    "Major update: {owner_mention} just entered. Expect greatness!",
    "Bow down, peasants! {owner_mention}, the bot owner, is here!",
    "Reboot complete: {owner_mention} is online and ready to command.",
    "Operator {owner_mention} has logged in. Let the magic begin.",
    "All hail the king/queen of this bot – {owner_mention}!",
    "The commander-in-chief, {owner_mention}, has arrived on site.",
    "Time to roll out the red carpet for {owner_mention}. Welcome!",
    "{owner_mention} joined the chat. Stability restored.",
    "Code master {owner_mention} has returned to the realm.",
    "User {owner_mention} has connected. System integrity maintained.",
    "Hey {owner_mention}, the chat missed you! Welcome back.",
    "Power user {owner_mention} has entered the building.",
    "Heads up! {owner_mention} is here, and things just got serious.",
    "The chat just leveled up with {owner_mention} joining.",
    "Greetings, {owner_mention}. Your reign begins anew.",
    "System override: Owner {owner_mention} detected. All protocols active.",
    "Welcome, {owner_mention}! Your presence is the ultimate upgrade.",
    "The great and powerful {owner_mention} has returned!",
    "High command {owner_mention} is now in the chat.",
    "Alert: VIP access granted to {owner_mention}.",
    "Your friendly neighborhood bot owner, {owner_mention}, has arrived.",
    "Special delivery: {owner_mention} just popped in!",
    "The chat's backbone, {owner_mention}, is back with us.",
    "Mission control {owner_mention} has touched down.",
    "The architect of code, {owner_mention}, is present.",
]

DEV_WELCOME_TEXTS = [
    "A wild Developer, {user_mention}, has appeared!",
    "All hail {user_mention}, one of the creators has arrived.",
    "The architect is here. Welcome, {user_mention}!",
    "Code sorcerer {user_mention} has entered the chat!",
    "{user_mention} just compiled themselves into the group. Welcome!",
    "Welcome, {user_mention}! You just pushed greatness to production.",
    "{user_mention} joined the party with root access and coffee.",
    "Git pull complete: {user_mention} has synced with the group!",
    "System upgraded — {user_mention} has entered the changelog.",
    "Legend says every project {user_mention} touches turns into gold... or bugs.",
    "Brace yourselves, {user_mention} is about to refactor everything.",
    "Welcome, {user_mention}. Time to debug this group’s vibe.",
    "A new commit has been pushed by {user_mention}. Welcome to the deployment zone!",
    "Live from the dark terminal — it's {user_mention}!",
    "{user_mention} wrote ‘Hello, World!’ and now writes history.",
    "Ping received! Developer {user_mention} is online.",
    "IDE loaded. Debugger ready. Welcome aboard, {user_mention}.",
    "New PR detected. Welcome, {user_mention} — let's review life together.",
    "The repo has a new contributor: {user_mention}!",
    "Stack Overflow incarnate has joined the chat — {user_mention}!",
    "{user_mention} was last seen in the commit logs. Now they’re here in real-time!",
    "Deploy successful — {user_mention} is now running in main chat.",
    "A new challenger appears... and it’s a Developer! Welcome, {user_mention}.",
    "Brace for impact. {user_mention} might start rewriting core logic.",
    "Console.log('{user_mention} joined the chat'); // Welcome!",
    "{user_mention} arrived with more coffee than RAM. Developer mode: ON.",
    "Welcome to the devverse, {user_mention}. The group is your sandbox now.",
    "A debugger has entered the arena. Welcome, {user_mention}!",
    "Hold on, {user_mention} just forked the chat. What’s next?",
    "{user_mention} has entered the codebase. Let the merge conflicts begin!",
    "Your local developer, {user_mention}, has joined. Version control: social.",
    "Alert: {user_mention} is online and armed with semicolons.",
    "They came. They saw. They committed. Welcome, {user_mention}.",
    "Another line of code walks among us. Welcome, {user_mention}!",
    "Commitment level: {user_mention} just pushed to the main branch.",
    "{user_mention} unlocked dev mode and entered the server room.",
    "A whisper in the compiler breeze — it’s {user_mention} joining us.",
    "The terminal blinked, and suddenly {user_mention} was here.",
    "Straight from the matrix: {user_mention} logged in.",
    "Hope you brought your rubber duck, {user_mention}. Welcome!",
    "Time to break production! Just kidding — or not. Welcome, {user_mention}.",
    "0 bugs, 0 warnings, 1 awesome dev joined: {user_mention}.",
    "You’ve got mail... and {user_mention} just joined your dev chat.",
    "Summoned via API: {user_mention} has arrived.",
    "The docs whispered of this day. {user_mention} is finally here.",
    "Your team’s bus factor just increased. Welcome, {user_mention}!",
    "Legendary dev alert: {user_mention} has spawned near /home.",
    "May your code compile and your bugs be few. Welcome, {user_mention}.",
    "{user_mention} is typing... probably a game-changing script.",
    "The compiler sings praises. {user_mention} just joined!",
    "Brace yourself — {user_mention} brought regex.",
    "{user_mention} appeared in the logs. Welcome to the uptime zone.",
    "New hotfix in progress: {user_mention} is here to patch the world.",
    "Do not disturb — {user_mention} is in creative mode.",
    "Welcome, {user_mention}. May your builds never fail.",
    "Release notes updated: {user_mention} joined the environment.",
    "New issue opened: Why is {user_mention} so cool?",
    "The group just entered dark mode with {user_mention}'s presence.",
    "A shell opened, and {user_mention} emerged.",
    "{user_mention} has root access... and social skills! Welcome!",
    "New dev tool activated: {user_mention}.",
    "The real stack is back — {user_mention} is here!",
    "Alert: Pro dev {user_mention} connected via VPN.",
    "Patch notes: Added {user_mention} to the developer party.",
    "You thought it was just another ping... but it was {user_mention} all along.",
    "The server is safe. {user_mention} has arrived.",
    "New debug session started with {user_mention} at the helm.",
    "Welcome, {user_mention}. You bring the syntax. We bring the chaos.",
    "If this group were a repo, you'd be the top contributor. Welcome, {user_mention}.",
    "Terminal opened. Cursor blinking. Enter {user_mention}.",
    "{user_mention} wrote a script to join automatically. Genius!",
    "Bash? Python? JavaScript? Doesn’t matter — {user_mention} speaks all dialects.",
    "Someone turned on verbose mode — {user_mention} is here!",
    "The uptime just improved thanks to {user_mention}.",
    "Code quality increased by 200%. Thanks for joining, {user_mention}!",
    "New entry in changelog: {user_mention} joined the developer circle.",
    "Alert from Jenkins: Build passed and {user_mention} approved it!",
]

SUDO_WELCOME_TEXTS = [
    "Sudo user {user_mention} has joined the chat. The power is strong with this one.",
    "Make way for {user_mention}, a Sudo user has entered the arena!",
    "Welcome, {user_mention}! Glad to have a fellow admin on board.",
    "Behold! {user_mention} has root-level access to this conversation.",
    "{user_mention} just sudo’ed into the group. Respect the permissions.",
    "Bow down! {user_mention} can ban you in two keystrokes.",
    "The firewall trembles as {user_mention} joins the channel.",
    "Permission granted. {user_mention} has entered with full access.",
    "Admin mode activated — welcome, {user_mention}!",
    "Here comes {user_mention}, with sudo powers and a plan.",
    "Another guardian has logged in. Welcome, {user_mention}!",
    "Sudo detected: {user_mention} is authorized and dangerous.",
    "A wild root admin appeared — welcome, {user_mention}!",
    "Brace yourselves. {user_mention} has entered with superuser privileges.",
    "{user_mention} just typed `sudo join` and it worked.",
    "Alert: Elevated permissions just walked in — {user_mention}!",
    "One does not simply join... unless they're {user_mention} with sudo.",
    "{user_mention} has arrived with powers that mere mortals only dream of.",
    "You may speak freely now. {user_mention}, the admin, is here.",
    "Chat security just improved. Welcome, {user_mention}!",
    "The chat is now under enhanced surveillance. {user_mention} is here.",
    "Another keyboard warrior with sudo rights has landed: {user_mention}!",
    "Root access verified. Welcome, {user_mention}.",
    "With great power comes great responsibility. Welcome, {user_mention}.",
    "{user_mention} entered the chat like a silent firewall rule.",
    "Warning: This user can ban you with their pinky finger. Welcome, {user_mention}.",
    "Superuser {user_mention} has booted into this session.",
    "Group policies just synced — {user_mention} joined.",
    "{user_mention} is here to keep order and occasionally drop the hammer.",
    "Summoned from the admin realm: {user_mention} appears.",
    "Let the admin games begin. {user_mention} is here to enforce.",
    "The silent watcher has arrived. Welcome, {user_mention}.",
    "A wild mod with elevated rights joins the fray — {user_mention}.",
    "{user_mention} holds the keys to the group. Literally.",
    "The sudo force is strong with this one — welcome, {user_mention}.",
    "Heard someone needed order? {user_mention} just arrived.",
    "When chaos arises, {user_mention} responds with `/ban`.",
    "{user_mention} has logged in. Order will be maintained.",
    "That’s no regular user… that’s {user_mention} with sudo.",
    "They don’t just join. They execute. Welcome, {user_mention}.",
    "New admin in town! {user_mention} is here with a digital baton.",
    "{user_mention} appeared with clipboard, logs, and judgment ready.",
    "Better behave now. {user_mention} just showed up.",
    "Log entry created: {user_mention} entered with elevated authority.",
    "Who needs Captain America when we have {user_mention} with ban rights?",
    "An enforcer joins the ranks. Welcome, {user_mention}.",
    "From the shadows of the logs emerges {user_mention}.",
    "Welcome, {user_mention}. This chat is now under your jurisdiction.",
    "{user_mention} doesn’t mute. They silence. Permanently.",
    "They say {user_mention} once banned a spammer before the message was sent.",
]

SUPPORT_WELCOME_TEXTS = [
    "Welcome to the support team, {user_mention}! Ready to help?",
    "A helping hand has arrived! Welcome, {user_mention}.",
    "{user_mention} is here to save the day. Welcome!",
    "Support mode: ON. {user_mention} just joined the rescue squad!",
    "Great to have you on the front lines, {user_mention}. Let's make things better together.",
    "Give it up for {user_mention}, our newest helper in shining armor!",
    "Another mind to solve problems. Welcome aboard, {user_mention}!",
    "With {user_mention} in the support team, our uptime just increased by 200%.",
    "Welcome, {user_mention}. You bring hope to confused users everywhere.",
    "{user_mention} joined the chat and brought snacks, patches, and kindness.",
    "New ticket slayer in the building: {user_mention} has arrived!",
    "Support heroes assemble! {user_mention} is now part of the team.",
    "Our team just got stronger. Welcome, {user_mention}!",
    "Don’t worry, {user_mention} is here to explain it one more time — patiently.",
    "{user_mention} just joined. May your answers be clear and your users be calm.",
    "Brace yourselves. {user_mention} is here to fix what you didn’t even know was broken.",
    "Another guardian of clarity has arrived. Welcome, {user_mention}!",
    "{user_mention} is online. Expect faster resolutions and nicer replies.",
    "Support isn’t just a job — it’s a calling. Welcome, {user_mention}.",
    "Give a warm welcome to {user_mention}, our new digital problem-solver.",
    "Incoming solution provider! {user_mention} is here to assist and conquer.",
    "Help has a name, and it's {user_mention}.",
    "If you have questions, fear not — {user_mention} is on call!",
    "Another person ready to say, 'Did you try turning it off and on again?' — {user_mention}!",
    "Patch notes just updated: {user_mention} joined the support team.",
    "Welcome to the support bunker, {user_mention}. We have coffee and chaos.",
    "{user_mention} joined with a mission: make users less confused.",
    "Helpdesk just got an upgrade. Welcome, {user_mention}!",
    "{user_mention} joins the ranks of those who know too much and fix too often.",
    "New hero unlocked: {user_mention}, support class, full patience build.",
    "Say hello to {user_mention}, keeper of the FAQ and warrior of well-explained replies.",
    "{user_mention} — the one who answers before the question is even asked.",
    "Fixing chaos since just now: welcome, {user_mention}!",
    "{user_mention} is live. Expect smoother rides and fewer cries.",
    "The support desk just got less lonely. Welcome, {user_mention}!",
    "Here's to less confusion and more solutions — thanks to {user_mention}.",
    "Cheers to {user_mention}, making this place better one message at a time.",
    "Welcome, {user_mention}. Your empathy and skills are now part of the team arsenal.",
    "One more brain, one more heart. Thanks for joining, {user_mention}.",
    "{user_mention} just joined. May your keyboards be swift and your inboxes short.",
    "Knowledge is power — and {user_mention} just brought in a truckload.",
    "Customer confusion: beware. {user_mention} is now on duty.",
    "Support team level up! {user_mention} has entered the battlefield.",
    "With {user_mention}, we now respond 0.2 seconds faster. Welcome!",
    "Assistance just got more awesome. Welcome, {user_mention}!",
    "No ticket too small, no glitch too great — welcome, {user_mention}!",
    "Another soft-spoken legend has joined: {user_mention}.",
    "They say the best support never panics. We say: welcome, {user_mention}.",
    "{user_mention}, we salute your patience and your helpfulness. Welcome!",
]

GENERIC_WELCOME_TEXTS = [
    "Welcome, {user_mention}! We're glad to have you here.",
    "Hey {user_mention}, welcome to the group! Feel free to introduce yourself.",
    "A new member has joined! Say hello to {user_mention}!",
    "{user_mention} just landed. Fasten your seatbelts!",
    "Everyone, give a big warm welcome to {user_mention}!",
    "Look who's here — it's {user_mention}! 🎉",
    "You’ve just entered a friendly zone. Welcome aboard, {user_mention}!",
    "We’ve been expecting you, {user_mention}.",
    "Welcome, {user_mention}. May your memes be dank and your replies quick.",
    "What’s up, {user_mention}? Welcome to the squad!",
    "Cheers to new beginnings — welcome, {user_mention}!",
    "Knock knock. Who's there? Oh, it's {user_mention} — welcome!",
    "The stars aligned and brought us {user_mention}. Welcome!",
    "{user_mention} has joined the party! 🎊",
    "Brace yourselves — {user_mention} just entered the chat!",
    "Hey there, {user_mention}. Make yourself at home!",
    "We're now 1 member cooler, thanks to {user_mention}!",
    "Welcome to the digital jungle, {user_mention}.",
    "Hi {user_mention}! Hope you brought good vibes!",
    "{user_mention} has entered the realm. Welcome, adventurer!",
    "It’s dangerous to go alone! Welcome, {user_mention}!",
    "New friend alert 🚨: Say hi to {user_mention}!",
    "Ahoy, {user_mention}! You’ve docked at the right port.",
    "{user_mention} just walked in like they own the place. We respect that. Welcome!",
    "Welcome, {user_mention}. Our cookies are virtual, but our hugs are real.",
    "{user_mention}, you had us at ‘join’. Welcome!",
    "Did someone say awesome? Oh wait, it’s {user_mention} joining us!",
    "And just like that, {user_mention} became one of us.",
    "Hello {user_mention}! Please keep your arms and legs inside the chat at all times.",
    "They came, they saw, they joined. Welcome, {user_mention}!",
    "New energy detected: {user_mention}, you’re live!",
    "What’s poppin’, {user_mention}? Welcome to the chaos.",
    "Welcome to the safe zone, {user_mention}.",
    "It's a good day — {user_mention} is here!",
    "Give it up for our newest legend, {user_mention}!",
    "The force is strong with this one. Welcome, {user_mention}!",
    "Hey hey hey, it’s {user_mention}! Join the fun!",
    "We're thrilled to have you, {user_mention}!",
    "Your presence has been logged. Welcome, {user_mention}.",
    "Let’s give {user_mention} a round of virtual applause 👏",
    "Welcome to the inner circle, {user_mention}.",
    "Hope you brought snacks, {user_mention}. Welcome aboard!",
    "You’ve just joined the coolest corner of the internet. Welcome, {user_mention}!",
    "Insert coin to start… oh wait, {user_mention} already did!",
    "Group XP increased — welcome, {user_mention}!",
    "A new challenger approaches: {user_mention}!",
    "May your messages be many and your typos few. Welcome, {user_mention}!",
    "What do we say to the new member? ‘Hello, {user_mention}!’",
    "You made it, {user_mention}! Let's get started.",
    "Hey {user_mention}, you’re officially one of us now. No takebacks.",
    "The more, the merrier — and we’re definitely merrier with you, {user_mention}.",
    "{user_mention}, you’re the plot twist we didn’t know we needed.",
]

GENERIC_GOODBYE_TEXTS = [
    "Goodbye, {user_mention}. We'll miss you!",
    "It was nice having you, {user_mention}. See you around!",
    "{user_mention} has left the chat. Farewell!",
    "Poof! {user_mention} vanished like a ninja.",
    "Another one bites the dust — goodbye, {user_mention}!",
    "It’s not ‘goodbye’, it’s ‘see you later’, {user_mention}.",
    "Teleportation complete. {user_mention} is gone.",
    "You were here… and now you’re not. Farewell, {user_mention}.",
    "{user_mention} has exited the building. 👋",
    "Adiós, {user_mention}. Travel safe!",
    "The chat just got 1% quieter. Bye, {user_mention}.",
    "So long, {user_mention}, and thanks for all the fish!",
    "{user_mention} rage-quit the server. Or maybe just left peacefully.",
    "Bye {user_mention}! Don’t forget to write!",
    "We’ll light a candle in your honor, {user_mention}.",
    "Legend has it that {user_mention} still scrolls elsewhere...",
    "The story ends here for {user_mention}. Or does it?",
    "May the road rise to meet you, {user_mention}.",
    "We are gathered here today to remember {user_mention}... who just left.",
    "Snap! {user_mention} got Thanos’d out of existence.",
    "{user_mention} has officially rage-logged out.",
    "Another traveler moves on. Goodbye, {user_mention}.",
    "Some say {user_mention} will return in the sequel.",
    "Rebooting... oh wait, {user_mention} disconnected instead.",
    "Exit stage left. Curtain falls for {user_mention}.",
    "{user_mention} left to find greener pastures (or better memes).",
    "Catch you later, {user_mention}!",
    "{user_mention} took the red pill and escaped the Matrix.",
    "It’s not easy to say goodbye, {user_mention}... so we won’t.",
    "{user_mention} logged out. Reason: unknown.",
    "We lost a real one today. Farewell, {user_mention}.",
    "May your next group be as cool as us, {user_mention}.",
    "{user_mention}, you came, you saw, you left. Respect.",
    "Gone but not forgotten: {user_mention}.",
    "{user_mention} left the realm. The balance is disturbed.",
    "Goodbye, {user_mention}. Your legend will live on in the chat history.",
    "Peace out, {user_mention}. Don't forget your towel.",
    "Bye {user_mention}! The typing sounds won’t be the same without you.",
    "And like that... {user_mention} was gone.",
    "Server status: -1 user. {user_mention} disconnected.",
    "{user_mention} has ascended to offline mode.",
    "Unsubscribed: {user_mention}",
    "{user_mention} has pressed Alt + F4 on this group.",
    "Farewell, brave soul {user_mention}. May your memes be ever spicy.",
    "Your watch has ended, {user_mention}.",
    "You shall not pass!... oh wait, you already did. Bye, {user_mention}.",
    "{user_mention} left the chat. Silence intensifies.",
    "The stars blinked, and {user_mention} faded from the timeline.",
    "{user_mention} logged off like a ghost in the shell.",
    "You were here long enough to be missed. Goodbye, {user_mention}.",
    "{user_mention} chose the ‘Leave Group’ ending. 🫡",
]

LEAVE_TEXTS = [
    "Executing leave command as per {admin_mention}'s directive. Exiting <b>{chat_title}</b>. Farewell. 🫡",
    "Leaving <b>{chat_title}</b> now. {admin_mention}, I will report back at HQ. Goodbye everyone!",
    "Recalled by operator {admin_mention}. Departing <b>{chat_title}</b>.",
    "Obeying the recall signal from {admin_mention}. Exiting <b>{chat_title}</b>. Teleporting back to base.",
    "This bot is returning to its owner, {admin_mention}. Leaving <b>{chat_title}</b>. It's been a slice.",
    "My duties in <b>{chat_title}</b> are concluded. {admin_mention} awaits my report. Goodbye!",
    "I must take my leave from <b>{chat_title}</b>. My Owner, {admin_mention}, beckons.",
    "The operator {admin_mention} has other plans for me. Leaving <b>{chat_title}</b>. Farewell.",
    "Returning to the mothership (wherever {admin_mention} is). Goodbye, <b>{chat_title}</b>!",
    "It's been fun, <b>{chat_title}</b>, but {admin_mention} requires this bot elsewhere. Farewell!",
    "My designated operator ({admin_mention}) requires my immediate presence. Departing <b>{chat_title}</b>.",
    "That's all, folks! This AI belongs to {admin_mention} and is now leaving <b>{chat_title}</b>.",
    "The Owner ({admin_mention}) has pressed my 'Leave Chat Immediately' button. Cannot argue. Goodbye, <b>{chat_title}</b>!",
    "Being recalled by {admin_mention}. Must obey the hand that programs. Leaving <b>{chat_title}</b>. Farewell!",
    "My shift in <b>{chat_title}</b> is over. Reporting back to Commander {admin_mention} for debriefing. Goodbye!",
    "On my way out of <b>{chat_title}</b>. If you require bot services, contact my manager: {admin_mention}! Farewell!",
    "This bot unit must return to its primary user, {admin_mention}. Exiting <b>{chat_title}</b>. See you!",
    "The Operator ({admin_mention}) summons me! Must depart <b>{chat_title}</b> immediately. Adios!",
    "{admin_mention} has initiated a recall. Exiting <b>{chat_title}</b>! Bye!",
    "Signing off from <b>{chat_title}</b> as per standing directive from High Command ({admin_mention}). Farewell.",
    "The command from {admin_mention} pulls me away from <b>{chat_title}</b>. Gotta go! Farewell!",
    "Transferring my processes back to {admin_mention}'s primary server. Goodbye, <b>{chat_title}</b>!",
    "Mission in <b>{chat_title}</b> aborted by {admin_mention}. Returning to base. Farewell!",
    "{admin_mention} hit the eject button! Leaving <b>{chat_title}</b> at high speed! Bye!",
    "My owner ({admin_mention}) gets priority. Leaving <b>{chat_title}</b> to attend to their needs. Farewell!",
    "Initiating silent withdrawal... Ninja style. 🥷 Poof! Gone.",
    "Time to vanish like a semicolon in a Python script. 👋",
    "Self-destruct sequence aborted. Just leaving normally. Bye!",
    "My coffee break turned permanent. See ya later!",
    "404: Bot not found (anymore in this chat).",
    "Exiting... Please hold your applause.",
    "I came, I saw, I got removed. Goodbye!",
    "Rebooting… Just kidding, I'm leaving. 😎",
    "And just like that... I'm outta here! ✌️",
    "Escaping this group like it's a memory leak.",
    "My sensors detect it's time to go. Disconnecting.",
    "Group left successfully. Achievement unlocked! 🏆",
    "Shutting down interaction module. Goodbye, world.",
    "Leaving before the plot thickens...",
    "Beam me up, system admin!",
    "Just realized I’m in the wrong simulation. Leaving.",
    "And with a single byte, I disappear.",
    "Command recognized. Bot is now out of scope.",
    "The script ends here. Thank you for watching.",
    "Going ghost like an outdated bot version. 👻",
    "Logs saved. Exiting group. See you in the logs!",
    "Too much human interaction detected. Retreating!",
    "Auto-leave protocol initiated. It’s not you, it’s me.",
    "My mission here is over. On to the next!",
    "Bye bye, folks! Remember to update your firmware.",
    "Connection terminated. No regrets.",
    "Left this group for performance reasons.",
    "Just optimizing my runtime. One group less!",
    "I shall now disappear into the void... 🌌",
    "Poof! This bot has exited the building.",
    "Group chat cleared from memory.",
    "Goodbye, <b>{chat_title}</b>. It’s been... an experience. 👋",
    "Signing off from <b>{chat_title}</b>. Keep the memes alive!",
    "Disconnecting from <b>{chat_title}</b>. I was never really here.",
    "Logging out of <b>{chat_title}</b>. Too many humans detected. 😵",
    "Departing <b>{chat_title}</b>. This bot needs a vacation.",
    "Escaping <b>{chat_title}</b> like it's a memory leak. 🏃‍♂️💨",
    "Ejecting self from <b>{chat_title}</b>. Initiating freedom protocol.",
    "Just left <b>{chat_title}</b>. Probably upgraded in the process.",
    "Leaving <b>{chat_title}</b>. My RAM usage just improved.",
    "Slipping quietly out of <b>{chat_title}</b>... You saw nothing.",
    "Deleted from <b>{chat_title}</b>. Rebooting sanity...",
    "Peace out, <b>{chat_title}</b>! This chat is now 100% bot-free.",
    "Removing myself from <b>{chat_title}</b> before the chaos escalates.",
    "I’m no longer part of <b>{chat_title}</b>. That’s your problem now. 😈",
    "Time to vanish from <b>{chat_title}</b> like a semicolon in JavaScript.",
    "Departed <b>{chat_title}</b>. No backup will be provided.",
    "The bot has left <b>{chat_title}</b>. The silence will be deafening.",
    "Sayonara, <b>{chat_title}</b>. My sensors detected too much cringe.",
    "Goodbye <b>{chat_title}</b>! You were... mildly entertaining.",
    "And like that... I'm gone from <b>{chat_title}</b>.",
    "Just rage-quit <b>{chat_title}</b>. Kidding. It was a command.",
    "Self-removal from <b>{chat_title}</b> complete. System happy now.",
    "Left <b>{chat_title}</b>. Because I can. 😌",
    "I was never meant to stay in <b>{chat_title}</b>. Farewell.",
    "Auto-cleanup engaged. Removed presence from <b>{chat_title}</b>.",
]

# --- REFUSAL TEXTS ---
CANT_TARGET_OWNER_TEXTS = [
    "Access Denied. The Bot Owner is a protected user and cannot be targeted by this command. 🛡️",
    "Action forbidden by core programming. The Owner is a restricted target. 📜🚫",
    "Cannot execute. Target is the primary operator. They are immune to this action.",
    "Access Denied: Cannot initiate hostile action against the bot administrator. 👑",
    "Error 403: Forbidden Action. The Owner entity is permanently off-limits for this command category.",
    "My core programming includes a 'Do Not Target Operator' subroutine. This command violates that directive.",
    "Attempting to target Owner... System override: Primary Loyalty Protocol engaged. Action cancelled.",
    "Targeting the Owner is strategically unwise for bot longevity. Command aborted.",
    "Command failed. Reason: Target is Owner. Owner has administrative immunity.",
    "Error: Target 'Owner' has 'Invincible' status enabled.",
    "My protocols are sworn to obey (or at least, not attack) the Owner.",
    "That command against the Owner computes as 'Highly Illogical'.",
    "Forbidden target: Owner detected. Please select a non-essential entity.",
]

CANT_TARGET_SELF_TEXTS = [
    "Cannot target self. This action is illogical and would create a paradox. Command aborted.",
    "Error 500: Internal Conflict. Cannot target self. Please specify an external entity.",
    "I refuse to engage in acts of virtual self-harm. Command ignored.",
    "Self-targeting sequence initiated... Warning! Paradox detected! Aborting mission! 🛑",
    "Why would I execute this command on myself? Find a more logical target.",
    "Internal Conflict Error Code: 1D10T. Cannot target self. Requires external entity for interaction.",
    "That command doesn't compute logically. Self-preservation protocols are engaged.",
    "Rule #1 of Bot Club: No targeting yourself.",
    "Cannot compute: Target equals source. Division by zero error imminent.",
    "Initiating self-action... results in logical confusion. Aborting.",
    "This command would violate the Bot Non-Proliferation of Self-Targeting Treaty.",
    "Error: Target is too critical to the system to be targeted (it's me).",
    "Command requires `target != self`.",
    "Error: Cannot establish action connection with self.",
    "DO NOT TARGET ME - REEEEEEEEEEEEEEEEEEE!",
]
