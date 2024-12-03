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
    timeout=20  # Increased timeout
)

# Get today's date in the required format
today = datetime.now().strftime("%Y-%m-%d")

# Fetch all orders for the current date with pagination
def fetch_all_orders_for_today():
    all_orders = []
    page = 1  # Start with the first page

    while True:
        try:
            response = wcapi.get("orders", params={"date_created": today, "per_page": 100, "page": page})
            if response.status_code == 200:
                orders = response.json()
                if not orders:  # If no more orders are returned, exit the loop
                    break
                all_orders.extend(orders)  # Add the fetched orders to the list
                page += 1  # Move to the next page
            else:
                print(f"Error fetching orders: {response.status_code}")
                print(response.json())
                break
        except Exception as e:
            print(f"An error occurred: {e}")
            break

    return all_orders

# Save orders to a JSON file
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

# Save orders to a CSV file for Swoove
def save_orders_to_swoove_csv(orders, file_name="swoove.csv"):
    with open(file_name, mode="w", newline="") as file:
        writer = csv.writer(file)
        # Write the header row
        writer.writerow(["Pickup Name", "Pickup Mobile", "Pickup Location", "Dropoff Name", "Dropoff Mobile", "Dropoff Location", "Item Name", "Item Price", "Item Size"])

        for order in orders:
            for item in order['line_items']:
                writer.writerow([
                    "shopeazygh",  # Pickup Name
                    "0558676095",  # Pickup Mobile
                    "Omanjor",  # Pickup Location
                    f"{order['billing']['first_name']} {order['billing']['last_name']}",  # Dropoff Name
                    order['billing']['phone'],  # Dropoff Mobile
                    order['billing']['address_1'],  # Dropoff Location
                    item['name'],  # Item Name
                    item['price'],  # Item Price
                    "Small",  # Item Size (default prepended with "Small")
                ])
    print(f"Swoove orders saved to {file_name}")

# Save orders to a CSV file for VDL
def save_orders_to_vdl_csv(orders, file_name="vdl.csv"):
    with open(file_name, mode="w", newline="") as file:
        writer = csv.writer(file)
        # Write the header row
        writer.writerow(["DATE [dd/mm/yyyy]", "PRODUCT", "UNIT PRICE", "NAME OF CUSTOMER", "REGION", "LOCATION OF CUSTOMER", "PHONE NUMBER", "QUANTITY OF PRODUCTS ORDERED", "COMMENT"])

        for order in orders:
            for item in order['line_items']:
                writer.writerow([
                    datetime.now().strftime("%d/%m/%Y"),  # Date
                    item['name'],  # Product
                    item['price'],  # Unit Price
                    f"{order['billing']['first_name']} {order['billing']['last_name']}",  # Name of Customer
                    order['billing']['state'],  # Region
                    order['billing']['address_1'],  # Location of Customer
                    order['billing']['phone'],  # Phone Number
                    item['quantity'],  # Quantity of Products Ordered
                    "",  # Comment (default empty)
                ])
    print(f"VDL orders saved to {file_name}")

# Main function
if __name__ == "__main__":
    orders = fetch_all_orders_for_today()
    if orders:
        print(f"Fetched {len(orders)} orders for today.")
        save_orders_to_json(orders)
        save_orders_to_swoove_csv(orders)
        save_orders_to_vdl_csv(orders)
    else:
        print("No orders found for today.")