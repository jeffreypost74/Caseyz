import discord
from discord.ext import commands
from discord import app_commands
import random
import requests
import json
import os
import asyncio
import time
from dotenv import load_dotenv

# --- Configuration Constants ---
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")

# File Paths
USER_DATA_FILE = "userdata.json"

# Cache Configuration
# Skinport Cache
SKINPORT_CACHE_FILE = 'skinport_cache.json'
SKINPORT_CACHE_DURATION = 600 # Skinport price cache duration (seconds)

# CS.FLOAT Cache
CSFLOAT_CACHE_FILE = 'csfloat_cache.json'
CSFLOAT_CACHE_DURATION = 72000 # CS.FLOAT price cache duration (seconds)

# LootFarm Cache
LOOTFARM_CACHE_FILE = 'lootfarm_cache.json'
LOOTFARM_CACHE_DURATION = 600 # LootFarm price cache duration (seconds)

# NEW: Steam Community Market (SCM) Cache
SCM_CACHE_FILE = 'scm_cache.json'
SCM_CACHE_DURATION = 1800 # SCM price cache duration (30 minutes)

# NEW: Skins API Cache
SKINS_API_CACHE_FILE = 'skins_api_cache.json'
SKINS_API_CACHE_DURATION = 250000 # Cache duration for skins.json (72 hours)

# ByMykel CSGO-API configuration
BY_MYKEL_API_URL = "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/skins_not_grouped.json"
BY_MYKEL_API_URL2 = "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/skins.json"
BY_MYKEL_LOCAL_CACHE_FILE = 'by_mykel_skins_data.json'
BY_MYKEL_CACHE_DURATION = 86400 * 7 # Cache ByMykel data for 7 days (seconds)

# Global variables to store data
BY_MYKEL_SKIN_DATA = {}
SKINPORT_PRICES_CACHE = None
LOOTFARM_PRICES_CACHE = None
SCM_PRICES_CACHE = {} # SCM will use a dict for individual item caching
MERGED_CSGO_PRICES_DATA = {} # Global dict for merged_csgo_prices.json content

# Market name overrides for specific skins
MARKET_NAME_OVERRIDES = {
    "M4A4 | Dragon King": "M4A4 | 龍王 (Dragon King)"
}

# Rarity Chances (ensure these sum to 100 or adjust as needed)
RARITY_CHANCES = {
    "Mil-Spec": 80,
    "Restricted": 15.98,
    "Classified": 3.2,
    "Covert": 0.64,
    "Knife": 0.26
}

STATTRAK_CHANCE = 0.10 # 10% chance for a skin to be StatTrak if available

RARITY_COLORS = {
    "Mil-Spec": 0x3b8eea,
    "Restricted": 0x5e3dac,
    "Classified": 0xbd42f4,
    "Covert": 0xff4b00,
    "Knife": 0xffd700
}

