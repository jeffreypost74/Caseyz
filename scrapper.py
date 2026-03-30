import requests
import json
import time

def get_skinport_prices():
    try:
        resp = requests.get("https://api.skinport.com/v1/items?app_id=730", timeout=10)
        resp.raise_for_status()
        return {item['market_hash_name']: item for item in resp.json()}
    except requests.exceptions.RequestException as e:
        print(f"Skinport request error: {e}")
        return {}
    except ValueError as e:
        print(f"Skinport JSON decoding error: {e}")
        return {}
    except Exception as e:
        print(f"Skinport general error: {e}")
        return {}

def get_lootfarm_prices():
    try:
        resp = requests.get("https://loot.farm/fullprice.json", timeout=10)
        resp.raise_for_status()
        items = resp.json()
        
        if not isinstance(items, list):
            print("LootFarm API returned unexpected data type (not a list).")
            return {}
        
        processed_items = {} # Use a new dictionary to store processed items
        for item in items:
            if isinstance(item, dict) and 'name' in item and 'price' in item:
                price_in_cents = item['price']
                if isinstance(price_in_cents, (int, float)):
                    # Divide by 100.0 here, before adding to the dictionary
                    processed_items[item['name']] = {"price": price_in_cents / 100.0}
                else:
                    processed_items[item['name']] = {"price": None} # Set to None if invalid
                    print(f"LootFarm: Invalid price 'p' for item: {item.get('name', 'Unknown')}")
            else:
                print(f"LootFarm: Skipping malformed item or item without 'name' or 'p': {item}")
        return processed_items # Return the dictionary with processed prices
    except requests.exceptions.RequestException as e:
        print(f"LootFarm request error: {e}")
        return {}
    except ValueError as e:
        print(f"LootFarm JSON decoding error: {e}")
        return {}
    except Exception as e:
        print(f"LootFarm general error: {e}")
        return {}


def merge_all_prices():
    skinport = get_skinport_prices()
    lootfarm = get_lootfarm_prices() # This now has 'p' already divided
    merged = {}

    all_names = set(skinport.keys()) | set(lootfarm.keys()) 

    for name in all_names:
        merged[name] = {
            "skinport": skinport.get(name, {}).get("min_price"),
            # 'p' is now correctly formatted (divided by 100.0) from get_lootfarm_prices
            "lootfarm": lootfarm.get(name, {}).get("price"),
        }

    return merged

if __name__ == "__main__":
    print("Fetching prices, please wait...")
    all_data = merge_all_prices()
    print("\n--- Price Data ---")

    output_filename = "merged_csgo_prices.json"
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=4)
        print(f"\nSuccessfully saved all merged data to '{output_filename}'")
    except Exception as e:
        print(f"\nError saving data to JSON: {e}")

    print("\n--- Sample of Merged Data (items with at least 2 prices) ---")
    count = 0
    for item_name, prices in all_data.items():
        available_prices = [p for p in prices.values() if p is not None]
        if len(available_prices) >= 2:
            print(f"{item_name}: {prices}")
            count += 1
        if count >= 5:
            break
    if count == 0:
        print("No items found with prices from at least two sources in the sample.")