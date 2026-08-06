import requests

response = requests.post(
    "http://localhost:8000/api/v1/orders/",
    json={"symbol": "EURUSD", "side": "buy", "quantity": 0.1, "price": 1.1000}
)

print(f"Status: {response.status_code}")
print("Raw server response:")
print(response.text)  # This will show what the server actually returned