# --- Case Skin Definitions (remains the same) ---
CHROMA_CASE_SKINS = {
    "Mil-Spec": {
        "MP9 | Deadly Poison": {"wears": ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"], "stattrak_available": True},
        "SCAR-20 | Grotto": {"wears": ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"], "stattrak_available": True},
        "XM1014 | Quicksilver": {"wears": ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"], "stattrak_available": True},
        "M249 | System Lock": {"wears": ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"], "stattrak_available": True},
        "Glock-18 | Catacombs": {"wears": ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"], "stattrak_available": True}
    },
    "Restricted": {
        "MAC-10 | Malachite": {"wears": ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"], "stattrak_available": True},
        "Sawed-Off | Serenity": {"wears": ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"], "stattrak_available": True},
        "Dual Berettas | Urban Shock": {"wears": ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"], "stattrak_available": True},
        "Desert Eagle | Naga": {"wears": ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"], "stattrak_available": True}
    },
    "Classified": {
        "M4A4 | Dragon King": {"wears": ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"], "stattrak_available": True},
        "P250 | Muertos": {"wears": ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"], "stattrak_available": True},
        "AK-47 | Cartel": {"wears": ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"], "stattrak_available": True}
    },
    "Covert": {
        "AWP | Man-o'-war": {"wears": ["Minimal Wear", "Field-Tested"], "stattrak_available": True},
        "Galil AR | Chatterbox": {"wears": ["Field-Tested", "Well-Worn", "Battle-Scarred"], "stattrak_available": True}
    }
}

CHROMA_KNIVES = {
    # Doppler
    "★ Bayonet | Doppler": ["Factory New"],
    "★ Flip Knife | Doppler": ["Factory New"],
    "★ Gut Knife | Doppler": ["Factory New"],
    "★ Karambit | Doppler": ["Factory New"],
    "★ M9 Bayonet | Doppler": ["Factory New"],
}

# Doppler phases and gems
doppler_phases = ["Phase 1", "Phase 2", "Phase 3", "Phase 4"]
doppler_gems = ["Ruby", "Sapphire", "Black Pearl"]


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="cs!", intents=intents)

# --- User Data Management ---
def load_user_data():
    if not os.path.exists(USER_DATA_FILE):
        return {}
    try:
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Error decoding {USER_DATA_FILE}. Returning empty data.")
        return {}

def save_user_data(data):
    try:
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving {USER_DATA_FILE}: {e}")

# --- Discord UI Views (Modified) ---
class SkinActionView(discord.ui.View):
    def __init__(self, user_id, display_name, price, bot_instance, skin_variant=None): # ADD skin_variant
        super().__init__(timeout=30)
        self.user_id = user_id
        self.display_name = display_name
        self.price = price
        self.bot = bot_instance
        self.skin_variant = skin_variant # Store the variant

    @discord.ui.button(label="💰 Sell", style=discord.ButtonStyle.green)
    async def sell_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ This isn't your skin to sell!", ephemeral=True)
            return

        data = load_user_data()
        user_id_str = str(self.user_id)
        data.setdefault(user_id_str, {"balance": 0, "inventory": {}})
        data[user_id_str]["balance"] += self.price
        save_user_data(data)
        new_balance = data[user_id_str]["balance"]

        for child in self.children:
            child.disabled = True
        embed = discord.Embed(
            title="Item Sold!",
            description=f"✅ Sold **{self.display_name}** for ${self.price:.2f}!",
            color=0x00FF00
        )
        embed.set_footer(text=f"Your new balance is ${new_balance:.2f}")

        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=None
        )

        new_view = discord.ui.View()
        new_view.add_item(OpenAnotherButton(self.user_id, self.bot))
        await interaction.followup.send("Want to open another case?", view=new_view, ephemeral=True)

    @discord.ui.button(label="🎒 Keep", style=discord.ButtonStyle.blurple)
    async def keep_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ This isn't your skin to keep!", ephemeral=True)
            return

        data = load_user_data()
        user_id_str = str(self.user_id)
        data.setdefault(user_id_str, {"balance": 0, "inventory": {}})
        inventory = data[user_id_str]["inventory"]

        # MODIFIED: Store skin as a dictionary including count and variant
        # Handle existing entries that might be in the old "count" format
        if self.display_name not in inventory:
            inventory[self.display_name] = {"count": 0, "variant": None} # Initialize if new
        elif not isinstance(inventory[self.display_name], dict):
            # Convert old format to new format if it's just a count
            inventory[self.display_name] = {"count": inventory[self.display_name], "variant": None}

        inventory[self.display_name]["count"] += 1
        # Only update variant if it's not None, otherwise keep existing None or previous variant
        if self.skin_variant is not None:
            inventory[self.display_name]["variant"] = self.skin_variant

        save_user_data(data)

        quantity = inventory[self.display_name]["count"] # Get count from the dictionary

        embed = discord.Embed(
                title="Item Kept!",
                description=f"🎒 Kept **{self.display_name}**.",
                color=0x3498db
            )
        embed.add_field(name="Quantity in inventory", value=str(quantity), inline=False)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=None
        )

        new_view = discord.ui.View()
        new_view.add_item(OpenAnotherButton(self.user_id, self.bot))
        await interaction.followup.send("Want to open another case?", view=new_view, ephemeral=True)

class InventoryView(discord.ui.View):
    def __init__(self, ctx, inventory, per_page=5):
        super().__init__()
        self.ctx = ctx
        # Ensure inventory items are in the new {count: X, variant: Y} format for consistency
        self.inventory = {k: v if isinstance(v, dict) else {"count": v, "variant": None} for k, v in inventory.items()}
        self.per_page = per_page
        self.current_page = 0
        
        # Calculate total pages based on unique items
        self.total_pages = (len(self.inventory) - 1) // per_page + 1
        if len(self.inventory) == 0: # Handle empty inventory case for pages
            self.total_pages = 1 

        self.prices = {}
        self.total_worth = 0.0
        for name, item_data in self.inventory.items(): # Iterate over item_data
            count = item_data.get("count", 0)
            # Use the existing get_price, which now has the cache_only_sources logic
            price, _, _ = get_price(name, allowed_sources=["Skinport", "LootFarm"])
            price = price or 0.0
            self.prices[name] = price
            self.total_worth += price * count

    def get_embed(self):
        embed = discord.Embed(
            title=f"🎒 {self.ctx.author.display_name}'s Inventory",
            color=0x3498db
        )
        start = self.current_page * self.per_page
        end = start + self.per_page

        # Get page items as (name, item_data_dict)
        page_items = list(self.inventory.items())[start:end]

        for name, item_data in page_items: # Iterate over item_data
            count = item_data.get("count", 0)
            variant = item_data.get("variant") # Get the variant
            price_val = round(self.prices.get(name, 0), 2)
            
            value_string = f"Quantity: {count}\n"
            if variant: # Add variant if it exists
                value_string += f"Variant: {variant}\n"
            
            if price_val > 0:
                value_string += f"Price per skin: ${price_val}"
            else:
                value_string += f"Price per skin: Not found"
            
            embed.add_field(name=name, value=value_string, inline=False)

        embed.set_footer(text=f"Page {self.current_page + 1} of {self.total_pages} | Total worth: ${self.total_worth:.2f}")
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("⛔ This is not your inventory!", ephemeral=True)
            return

        self.current_page = (self.current_page - 1) % self.total_pages
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("⛔ This is not your inventory!", ephemeral=True)
            return

        self.current_page = (self.current_page + 1) % self.total_pages
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

class OpenAnotherButton(discord.ui.Button):
    def __init__(self, user_id, bot_instance):
        super().__init__(label="🎁 Open another", style=discord.ButtonStyle.primary)
        self.user_id = user_id
        self.bot = bot_instance

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ This isn't your button!", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            await interaction.message.delete()
        except discord.NotFound:
            pass
        except discord.Forbidden:
            pass
        except Exception as e:
            print(f"Error deleting ephemeral message: {e}")

        # The generate_random_skin function would need to return the Doppler variant
        # to display it separately. Let's adjust generate_random_skin to return
        # variant_info in addition to display_name, market_name, rarity.
        display_name, market_name, rarity, variant_info, skin_image_url = generate_random_skin() 
        price, image_url, price_source = get_price(market_name) # Unpack the source here
        price_val = round(price, 2) if price else 0.0

        embed = discord.Embed(
            title="🎉 You unboxed:",
            description=f"**{display_name}**",
            color=RARITY_COLORS.get(rarity, 0x808080)
        )
        # Add Doppler variant info if available
        if variant_info:
            embed.add_field(name="Variant", value=variant_info, inline=False)
            
        if price:
            embed.add_field(name="💵 Price", value=f"${price_val}")
            if price_source: # Add footer if a price source was found
                embed.set_footer(text=f"Price fetched from {price_source}")
        else:
            embed.add_field(name="❌ Price not found", value="This item's price was not found.")
            embed.set_footer(text="Price not available from any platform.") # Generic footer for no price

        if skin_image_url:
            embed.set_image(url=skin_image_url)
        else:
            embed.set_image(url=image_url)

        view = SkinActionView(self.user_id, display_name, price_val, self.bot, skin_variant=variant_info) # PASS skin_variant
        await interaction.followup.send(embed=embed, view=view)

@bot.event
async def on_ready():
    print(f'✅ Bot connected as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} slash commands.')
    except Exception as e:
        print(f'❌ Sync error: {e}')
    
    global BY_MYKEL_SKIN_DATA, MERGED_CSGO_PRICES_DATA, SCM_PRICES_CACHE
    
    BY_MYKEL_SKIN_DATA = download_and_cache_by_mykel_data()
    if not BY_MYKEL_SKIN_DATA:
        print("⚠️ Failed to load ByMykel skin data. Image links might be missing.")

    # Load initial merged prices data
    MERGED_CSGO_PRICES_DATA = load_merged_prices_data()

    # Load SCM cache on startup
    SCM_PRICES_CACHE = load_scm_cached_data()

    # Pre-populate caches for immediate use (optional, can be done on first call)
    # global SKINPORT_PRICES_CACHE, LOOTFARM_PRICES_CACHE
    # SKINPORT_PRICES_CACHE = update_skinport_cache()
    # LOOTFARM_PRICES_CACHE = update_lootfarm_cache()

    # Start the periodic merged prices saving task
    bot.loop.create_task(save_merged_prices_periodically())
    # Start the periodic SCM cache saving task
    bot.loop.create_task(save_scm_cache_periodically())


# --- Rarity and Skin Generation Logic (remains the same) ---
def roll_rarity():
    roll = random.uniform(0, 100)
    cumulative = 0
    for rarity, chance in RARITY_CHANCES.items():
        cumulative += chance
        if roll <= cumulative:
            return rarity
    return "Mil-Spec"

# MODIFIED: generate_random_skin to return variant_info
def generate_random_skin():
    rarity = roll_rarity()
    is_stattrak = False
    variant_info = None # Initialize variant_info
    skin_image_url = None

    if rarity == "Knife":
        base_skin_name = random.choice(list(CHROMA_KNIVES.keys())) # e.g., "★ Bayonet | Doppler"
        wear = random.choice(CHROMA_KNIVES[base_skin_name])
        is_stattrak = random.random() < STATTRAK_CHANCE

        # Handle Doppler variants first
        if "Doppler" in base_skin_name:
            is_stattrak = False
            chosen_type = random.choices(["phase", "gem"], weights=[0.80, 0.20], k=1)[0]
            if chosen_type == "phase":
                selected_variant = random.choice(doppler_phases)
            else: # chosen_type == "gem"
                selected_variant = random.choice(doppler_gems)
            
            variant_info = selected_variant # Store the variant info

            # Construct names for Doppler
            # For display, remove the initial '★ ' then add it back with StatTrak™ if needed
            base_name_without_star = base_skin_name[2:] # Remove "★ "
            
            skin_name_for_json_match = f"{base_skin_name}"
            skins_data = load_skins_data()
            if skins_data:
                for skin_entry in skins_data:
                    # Match by the full name including variant and wear
                    if (skin_entry.get("name") == skin_name_for_json_match and
                        skin_entry.get("phase") == selected_variant):
                            # Assuming variant_info in JSON has 'phase' or 'gem'
                            skin_image_url = skin_entry.get("image")
                            break # Found the match, exit loop

            display_name = f"{base_name_without_star} {selected_variant} ({wear})"
            market_name_base = MARKET_NAME_OVERRIDES.get(base_skin_name, base_skin_name)
            market_name = f"{market_name_base} {selected_variant} ({wear})"
            
            if is_stattrak:
                display_name = f"★ StatTrak™ {display_name}" # Apply the new format here
                market_name = f"{display_name}" # Market name usually has StatTrak™ at the very front
            else:
                display_name = f"{base_skin_name} ({wear})" # Original star format if not StatTrak
        else:
            # For non-Doppler knives
            display_name = f"{base_skin_name} ({wear})"
            market_name = MARKET_NAME_OVERRIDES.get(base_skin_name, base_skin_name) + f" ({wear})"

            if is_stattrak:
                # For non-doppler knives, the star is already part of base_skin_name
                # We need to insert StatTrak™ after the star
                display_name_parts = display_name.split(" ", 1) # Split after the first space to separate "★"
                display_name = f"{display_name_parts[0]} StatTrak™ {display_name_parts[1]}"
                market_name = f"{display_name_parts[0]} StatTrak™ {display_name_parts[1]}" # Market name format
    else: # This is for non-knife skins
        skin_data = random.choice(list(CHROMA_CASE_SKINS[rarity].items()))
        skin_name = skin_data[0] 
        skin_info = skin_data[1]

        wear = random.choice(skin_info["wears"])
        if skin_info["stattrak_available"]:
            is_stattrak = random.random() < STATTRAK_CHANCE
        
        display_name = f"{skin_name} ({wear})"
        market_skin = MARKET_NAME_OVERRIDES.get(skin_name, skin_name)
        market_name = f"{market_skin} ({wear})"

        if is_stattrak:
            display_name = f"StatTrak™ {display_name}"
            market_name = f"StatTrak™ {market_name}"

    return display_name, market_name, rarity, variant_info, skin_image_url # Return variant_info


# --- Price API Cache Functions ---
def load_skins_data():
    """
    Loads skins data from cache or fetches it from the ByMykel CSGO-API.
    """
    if os.path.exists(SKINS_API_CACHE_FILE):
        with open(SKINS_API_CACHE_FILE, 'r') as f:
            cache_data = json.load(f)
        if time.time() - cache_data['timestamp'] < SKINS_API_CACHE_DURATION:
            # print("Loading skins data from cache.") # For debugging
            return cache_data['data']

    # print("Fetching skins data from API.") # For debugging
    try:
        skins_api_url = BY_MYKEL_API_URL2
        response = requests.get(skins_api_url)
        response.raise_for_status() # Raise an exception for HTTP errors
        skins_data = response.json()

        with open(SKINS_API_CACHE_FILE, 'w') as f:
            json.dump({'timestamp': time.time(), 'data': skins_data}, f)
        return skins_data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching skins data: {e}")
        return None

# Skinport
def load_skinport_cached_data(ignore_expiry=False):
    if not os.path.exists(SKINPORT_CACHE_FILE):
        return None
    try:
        with open(SKINPORT_CACHE_FILE, 'r') as f:
            cached = json.load(f)
        # If ignore_expiry is False, we check for expiration normally
        if not ignore_expiry and time.time() - cached["timestamp"] > SKINPORT_CACHE_DURATION:
            print("⏳ Skinport cache expired.")
            return None
        # If ignore_expiry is True and cache is expired, log that it's being used as fallback
        if ignore_expiry and time.time() - cached["timestamp"] > SKINPORT_CACHE_DURATION:
            print("⚠️ Using expired Skinport cache due to API error.")
        print("✅ Loaded Skinport data from cache.")
        return cached["items"]
    except Exception as e:
        print(f"❌ Error loading Skinport cache: {e}.")
        return None

def update_skinport_cache():
    print("🔄 Fetching fresh data from Skinport API...")
    url = 'https://api.skinport.com/v1/items?app_id=730&currency=USD'
    headers = {
        'Accept': "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            with open(SKINPORT_CACHE_FILE, 'w') as f:
                json.dump({"timestamp": time.time(), "items": data}, f)
            print("✅ Skinport cache updated.")
            return data
        else: # Handles any non-200 status code (e.g., 406, 503, 404, etc.)
            print(f"⚠️ Skinport API returned {response.status_code}. Attempting to use existing cache (even if expired).")
            # Call load_skinport_cached_data with ignore_expiry=True for fallback
            cached_data = load_skinport_cached_data(ignore_expiry=True)
            if cached_data:
                print("✅ Successfully loaded Skinport data from existing cache due to API error.")
                return cached_data
            else:
                print("❌ Existing Skinport cache not found or invalid. Cannot use cache for API error.")
                return None
    except Exception as e: # Handles network errors, timeouts, JSON decoding errors, etc.
        print(f"❌ Error fetching Skinport data: {e}. Attempting to use existing cache (even if expired).")
        # Call load_skinport_cached_data with ignore_expiry=True for fallback
        cached_data = load_skinport_cached_data(ignore_expiry=True)
        if cached_data:
            print("✅ Successfully loaded Skinport data from existing cache due to fetch error.")
            return cached_data
        else:
            print("❌ Existing Skinport cache not found or invalid. Cannot use cache for fetch error.")
            return None

# LootFarm
def load_lootfarm_cached_data():
    if not os.path.exists(LOOTFARM_CACHE_FILE):
        return None
    try:
        with open(LOOTFARM_CACHE_FILE, 'r') as f:
            cached = json.load(f)
        if time.time() - cached["timestamp"] > LOOTFARM_CACHE_DURATION:
            print("⏳ LootFarm cache expired.")
            return None
        print("✅ Loaded LootFarm data from cache.")
        return cached["items"]
    except Exception as e:
        print(f"❌ Error loading LootFarm cache: {e}. Re-fetching.")
        return None

def update_lootfarm_cache():
    print("🔄 Fetching fresh data from LootFarm API...")
    try:
        resp = requests.get("https://loot.farm/fullprice.json", timeout=10)
        resp.raise_for_status()
        items = resp.json()
        
        if not isinstance(items, list):
            print("LootFarm API returned unexpected data type (not a list).")
            return {}
        
        processed_items = {}
        for item in items:
            if isinstance(item, dict) and 'name' in item and 'price' in item:
                price_in_cents = item['price']
                if isinstance(price_in_cents, (int, float)):
                    processed_items[item['name']] = {"price": price_in_cents / 100.0}
                else:
                    processed_items[item['name']] = {"price": None}
        
        with open(LOOTFARM_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({"timestamp": time.time(), "items": processed_items}, f, ensure_ascii=False, indent=4)
        print("✅ LootFarm cache updated.")
        return processed_items
    except requests.exceptions.RequestException as e:
        print(f"❌ LootFarm request error: {e}")
        return None
    except ValueError as e:
        print(f"❌ LootFarm JSON decoding error: {e}. Response text (first 200 chars): {resp.text[:200]}...")
        return None
    except Exception as e:
        print(f"❌ LootFarm general error: {e}")
        return None

# NEW: Steam Community Market (SCM) - Modified for persistent saving
def load_scm_cached_data():
    if not os.path.exists(SCM_CACHE_FILE):
        return {}
    try:
        with open(SCM_CACHE_FILE, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        print("✅ Loaded SCM data from cache.")
        return cached
    except Exception as e:
        print(f"❌ Error loading SCM cache: {e}. Returning empty data.")
        return {}

def save_scm_cached_data():
    try:
        with open(SCM_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(SCM_PRICES_CACHE, f, ensure_ascii=False, indent=4)
        # print("💾 SCM cache updated on disk.") # Too verbose for periodic save
    except Exception as e:
        print(f"❌ Error saving SCM cache: {e}")

async def save_scm_cache_periodically():
    while True:
        await asyncio.sleep(SCM_CACHE_DURATION) # Save every SCM_CACHE_DURATION seconds
        save_scm_cached_data()

def get_scm_price(market_hash_name):
    global SCM_PRICES_CACHE
    
    # Check cache first
    if market_hash_name in SCM_PRICES_CACHE and \
       time.time() - SCM_PRICES_CACHE[market_hash_name].get("timestamp", 0) < SCM_CACHE_DURATION:
        print(f"Retrieving {market_hash_name} price from SCM cache.")
        return SCM_PRICES_CACHE[market_hash_name]["price"]

    print(f"🔄 Fetching fresh price for {market_hash_name} from Steam Community Market...")
    
    # URL encode the market_hash_name
    encoded_name = requests.utils.quote(market_hash_name)
    url = f"https://steamcommunity.com/market/priceoverview/?appid=730&currency=1&market_hash_name={encoded_name}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("success") and "lowest_price" in data:
            # Extract price string (e.g., "$12.34 USD") and convert to float
            price_str = data["lowest_price"]
            # Remove currency symbols and commas, then convert to float
            price_float = float(price_str.replace('$', '').replace('€', '').replace('£', '').replace(',', '').strip().split(' ')[0])
            
            SCM_PRICES_CACHE[market_hash_name] = {"price": price_float, "timestamp": time.time()}
            # save_scm_cached_data() # Not necessary to save on every fetch, periodic save is better
            return price_float
        else:
            print(f"⚠️ SCM: No lowest_price found or success was false for {market_hash_name}. Data: {data}")
            return None

    except requests.exceptions.HTTPError as e:
        print(f"❌ SCM HTTP Error for {market_hash_name}: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 429:
            print("❗ SCM API Rate Limited. You might be making too many requests.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error fetching SCM data for {market_hash_name}: {e}")
        return None
    except (json.JSONDecodeError, ValueError) as e:
        print(f"❌ JSON/Value error from SCM data for {market_hash_name}: {e}. Response content: {response.text[:200]}...")
        return None
    except Exception as e:
        print(f"❌ An unexpected error occurred during SCM price fetch for {market_hash_name}: {e}")
        return None

def load_csfloat_cached_data():
    if not os.path.exists(CSFLOAT_CACHE_FILE):
        return {} # Return empty dict if file doesn't exist
    try:
        with open(CSFLOAT_CACHE_FILE, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        # We don't check timestamp here because get_csfloat_price will do it
        print("✅ Loaded CS.FLOAT data from cache.")
        return cached # Expects a dict of {market_name: {"price": x, "timestamp": y}}
    except Exception as e:
        print(f"❌ Error loading CS.FLOAT cache: {e}. Returning empty data.")
        return {}

def save_csfloat_cached_data(data):
    try:
        with open(CSFLOAT_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("💾 CS.FLOAT cache updated on disk.")
    except Exception as e:
        print(f"❌ Error saving CS.FLOAT cache: {e}")

# CS.FLOAT
def get_csfloat_price(market_name):
    if not CSFLOAT_API_KEY:
        print("❌ CSFLOAT_API_KEY is not set. Cannot fetch prices from CS.FLOAT.")
        return None

    cached_prices = load_csfloat_cached_data()
    if market_name in cached_prices and \
       time.time() - cached_prices[market_name].get("timestamp", 0) < CSFLOAT_CACHE_DURATION:
        print(f"Retrieving {market_name} price from CS.FLOAT cache.")
        return cached_prices[market_name]["price"]

    print(f"🔄 Fetching fresh price for {market_name} from CS.FLOAT API (last resort)...")
    
    url = f'https://csfloat.com/api/v1/listings?market_hash_name={requests.utils.quote(market_name)}' # URL encode here
    print(url)
    headers = {
        "Authorization": CSFLOAT_API_KEY,
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data:
            lowest_price_listing = min(data, key=lambda x: x.get('price'))
            price_usd_cents = lowest_price_listing.get('price')
            
            if price_usd_cents is not None:
                price_usd = price_usd_cents / 100.0
                cached_prices[market_name] = {"price": price_usd, "timestamp": time.time()}
                save_csfloat_cached_data(cached_prices)
                return price_usd
        else:
            print(f"⚠️ No active listings found for {market_name} on CS.FLOAT.")
            return None

    except requests.exceptions.HTTPError as e:
        print(f"❌ CS.FLOAT API HTTP Error for {market_name}: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 401:
            print("❗ CS.FLOAT authentication failed. Check your CSFLOAT_API_KEY.")
        elif e.response.status_code == 429:
            print("❗ CS.FLOAT API Rate Limited. You might need to wait or check your plan.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error fetching CS.FLOAT data for {market_name}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON decoding error from CS.FLOAT data for {market_name}: {e}")
        return None
    except Exception as e:
        print(f"❌ An unexpected error occurred during CS.FLOAT price fetch for {market_name}: {e}")
        return None

# ByMykel (Image Data)
def download_and_cache_by_mykel_data():
    if os.path.exists(BY_MYKEL_LOCAL_CACHE_FILE):
        try:
            with open(BY_MYKEL_LOCAL_CACHE_FILE, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            if time.time() - cached_data.get("timestamp", 0) < BY_MYKEL_CACHE_DURATION:
                print("🖼️ Using cached ByMykel skin data (still fresh).")
                return cached_data.get("skins", {})
        except Exception as e:
            print(f"⚠️ Error loading ByMykel local cache, re-downloading: {e}")

    print("🌐 Downloading fresh ByMykel skin data...")
    try:
        response = requests.get(BY_MYKEL_API_URL, timeout=30)
        response.raise_for_status()
        all_skins_list = response.json()

        processed_data = {}
        for skin_item in all_skins_list:
            if 'name' in skin_item and 'image' in skin_item:
                processed_data[skin_item['name'].lower()] = {
                    "image_url": skin_item['image'],
                    "rarity": skin_item.get('rarity', {}).get('name')
                }
        
        with open(BY_MYKEL_LOCAL_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump({"timestamp": time.time(), "skins": processed_data}, f, ensure_ascii=False, indent=4)
        print("✅ ByMykel skin data downloaded and cached successfully.")
        return processed_data
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error downloading ByMykel data: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON decoding error from ByMykel data: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred during ByMykel data download: {e}")
    
    if os.path.exists(BY_MYKEL_LOCAL_CACHE_FILE):
        print("⚠️ Falling back to old local ByMykel cache due to download error.")
        try:
            with open(BY_MYKEL_LOCAL_CACHE_FILE, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            return cached_data.get("skins", {})
        except Exception as e:
            print(f"❌ Failed to load old ByMykel cache fallback: {e}")
    return {}

def get_image_url_from_by_mykel(market_hash_name: str):
    global BY_MYKEL_SKIN_DATA
    if not BY_MYKEL_SKIN_DATA:
        BY_MYKEL_SKIN_DATA = download_and_cache_by_mykel_data()
    return BY_MYKEL_SKIN_DATA.get(market_hash_name.lower(), {}).get("image_url")


# NEW: Merged Prices Data Management (for persistent pricing)
MERGED_PRICES_FILE = "merged_csgo_prices.json"
MERGED_PRICES_SAVE_INTERVAL = 1500 # Save every 25 minutes (1500 seconds)

def load_merged_prices_data():
    if not os.path.exists(MERGED_PRICES_FILE):
        return {}
    try:
        with open(MERGED_PRICES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Error decoding {MERGED_PRICES_FILE}. Starting fresh.")
        return {}
    except Exception as e:
        print(f"Error loading {MERGED_PRICES_FILE}: {e}. Starting fresh.")
        return {}

def save_merged_prices_data(data):
    try:
        with open(MERGED_PRICES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        # print(f"💾 Merged prices data saved to {MERGED_PRICES_FILE}") # Too verbose
    except Exception as e:
        print(f"❌ Error saving merged prices data to {MERGED_PRICES_FILE}: {e}")

# Call this periodically or on bot shutdown
async def save_merged_prices_periodically():
    while True:
        await asyncio.sleep(MERGED_PRICES_SAVE_INTERVAL)
        save_merged_prices_data(MERGED_CSGO_PRICES_DATA)

# MODIFIED: get_price to allow specific sources
def get_price(market_name, allowed_sources=None): #
    global SKINPORT_PRICES_CACHE, LOOTFARM_PRICES_CACHE, MERGED_CSGO_PRICES_DATA

    potential_prices_with_sources = [] # Store (price, source) tuples
    
    # Ensure source-specific caches are loaded/updated
    # These functions themselves should handle cache duration, so it's fine to call them
    if allowed_sources is None or "Skinport" in allowed_sources: #
        if SKINPORT_PRICES_CACHE is None:
            SKINPORT_PRICES_CACHE = update_skinport_cache()
    
    if allowed_sources is None or "LootFarm" in allowed_sources: #
        if LOOTFARM_PRICES_CACHE is None:
            LOOTFARM_PRICES_CACHE = update_lootfarm_cache()
    
    # Determine the name to use for Skinport lookup
    # Replace literal '★' with its Unicode escape sequence if it's a knife
    skinport_search_name = market_name
    if market_name.startswith("★"):
        skinport_search_name = market_name.replace("★", "\u2605") # \u2605 is the star character in unicode

    # 1. Try Skinport if allowed
    if allowed_sources is None or "Skinport" in allowed_sources: #
        price_from_skinport = None
        if SKINPORT_PRICES_CACHE:
            for item in SKINPORT_PRICES_CACHE:
                # Use skinport_search_name for comparison
                if item["market_hash_name"].lower() == skinport_search_name.lower():
                    price_from_skinport = item.get("suggested_price")
                    if price_from_skinport is not None:
                        print(f"✅ Price found for {market_name} on Skinport: ${price_from_skinport:.2f}")
                        potential_prices_with_sources.append((price_from_skinport, "Skinport"))
                    break # Exit loop once price is found
            if price_from_skinport is None:
                print(f"❌ Price not found for {market_name} on Skinport.")
        else:
            print(f"⚠️ Skinport cache not available for {market_name}. Skipping Skinport.")

    # 2. Try LootFarm if allowed
    if allowed_sources is None or "LootFarm" in allowed_sources: #
        price_from_lootfarm = None
        print(f"Attempting LootFarm for {market_name}...")
        if LOOTFARM_PRICES_CACHE:
            lootfarm_item = LOOTFARM_PRICES_CACHE.get(market_name)
            if lootfarm_item and lootfarm_item.get("price") is not None:
                price_from_lootfarm = lootfarm_item["price"]
                print(f"✅ Price found for {market_name} on LootFarm: ${price_from_lootfarm:.2f}")
                potential_prices_with_sources.append((price_from_lootfarm, "LootFarm"))
        if price_from_lootfarm is None:
            print(f"❌ Price not found for {market_name} on LootFarm.")
    
    # Determine the lowest price and its source from preferred sources (Skinport, LootFarm, SCM)
    final_lowest_price = None
    final_source_platform = None

    if potential_prices_with_sources:
        # Find the entry with the minimum price
        lowest_preferred_entry = min(potential_prices_with_sources, key=lambda x: x[0])
        final_lowest_price = lowest_preferred_entry[0]
        final_source_platform = lowest_preferred_entry[1]

    # Only attempt SCM or CS.FLOAT if allowed_sources is None (meaning all sources are allowed)
    # This prevents live fetches for inventory view
    if allowed_sources is None: #
        # 3. Try Steam Community Market
        price_from_scm = None
        print(f"Attempting Steam Community Market for {market_name}...")
        price_from_scm = get_scm_price(market_name)
        if price_from_scm is not None:
            print(f"✅ Price found for {market_name} on SCM: ${price_from_scm:.2f}")
            potential_prices_with_sources.append((price_from_scm, "SCM"))
            # Re-evaluate lowest price after adding SCM
            if potential_prices_with_sources:
                lowest_after_scm = min(potential_prices_with_sources, key=lambda x: x[0])
                final_lowest_price = lowest_after_scm[0]
                final_source_platform = lowest_after_scm[1]
        else:
            print(f"❌ Price not found for {market_name} on SCM.")

        # 4. Try CS.FLOAT as the last resort ONLY IF no price was found from the first three
        price_from_csfloat = None
        source_from_csfloat = None
        if final_lowest_price is None: # Only call CS.FLOAT if no price was found from Skinport, LootFarm, or SCM
            print(f"Attempting CS.FLOAT for {market_name} (last resort as other sources failed)...")
            price_from_csfloat = get_csfloat_price(market_name)
            if price_from_csfloat is not None:
                source_from_csfloat = "CS.FLOAT"
                final_lowest_price = price_from_csfloat # Update final price
                final_source_platform = source_from_csfloat # Update final source
                print(f"✅ Price found for {market_name} on CS.FLOAT: ${price_from_csfloat:.2f}")
            else:
                print(f"❌ Price not found for {market_name} on CS.FLOAT.")
        else:
            print(f"Skipping CS.FLOAT for {market_name} as a price was already found from a preferred source.")

    image_url = get_image_url_from_by_mykel(market_name)

    # Update MERGED_CSGO_PRICES_DATA with the found price (if any)
    # This acts as a long-term cache for any item ever queried
    if market_name not in MERGED_CSGO_PRICES_DATA:
        MERGED_CSGO_PRICES_DATA[market_name] = {} # Initialize if new
    
    # Update the "any" source price and timestamp
    MERGED_CSGO_PRICES_DATA[market_name]["any_source_price"] = final_lowest_price
    MERGED_CSGO_PRICES_DATA[market_name]["last_updated"] = time.time()
    
    return final_lowest_price, image_url, final_source_platform

# --- Discord Commands (Modified) ---
@bot.command(name="chroma")
async def chroma_case(ctx):
    await ctx.defer()
    # MODIFIED: Unpack variant_info
    display_name, market_name, rarity, variant_info, skin_image_url = generate_random_skin() # skin_image_url added here
    price, image_url, price_source = get_price(market_name)
    price_val = round(price, 2) if price else 0.0

    embed = discord.Embed(
        title="🎉 You unboxed:",
        description=f"**{display_name}**",
        color=RARITY_COLORS.get(rarity, 0x808080)
    )
    # MODIFIED: Add a field for variant_info if it exists
    if variant_info:
        embed.add_field(name="🎨 Variant", value=variant_info, inline=True)
    
    if price:
        embed.add_field(name="💵 Price", value=f"${price_val}")
        if price_source:
            embed.set_footer(text=f"Price fetched from {price_source}")
    else:
        embed.add_field(name="❌ Price not found", value="This item's price was not found on any marketplace.")
        embed.set_footer(text="Price not available from any platform.")

    if skin_image_url: # Prioritize the image from generate_random_skin if it's there
        embed.set_image(url=skin_image_url)
    elif image_url: # Otherwise use the image from get_price
        embed.set_image(url=image_url)

    view = SkinActionView(ctx.author.id, display_name, price_val, bot, skin_variant=variant_info) # PASS skin_variant
    await ctx.send(embed=embed, view=view)

@bot.tree.command(name="chroma", description="Unbox a Chroma case")
async def chroma_slash(interaction: discord.Interaction):
    await interaction.response.defer()
    # MODIFIED: Unpack variant_info
    display_name, market_name, rarity, variant_info, skin_image_url = generate_random_skin() # skin_image_url added here
    price, image_url, price_source = get_price(market_name)
    price_val = round(price, 2) if price else 0.0

    embed = discord.Embed(
        title="🎉 You unboxed:",
        description=f"**{display_name}**",
        color=RARITY_COLORS.get(rarity, 0x808080)
    )
    # MODIFIED: Add a field for variant_info if it exists
    if variant_info:
        embed.add_field(name="🎨 Variant", value=variant_info, inline=True)
        
    if price:
        embed.add_field(name="💵 Price", value=f"${price_val}")
        if price_source:
            embed.set_footer(text=f"Price fetched from {price_source}")
    else:
        embed.add_field(name="❌ Price not found", value="This item's price was not found on any marketplace.")
        embed.set_footer(text="Price not available from any platform.")

    if skin_image_url: # Prioritize the image from generate_random_skin if it's there
        embed.set_image(url=skin_image_url)
    elif image_url: # Otherwise use the image from get_price
        embed.set_image(url=image_url)

    view = SkinActionView(interaction.user.id, display_name, price_val, bot, skin_variant=variant_info) # PASS skin_variant
    await interaction.followup.send(embed=embed, view=view)

@bot.command(name="balance")
async def balance(ctx):
    data = load_user_data()
    balance = data.get(str(ctx.author.id), {}).get("balance", 0.0)
    embed = discord.Embed(
        title=f"💰 {ctx.author.display_name}'s Balance",
        description=f"${balance:.2f}",
        color=0x00ff00
    )
    embed.set_footer(text="Keep grinding and stacking those skins!")

    await ctx.send(embed=embed)

@bot.command(name="inventory")
async def inventory(ctx):
    data = load_user_data()
    inventory = data.get(str(ctx.author.id), {}).get("inventory", {})

    if not inventory:
        await ctx.send("🎒 Your inventory is empty.")
        return

    view = InventoryView(ctx, inventory)
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

@bot.command(name="sell")
async def sell_inventory_item(ctx, *, skin_name: str):
    user_id_str = str(ctx.author.id)
    data = load_user_data()
    user_data = data.get(user_id_str, {"balance": 0, "inventory": {}})
    inventory = user_data.get("inventory", {})

    matched_skin = None
    for inv_skin in inventory:
        if inv_skin.lower() == skin_name.lower():
            matched_skin = inv_skin
            break

    if matched_skin is None or (isinstance(inventory[matched_skin], dict) and inventory[matched_skin].get("count", 0) <= 0) or \
       (not isinstance(inventory[matched_skin], dict) and inventory[matched_skin] <= 0):
        await ctx.send(f"❌ You don't have **{skin_name}** in your inventory.")
        return

    price, _, _ = get_price(matched_skin) # Only need price for selling, ignore image and source
    if price is None:
        await ctx.send(f"❌ Could not find price for **{matched_skin}** from any marketplace.")
        return

    # Decrement count based on whether it's the old or new format
    if isinstance(inventory[matched_skin], dict):
        inventory[matched_skin]["count"] -= 1
        if inventory[matched_skin]["count"] == 0:
            del inventory[matched_skin]
    else: # Old format (just a count)
        inventory[matched_skin] -= 1
        if inventory[matched_skin] == 0:
            del inventory[matched_skin]


    user_data["balance"] += price
    data[user_id_str] = user_data
    save_user_data(data)

    embed = discord.Embed(
        title="✅ Item Sold!",
        description=f"You sold **{matched_skin}** for **${price:.2f}**.",
        color=0x2ecc71
    )
    embed.set_footer(text=f"Your new balance is ${user_data['balance']:.2f}")
    await ctx.send(embed=embed)

async def skin_autocomplete(interaction: discord.Interaction, current: str):
    user_id_str = str(interaction.user.id)
    data = load_user_data()
    inventory = data.get(user_id_str, {}).get("inventory", {})
    matches = [
        skin for skin in inventory.keys()
        if current.lower() in skin.lower()
    ]
    return [
        app_commands.Choice(name=skin, value=skin)
        for skin in matches[:25]
    ]

@bot.tree.command(name="sell", description="Sell a skin from your inventory")
@app_commands.describe(skin="The skin to sell")
@app_commands.autocomplete(skin=skin_autocomplete)
async def sell_slash(interaction: discord.Interaction, skin: str):
    user_id_str = str(interaction.user.id)
    data = load_user_data()
    user_data = data.get(user_id_str, {"balance": 0, "inventory": {}})
    inventory = user_data.get("inventory", {})

    matched_skin = None
    for inv_skin in inventory:
        if inv_skin.lower() == skin.lower():
            matched_skin = inv_skin
            break

    if matched_skin is None or (isinstance(inventory[matched_skin], dict) and inventory[matched_skin].get("count", 0) <= 0) or \
       (not isinstance(inventory[matched_skin], dict) and inventory[matched_skin] <= 0):
        await interaction.response.send_message(f"❌ You don't have **{skin}** in your inventory.", ephemeral=True)
        return

    price, _, _ = get_price(matched_skin) # Only need price for selling, ignore image and source
    if price is None:
        await interaction.response.send_message(f"❌ Could not find price for **{matched_skin}** from any marketplace.", ephemeral=True)
        return

    # Decrement count based on whether it's the old or new format
    if isinstance(inventory[matched_skin], dict):
        inventory[matched_skin]["count"] -= 1
        if inventory[matched_skin]["count"] == 0:
            del inventory[matched_skin]
    else: # Old format (just a count)
        inventory[matched_skin] -= 1
        if inventory[matched_skin] == 0:
            del inventory[matched_skin]


    user_data["balance"] += price
    data[user_id_str] = user_data
    save_user_data(data)

    embed = discord.Embed(
        title="✅ Item Sold!",
        description=f"You sold **{matched_skin}** for **${price:.2f}**.",
        color=0x2ecc71
    )
    embed.set_footer(text=f"Your new balance is ${user_data['balance']:.2f}")

    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- CS:GO Bet Game Logic ---
CSGO_TEAMS = [
    "Faze Clan", "Vitality", "Falcons", "Kaks Gaming",
    "Bot Jojo106 Gayming", "Michaelele 游戏", "PengyZ E-Sports", "Astralis"
]

KILL_EMOJIS = ["🔫", "💥", "🎯", "🔪", "💣"] # Gun, Explosion, Headshot, Knife, Bomb kill
BOMB_EMOJIS = {"plant": "💣", "defuse": "✅"}

# Function to simulate a single round
async def simulate_round(round_num, team1_name, team2_name, is_t_side_team1):
    round_log = []
    winner_team = None

    # Randomly determine round winner (50/50 for each team to win the round)
    if random.random() < 0.5:
        winner_team = team1_name
        loser_team = team2_name
    else:
        winner_team = team2_name
        loser_team = team1_name

    round_log.append(f"**Round {round_num}:**\n")

    # Simulate kills
    num_kills = random.randint(2, 5)
    players_winner = [f"Player{i+1} ({winner_team})" for i in range(5)]
    players_loser = [f"Player{i+1} ({loser_team})" for i in range(5)]

    killed_players = random.sample(players_loser, min(num_kills, 5))

    for i in range(num_kills):
        killer = random.choice(players_winner)
        if killed_players:
            victim = killed_players.pop(0) # Pop to ensure unique victims per round
        else:
            victim = random.choice(players_loser) # Fallback if not enough unique victims
        kill_emoji = random.choice(KILL_EMOJIS)
        round_log.append(f"  {killer} {kill_emoji} {victim}")

    # Simulate bomb plant/defuse if applicable
    if winner_team == team1_name and is_t_side_team1: # Team 1 is T-side and won
        if random.random() < 0.7: # 70% chance to plant if T-side wins
            round_log.append(f"  {BOMB_EMOJIS['plant']} {team1_name} planted the bomb!")
            if random.random() < 0.3: # 30% chance for defuse attempt if planted
                round_log.append(f"  {BOMB_EMOJIS['defuse']} {team2_name} defused the bomb!")
                # If defused, the round winner might change, but for simplicity, we'll keep the initial winner for now.
                # In a more complex sim, defuse would flip the round win.
    elif winner_team == team2_name and not is_t_side_team1: # Team 2 is T-side and won
        if random.random() < 0.7:
            round_log.append(f"  {BOMB_EMOJIS['plant']} {team2_name} planted the bomb!")
            if random.random() < 0.3:
                round_log.append(f"  {BOMB_EMOJIS['defuse']} {team1_name} defused the bomb!")

    round_log.append(f"**{winner_team} wins the round!**\n")
    return "\n".join(round_log), winner_team

async def simulate_cs_match(interaction, bet_amount, chosen_team, opponent_team):
    team1_score = 0
    team2_score = 0
    max_rounds = 15 # Max rounds for a short match
    rounds_to_win = 8 # First to 8 wins

    # Determine which team starts as T-side (Terrorist)
    chosen_team_starts_t_side = random.choice([True, False])

    message_content = f"### ⚔️ {chosen_team} vs {opponent_team} - Match Start! ⚔️\n"
    message_content += f"**Current Score:** {chosen_team}: {team1_score} | {opponent_team}: {team2_score}\n"
    message_content += "--- Killfeed ---\n"
    # Ensure interaction.followup.send is awaited when called outside interaction.response.send_message
    if not interaction.response.is_done():
        await interaction.response.send_message("Starting match simulation...")
        match_message = await interaction.followup.send(message_content)
    else:
        match_message = await interaction.followup.send(content=message_content)


    for round_num in range(1, max_rounds + 1):
        if team1_score >= rounds_to_win or team2_score >= rounds_to_win:
            break # Match ends if one team reaches winning score

        # Sides swap after 7 rounds (half-time for a 15-round match)
        current_chosen_team_is_t_side = chosen_team_starts_t_side
        if round_num > 7: # Half-time
            current_chosen_team_is_t_side = not chosen_team_starts_t_side

        round_log, winner = await simulate_round(round_num, chosen_team, opponent_team, current_chosen_team_is_t_side)

        if winner == chosen_team:
            team1_score += 1
        else:
            team2_score += 1

        # Update message with new round log and score
        message_content = f"### ⚔️ {chosen_team} vs {opponent_team} - Match In Progress ⚔️\n"
        message_content += f"**Current Score:** {chosen_team}: {team1_score} | {opponent_team}: {team2_score}\n"
        message_content += "--- Killfeed ---\n"
        message_content += round_log

        await match_message.edit(content=message_content)
        await asyncio.sleep(2) # Pause between rounds for readability

    # Determine final winner
    final_winner = ""
    if team1_score > team2_score:
        final_winner = chosen_team
    elif team2_score > team1_score:
        final_winner = opponent_team
    else:
        final_winner = "It's a Tie!" # Should not happen with first to X rounds, but good for ties

    return final_winner, team1_score, team2_score

class BetView(discord.ui.View):
    def __init__(self, user_id, bet_amount, team1, team2, bot_instance):
        super().__init__(timeout=60) # User has 60 seconds to choose
        self.user_id = user_id
        self.bet_amount = bet_amount
        self.team1 = team1
        self.team2 = team2
        self.bot = bot_instance

        # Dynamically create and add buttons for each team
        # Use a unique prefix like "bet_select_team_" to avoid conflicts
        team1_button = discord.ui.Button(label=team1, style=discord.ButtonStyle.blurple, custom_id=f"bet_select_team_{team1}")
        team2_button = discord.ui.Button(label=team2, style=discord.ButtonStyle.blurple, custom_id=f"bet_select_team_{team2}")

        # Assign a single callback for both team selection buttons
        team1_button.callback = self._team_selection_callback
        team2_button.callback = self._team_selection_callback

        self.add_item(team1_button)
        self.add_item(team2_button)
        # The cancel button will be added by its decorator below

    async def on_timeout(self):
        # Disable all buttons on timeout
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(content="🚫 Bet selection timed out. Your bet has been refunded.", view=self)
            # Refund the bet if timed out
            data = load_user_data()
            user_id_str = str(self.user_id)
            user_data = data.get(user_id_str, {"balance": 0.0})
            user_data["balance"] += self.bet_amount
            save_user_data(data)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="bet_cancel")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ This isn't your bet to cancel!", ephemeral=True)
            return

        # Disable all buttons
        for item in self.children:
            item.disabled = True

        # Refund the bet
        data = load_user_data()
        user_id_str = str(self.user_id)
        user_data = data.get(user_id_str, {"balance": 0.0})
        user_data["balance"] += self.bet_amount
        save_user_data(data)

        await interaction.response.edit_message(content="❌ Bet cancelled. Your bet has been refunded.", view=self)

    async def _team_selection_callback(self, interaction: discord.Interaction):
        # Extract the selected team name from the custom_id
        # custom_id format: "bet_select_team_TeamName"
        selected_team_name = interaction.data["custom_id"].replace("bet_select_team_", "")
        await self.handle_team_selection(interaction, selected_team_name)

    async def handle_team_selection(self, interaction: discord.Interaction, selected_team_name: str):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ This isn't your bet!", ephemeral=True)
            return

        # Disable all buttons once a choice is made
        for item in self.children:
            item.disabled = True
        # Use edit_message for the initial response if already deferred or responded
        if interaction.response.is_done():
            await interaction.edit_original_response(content=f"You chose **{selected_team_name}**! Simulating match...", view=self)
        else:
            await interaction.response.send_message(content=f"You chose **{selected_team_name}**! Simulating match...", view=self)


        # Determine the opponent team
        opponent_team_name = self.team2 if selected_team_name == self.team1 else self.team1

        # Simulate the match
        final_winner, team1_score, team2_score = await simulate_cs_match(interaction, self.bet_amount, selected_team_name, opponent_team_name)

        data = load_user_data()
        user_id_str = str(self.user_id)
        user_data = data.get(user_id_str, {"balance": 0.0})
        current_balance = user_data["balance"]

        result_embed = discord.Embed(title="🏆 Match Result", color=0x3498db)
        result_embed.add_field(name="Final Score", value=f"{selected_team_name}: {team1_score} | {opponent_team_name}: {team2_score}", inline=False)
        result_embed.add_field(name="Match Winner", value=f"**{final_winner}**", inline=False)

        if final_winner == selected_team_name:
            # Player wins, apply payout (e.g., 1.9x for a 5% house edge on a 50/50 chance)
            payout_multiplier = 1.9
            winnings = self.bet_amount * payout_multiplier
            new_balance = current_balance + winnings
            result_embed.description = f"🎉 Your team **{selected_team_name}** won! You won **${winnings:.2f}**!"
            result_embed.color = 0x00ff00 # Green for win
        else:
            # Player loses (already deducted bet at command start)
            new_balance = current_balance # Balance already reduced by bet_amount
            result_embed.description = f"💔 Your team **{selected_team_name}** lost. You lost **${self.bet_amount:.2f}**."
            result_embed.color = 0xff0000 # Red for loss

        user_data["balance"] = new_balance
        save_user_data(data)

        result_embed.set_footer(text=f"Your new balance: ${new_balance:.2f}")
        await interaction.followup.send(embed=result_embed)

@bot.command(name="bet")
async def bet(ctx, amount: float):
    user_id_str = str(ctx.author.id)
    data = load_user_data()
    user_data = data.get(user_id_str, {"balance": 0.0, "inventory": {}})
    current_balance = user_data.get("balance", 0.0)

    if amount <= 0:
        await ctx.send("🚫 You must bet a positive amount.")
        return

    if amount > current_balance:
        await ctx.send(f"❌ You don't have enough balance! Your current balance is **${current_balance:.2f}**.")
        return

    # Deduct bet amount immediately
    user_data["balance"] -= amount
    save_user_data(data)

    # Randomly pick two distinct teams
    teams_for_bet = random.sample(CSGO_TEAMS, 2)
    team1 = teams_for_bet[0]
    team2 = teams_for_bet[1]

    embed = discord.Embed(
        title="Choose Your Team!",
        description=f"You are betting **${amount:.2f}**.\n\nWhich team will win?",
        color=0x3498db
    )
    embed.add_field(name="Team 1", value=team1, inline=True)
    embed.add_field(name="Team 2", value=team2, inline=True)
    embed.set_footer(text="Select your team below within 60 seconds.")

    view = BetView(ctx.author.id, amount, team1, team2, bot)

    # Store the message to allow the view to edit it later
    view.message = await ctx.send(embed=embed, view=view)


@bot.tree.command(name="bet", description="Bet on a simulated CS:GO match (5% house edge)")
@app_commands.describe(amount="The amount of money to bet")
async def bet_slash(interaction: discord.Interaction, amount: float):
    user_id_str = str(interaction.user.id)
    data = load_user_data()
    user_data = data.get(user_id_str, {"balance": 0.0, "inventory": {}})
    current_balance = user_data.get("balance", 0.0)

    if amount <= 0:
        await interaction.response.send_message("🚫 You must bet a positive amount.", ephemeral=True)
        return

    if amount > current_balance:
        await interaction.response.send_message(f"❌ You don't have enough balance! Your current balance is **${current_balance:.2f}**.", ephemeral=True)
        return

    # Deduct bet amount immediately
    user_data["balance"] -= amount
    save_user_data(data)

    # Randomly pick two distinct teams
    teams_for_bet = random.sample(CSGO_TEAMS, 2)
    team1 = teams_for_bet[0]
    team2 = teams_for_bet[1]

    embed = discord.Embed(
        title="Choose Your Team!",
        description=f"You are betting **${amount:.2f}**.\n\nWhich team will win?",
        color=0x3498db
    )
    embed.add_field(name="Team 1", value=team1, inline=True)
    embed.add_field(name="Team 2", value=team2, inline=True)
    embed.set_footer(text="Select your team below within 60 seconds.")

    view = BetView(interaction.user.id, amount, team1, team2, bot)

    await interaction.response.send_message(embed=embed, view=view)
    # Store the message to allow the view to edit it later
    view.message = await interaction.original_response()

@bot.command(name="transfer")
async def transfer_money(ctx, member: discord.Member, amount: float):
    """
    Transfers money from your balance to another user's balance.
    Usage: cs!transfer <@user> <amount>
    """
    sender_id_str = str(ctx.author.id)
    recipient_id_str = str(member.id)
    
    data = load_user_data()
    sender_data = data.get(sender_id_str, {"balance": 0.0})
    recipient_data = data.get(recipient_id_str, {"balance": 0.0})

    sender_balance = sender_data.get("balance", 0.0)

    # Validation
    if amount <= 0:
        await ctx.send("🚫 You must transfer a positive amount.")
        return

    if amount > sender_balance:
        await ctx.send(f"❌ You don't have enough balance to transfer **${amount:.2f}**! Your current balance is **${sender_balance:.2f}**.")
        return

    if ctx.author.id == member.id:
        await ctx.send("🤔 You cannot transfer money to yourself!")
        return

    # Perform transfer
    sender_data["balance"] -= amount
    recipient_data["balance"] += amount

    data[sender_id_str] = sender_data
    data[recipient_id_str] = recipient_data
    save_user_data(data)

    # Confirmation messages
    embed_sender = discord.Embed(
        title="💸 Money Transferred!",
        description=f"You successfully transferred **${amount:.2f}** to {member.mention}.",
        color=0x00ff00
    )
    embed_sender.set_footer(text=f"Your new balance: ${sender_data['balance']:.2f}")
    await ctx.send(embed=embed_sender)

    # Try to notify the recipient
    try:
        embed_recipient = discord.Embed(
            title="💰 Money Received!",
            description=f"{ctx.author.mention} has transferred **${amount:.2f}** to you!",
            color=0x00ff00
        )
        embed_recipient.set_footer(text=f"Your new balance: ${recipient_data['balance']:.2f}")
        await member.send(embed=embed_recipient)
    except discord.Forbidden:
        print(f"Could not send DM to {member.name} ({member.id}).")
        await ctx.send(f"⚠️ I couldn't DM {member.mention} about the transfer, but their balance has been updated.", ephemeral=True)
    except Exception as e:
        print(f"Error sending DM to {member.name} ({member.id}): {e}")
        await ctx.send(f"⚠️ An error occurred while trying to notify {member.mention}, but their balance has been updated.", ephemeral=True)

@bot.tree.command(name="transfer", description="Transfer money to another user")
@app_commands.describe(member="The user to transfer money to", amount="The amount to transfer")
async def transfer_slash(interaction: discord.Interaction, member: discord.Member, amount: float):
    sender_id_str = str(interaction.user.id)
    recipient_id_str = str(member.id)
    
    data = load_user_data()
    sender_data = data.get(sender_id_str, {"balance": 0.0})
    recipient_data = data.get(recipient_id_str, {"balance": 0.0})

    sender_balance = sender_data.get("balance", 0.0)

    # Validation
    if amount <= 0:
        await interaction.response.send_message("🚫 You must transfer a positive amount.", ephemeral=True)
        return

    if amount > sender_balance:
        await interaction.response.send_message(f"❌ You don't have enough balance to transfer **${amount:.2f}**! Your current balance is **${sender_balance:.2f}**.", ephemeral=True)
        return

    if interaction.user.id == member.id:
        await interaction.response.send_message("🤔 You cannot transfer money to yourself!", ephemeral=True)
        return

    # Defer the response as the operation involves file I/O and potential DM
    await interaction.response.defer(ephemeral=False) # Make it visible to others if successful

    # Perform transfer
    sender_data["balance"] -= amount
    recipient_data["balance"] += amount

    data[sender_id_str] = sender_data
    data[recipient_id_str] = recipient_data
    save_user_data(data)

    # Confirmation messages
    embed_sender = discord.Embed(
        title="💸 Money Transferred!",
        description=f"You successfully transferred **${amount:.2f}** to {member.mention}.",
        color=0x00ff00
    )
    embed_sender.set_footer(text=f"Your new balance: ${sender_data['balance']:.2f}")
    await interaction.followup.send(embed=embed_sender)

    # Try to notify the recipient
    try:
        embed_recipient = discord.Embed(
            title="💰 Money Received!",
            description=f"{interaction.user.mention} has transferred **${amount:.2f}** to you!",
            color=0x00ff00
        )
        embed_recipient.set_footer(text=f"Your new balance: ${recipient_data['balance']:.2f}")
        await member.send(embed=embed_recipient)
    except discord.Forbidden:
        print(f"Could not send DM to {member.name} ({member.id}).")
        await interaction.followup.send(f"⚠️ I couldn't DM {member.mention} about the transfer, but their balance has been updated.", ephemeral=True)
    except Exception as e:
        print(f"Error sending DM to {member.name} ({member.id}): {e}")
        await interaction.followup.send(f"⚠️ An error occurred while trying to notify {member.mention}, but their balance has been updated.", ephemeral=True)

bot.run(TOKEN)