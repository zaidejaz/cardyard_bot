# Gift Card Monitor Bot

This Discord bot monitors specified gift card websites for new or updated gift card listings and sends notifications to a designated Discord channel.

## Prerequisites

- Python 3.7 or higher
- A Discord account and a server where you have permission to add bots
- Basic familiarity with command line operations

## Setup Instructions

### 1. Open the terminal or command propmpt inside the folder. 
Check your python version 

```bash
python --version
```

If python doesnot work for mac try python3 and same if the pip doesnot work try pip3. 

### 2. Set Up a Virtual Environment (Optional but Recommended)

It's a good practice to use a virtual environment. Here's how to set it up:

```bash
pip install poetry
```

Install all dependencies

```bash
poetry install
```

Activate the environment

```bash
poetry shell
```

### 3. Install Dependencies

Install the required Python packages:

```bash
poetry add playwright python-dotenv colorlog discord.py
```

After installation, set up Playwright:

```bash
playwright install chromium
```

### 4. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click "New Application" and give it a name.
3. Go to the "Bot" tab and click "Add Bot".
4. Under the "Token" section, click "Copy" to copy your bot token. Keep this secret!

### 5. Invite the Bot to Your Server

1. In the Discord Developer Portal, go to the "OAuth2" tab.
2. In the "Scopes" section, check "bot".
3. In the "Bot Permissions" section, check "Send Messages" and any other permissions you want to give the bot.
4. Copy the generated URL and open it in a web browser to invite the bot to your server.

### 6. Configure the Bot

1. In the project directory, create a file named `.env`.
2. Add the following lines to the `.env` file:

   ```
   DISCORD_TOKEN=your_bot_token_here
   CHANNEL_ID=your_channel_id_here
   ```

   Replace `your_bot_token_here` with the bot token you copied earlier.

3. To get the `CHANNEL_ID`:
   - In Discord, go to User Settings > Advanced and enable Developer Mode.
   - Right-click on the channel where you want the bot to send messages and click "Copy ID".
   - Replace `your_channel_id_here` with this ID.

### 7. Customize Gift Card URLs

Open the Python script and locate the `CATEGORY_URLS` list. Add or modify the URLs of the gift card pages you want to monitor.

## Running the Bot

1. Make sure you're in the project directory and your virtual environment is activated (if you're using one).

2. Run the bot:

   ```bash
   python main.py
   ```

3. You should see console output indicating that the bot has connected to Discord.

4. The bot will check for new gift cards every 10 minutes by default. You can adjust this interval in the script if needed.

## Troubleshooting

- If you encounter any "Module not found" errors, make sure you've installed all the required packages.
- If the bot can't connect to Discord, double-check your `DISCORD_TOKEN` in the `.env` file.
- If the bot connects but doesn't send messages, verify that the `CHANNEL_ID` is correct and the bot has permission to send messages in that channel.
- For any other issues, check the console output for error messages. Most errors will be logged with detailed information.

## Customization

You can modify the script to change:
- The check interval (currently set to 10 minutes)
- The format of the Discord messages
- The gift card websites being monitored
