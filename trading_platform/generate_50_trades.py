import requests
import random
import time

# The API endpoint you successfully tested
url = "http://localhost:8000/api/v1/orders/"

# Realistic instruments for a trading platform
instruments = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", 
    "NZDUSD", "USDCHF", "BTCUSD", "ETHUSD", "XAUUSD"
]

sides = ["buy", "sell"]

print("Starting to generate 50 random trades...")

for i in range(1, 51):
    # Pick a random instrument
    symbol = random.choice(instruments)
    
    # Randomly pick buy or sell
    side = random.choice(sides)
    
    # Generate a random quantity (lots) between 0.01 and 1.0
    quantity = round(random.uniform(0.01, 1.0), 2)
    
    # Generate a random price based on the instrument type
    # Forex is 1.0 - 2.0, Crypto is 1000 - 65000, Gold is 1800+
    if symbol in ["BTCUSD"]:
        price = round(random.uniform(30000, 65000), 2)
    elif symbol in ["ETHUSD"]:
        price = round(random.uniform(1500, 4000), 2)
    elif symbol in ["XAUUSD"]:
        price = round(random.uniform(1800, 2100), 2)
    else:
        price = round(random.uniform(0.65, 1.60), 5)

    # Build the JSON payload
    payload = {
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": price
    }

    try:
        # Send the POST request
        response = requests.post(url, json=payload)
        
        if response.status_code in [200, 201]:
            print(f"[{i}/50] SUCCESS: {symbol} {side} {quantity} @ {price} - ID: {response.json().get('id')}")
        else:
            print(f"[{i}/50] FAILED: Status {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"[{i}/50] ERROR: Could not connect to server. Is it running?")
        print(f"Error details: {e}")
        break  # Stop if the server isn't running

    # Short pause to avoid overwhelming the database/backend (optional)
    time.sleep(0.05)

print("\nFinished generating data!")