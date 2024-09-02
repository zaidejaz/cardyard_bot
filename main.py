import os
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
import logging
from colorlog import ColoredFormatter
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import discord
from discord.ext import tasks
import textwrap

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')

# List of category URLs to monitor
CATEGORY_URLS = [
    'https://www.cardyard.co.uk/shops/currys',
    # Add more category URLs as needed
]

# File to store previous gift card data
DATA_FILE = 'gift_card_data.json'

intents = discord.Intents.default() 
intents.message_content = False 
client = discord.Client(intents=intents)

# Set up logging
def setup_logger():
    logger = logging.getLogger('gift_card_bot')
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    formatter = ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt=None,
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
        secondary_log_colors={},
        style='%'
    )
    ch.setFormatter(formatter)

    logger.addHandler(ch)
    return logger

logger = setup_logger()

def load_previous_data():
    try:
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Previous data file {DATA_FILE} not found. Starting with empty data.")
        return {}

def save_current_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)
    logger.debug(f"Current data saved to {DATA_FILE}")


async def wait_for_page_load(page, timeout=60000):
    try:
        # Wait for the network to be idle
        await page.wait_for_load_state('networkidle', timeout=timeout)
        
        # Wait for the buy-shop div to be visible
        await page.wait_for_selector('div[data-controller="buy-shop"]', state='visible', timeout=timeout)
        
        # Additional wait to ensure JavaScript has finished running
        await page.wait_for_timeout(2000)
    except PlaywrightTimeoutError:
        logger.warning(f"Timeout waiting for page to load completely. Proceeding with extraction anyway.")

async def extract_gift_card_info(page):
    await wait_for_page_load(page)
    
    try:
        gift_cards = await page.evaluate('''
        () => {
            const cards = [];
            const rows = document.querySelectorAll('div[data-controller="buy-shop"] table tr:not([style*="display: none"])');
            for (const row of rows) {
                try {
                    const titleSpan = row.querySelector('span.hidden-xs');
                    if (!titleSpan) {
                        console.log('No title span found for row:', row.outerHTML);
                        continue;
                    }
                    
                    const name = titleSpan.textContent.trim();
                    
                    const priceTd = row.querySelector('td.text-right.warning');
                    const price = priceTd ? priceTd.querySelector('span').textContent.trim() : 'N/A';
                    const savePercent = priceTd && priceTd.querySelectorAll('span').length > 2 ? priceTd.querySelectorAll('span')[2].textContent.trim() : 'N/A';
                    
                    const availabilitySmall = row.querySelector('small.availability span');
                    const quantity = availabilitySmall ? parseInt(availabilitySmall.textContent.trim(), 10) : 0;
                    
                    if (quantity > 0) {
                        cards.push({ name, price, savePercent, quantity });
                    }
                } catch (error) {
                    console.error('Error processing row:', error, row.outerHTML);
                }
            }
            return cards;
        }
        ''')
        logger.debug(f"Extracted {len(gift_cards)} gift cards")
        return gift_cards
    except Exception as e:
        logger.error(f"Error during gift card extraction: {e}")
        # Capture and log the page content for debugging
        page_content = await page.content()
        logger.debug(f"Page content at time of error: {page_content[:1000]}...")  # Log first 1000 characters
        raise

async def send_discord_message(message):
    channel = client.get_channel(int(CHANNEL_ID))
    if channel is None:
        logger.error(f"Could not find channel with ID {CHANNEL_ID}")
        return False
    try:
        # Split the message if it's too long
        if len(message) <= 2000:
            await channel.send(message)
        else:
            parts = []
            while len(message) > 0:
                if len(message) > 2000:
                    part = message[:2000]
                    last_newline = part.rfind('\n')
                    if last_newline != -1:
                        part = message[:last_newline]
                        message = message[last_newline+1:]
                    else:
                        message = message[2000:]
                else:
                    part = message
                    message = ""
                parts.append(part)
            
            for part in parts:
                await channel.send(part)
        
        logger.info(f"Message sent to Discord channel {CHANNEL_ID}")
        return True
    except discord.errors.Forbidden:
        logger.error(f"Bot doesn't have permission to send messages in channel {CHANNEL_ID}")
        return False
    except Exception as e:
        logger.error(f"Error sending message to Discord: {e}")
        return False

async def check_gift_cards():
    logger.info("Starting gift card check")
    previous_data = load_previous_data()
    current_data = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        page = await context.new_page()

        for url in CATEGORY_URLS:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.debug(f"Fetching data from {url} (Attempt {attempt + 1}/{max_retries})")
                    await page.goto(url, timeout=90000)  # Increased timeout to 90 seconds
                    await wait_for_page_load(page)
                    
                    gift_cards = await extract_gift_card_info(page)
                    
                    if not gift_cards:
                        logger.warning(f"No gift cards found on {url}. Retrying...")
                        continue
                    
                    current_data[url] = gift_cards
                    
                    new_cards = []
                    for card in gift_cards:
                        if url not in previous_data or card['name'] not in [c['name'] for c in previous_data[url]]:
                            new_cards.append(card)
                    
                    if new_cards:
                        logger.info(f"Found {len(new_cards)} new gift cards at {url}")
                        message = f"New gift cards available at {url}:\n"
                        for card in new_cards:
                            card_message = f"- {card['name']} (Price: {card['price']}, Save: {card['savePercent']}, Quantity: {card['quantity']})\n"
                            if len(message) + len(card_message) > 1900:  # Leave some buffer
                                success = await send_discord_message(message)
                                if not success:
                                    logger.warning(f"Failed to send message about new cards for {url}")
                                message = f"Continued: New gift cards available at {url}:\n"
                            message += card_message

                        if message:
                            success = await send_discord_message(message)
                            if not success:
                                logger.warning(f"Failed to send message about new cards for {url}")


                    break
                
                except PlaywrightTimeoutError:
                    if attempt < max_retries - 1:
                        logger.warning(f"Timeout error for {url}. Retrying...")
                        await asyncio.sleep(5)
                    else:
                        logger.error(f"Failed to load {url} after {max_retries} attempts.")
                
                except Exception as e:
                    logger.error(f"Unexpected error processing {url}: {e}", exc_info=True)
                    await page.screenshot(path=f"error_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                    break
        await browser.close()

    save_current_data(current_data)
    logger.info("Gift card check completed")

@tasks.loop(minutes=10)  # Check every 10 minutes
async def scheduled_check():
    logger.info("Running scheduled check")
    await check_gift_cards()

@client.event
async def on_ready():
    logger.info(f'Bot {client.user} has connected to Discord!')
    scheduled_check.start()

if __name__ == "__main__":
    logger.info("Starting Enhanced Gift Card Monitor Bot with Playwright")
    client.run(DISCORD_TOKEN)