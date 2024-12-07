import os
import json
import csv
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
    version="wc/v3",
    timeout=20
)

# Get today's date
today = datetime.now().strftime("%Y-%m-%d")
today_csv_date = datetime.now().strftime("%d-%m-%Y")  # For filenames

# Processed orders log file
PROCESSED_ORDERS_FILE = "processed_orders.json"


# Load processed orders
def load_processed_orders():
    if os.path.exists(PROCESSED_ORDERS_FILE):
        with open(PROCESSED_ORDERS_FILE, "r") as file:
            return set(json.load(file))
    return set()


# Save processed orders
def save_processed_orders(order_ids):
    with open(PROCESSED_ORDERS_FILE, "w") as file:
        json.dump(list(order_ids), file)


# Fetch all orders for today
def fetch_all_orders_for_today():
    all_orders = []
    page = 1

    while True:
        try:
            response = wcapi.get("orders", params={"date_created": today, "per_page": 100, "page": page})
            if response.status_code == 200:
                orders = response.json()
                if not orders:
                    break
                all_orders.extend(orders)
                page += 1
            else:
                print(f"Error fetching orders: {response.status_code}")
                print(response.json())
                break
        except Exception as e:
            print(f"An error occurred: {e}")
            break

    return all_orders


# Save orders to a JSON file
def save_orders_to_json(orders, run_number):
    file_name = f"new_orders_{today_csv_date}_run{run_number}.json"
    formatted_orders = [
        {
            "location": order['billing']['address_1'],
            "product": ", ".join([item['name'] for item in order['line_items']]),
            "phone_number": order['billing']['phone']
        }
        for order in orders
    ]

    with open(file_name, "w") as file:
        json.dump(formatted_orders, file, indent=4)
    print(f"New orders saved to {file_name}")


# Main function
if __name__ == "__main__":
    processed_orders = load_processed_orders()
    all_orders = fetch_all_orders_for_today()
    new_orders = [order for order in all_orders if order['id'] not in processed_orders]

    if new_orders:
        print(f"Fetched {len(new_orders)} new orders for today.")
        processed_orders.update(order['id'] for order in new_orders)

        # Determine the current run number
        existing_files = [f for f in os.listdir() if f.startswith(f"new_orders_{today_csv_date}")]
        run_number = len(existing_files) + 1

        # Save the new orders to a file
        save_orders_to_json(new_orders, run_number)

        # Update the processed orders log
        save_processed_orders(processed_orders)
    else:
        print("No new orders found.")