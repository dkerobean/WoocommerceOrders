import os
import json
from woocommerce import API
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Fetch credentials from environment variables
WC_STORE_URL = os.getenv("WOOCOMMERCE_STORE_URL")
WC_CONSUMER_KEY = os.getenv("WOOCOMMERCE_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WOOCOMMERCE_CONSUMER_SECRET")

# Initialize WooCommerce API client
wcapi = API(
    url=WC_STORE_URL,
    consumer_key=WC_CONSUMER_KEY,
    consumer_secret=WC_CONSUMER_SECRET,
    version="wc/v3"
)

# Get today's date in the required format
today = datetime.now().strftime("%Y-%m-%d")


# Fetch orders for the current date
def fetch_orders_for_today():
    try:
        response = wcapi.get("orders", params={"date_created": today})
        if response.status_code == 200:
            orders = response.json()
            return orders
        else:
            print(f"Error fetching orders: {response.status_code}")
            print(response.json())
            return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


# Extract relevant fields from orders and save to JSON
def save_orders_to_json(orders, file_name="orders.json"):
    formatted_orders = []
    for order in orders:
        formatted_order = {
            "name": f"{order['billing']['first_name']} {order['billing']['last_name']}",
            "location": order['billing']['address_1'],
            "product": ", ".join([item['name'] for item in order['line_items']]),
            "state": order['billing']['state'],
            "phone_number": order['billing']['phone']
        }
        formatted_orders.append(formatted_order)

    # Write to a JSON file
    with open(file_name, "w") as file:
        json.dump(formatted_orders, file, indent=4)
    print(f"Orders saved to {file_name}")


# Main function
if __name__ == "__main__":
    orders = fetch_orders_for_today()
    if orders:
        save_orders_to_json(orders)
    else:
        print("No orders found for today.")
