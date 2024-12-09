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

# File to track processed orders
PROCESSED_ORDERS_FILE = "processed_orders.json"

# Mapping for region codes
STATE_MAPPING = {
    "GA": "Greater Accra",
    "AH": "Ashanti",
    "AA": "Ahafo",
    "BR": "Brong-Ahafo",
    "CE": "Central",
    "EP": "Eastern",
    "NR": "Northern",
    "UE": "Upper East",
    "UW": "Upper West",
    "WR": "Western",
    "VR": "Volta",
    "WP": "Western North",
    "CP": "Cape Coast",
}

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

# Fetch orders for today only
def fetch_all_orders_for_today():
    all_orders = []
    page = 1

    # Define the start and end of the current day
    start_of_day = f"{today}T00:00:00"
    end_of_day = f"{today}T23:59:59"

    while True:
        try:
            # Use date range filtering for today's orders
            response = wcapi.get("orders", params={
                "after": start_of_day,
                "before": end_of_day,
                "per_page": 100,
                "page": page
            })
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

# Save orders to VDL CSV
def save_orders_to_vdl_csv(orders, run_number):
    file_name = f"vdl_orders_{today_csv_date}_run{run_number}.csv"
    is_new_file = not os.path.exists(file_name)

    with open(file_name, mode="a", newline="") as file:
        writer = csv.writer(file)
        if is_new_file:
            # Write header for VDL
            writer.writerow(["DATE [dd/mm/yyyy]", "PRODUCT", "UNIT PRICE", "NAME OF CUSTOMER", "REGION", "LOCATION OF CUSTOMER", "PHONE NUMBER", "QUANTITY OF PRODUCTS ORDERED", "COMMENT"])

        for order in orders:
            for item in order['line_items']:
                region_full = STATE_MAPPING.get(order['billing']['state'], order['billing']['state'])
                writer.writerow([
                    today_csv_date,  # Date
                    item['name'],  # Product
                    item['price'],  # Unit Price
                    f"{order['billing']['first_name']} {order['billing']['last_name']}",  # Name of Customer
                    region_full,  # Region
                    order['billing']['address_1'],  # Location
                    order['billing']['phone'],  # Phone
                    item['quantity'],  # Quantity
                    ""  # Comment
                ])
    print(f"VDL orders saved to {file_name}")

# Save orders to Stride CSV
def save_orders_to_stride_csv(orders, run_number):
    file_name = f"stride_orders_{today_csv_date}_run{run_number}.csv"
    is_new_file = not os.path.exists(file_name)

    with open(file_name, mode="a", newline="") as file:
        writer = csv.writer(file)
        if is_new_file:
            # Write header for Stride
            writer.writerow(["Order ID", "Customer Name", "Phone", "Address", "Product", "Quantity", "Price"])

        for order in orders:
            for item in order['line_items']:
                writer.writerow([
                    order['id'],  # Order ID
                    f"{order['billing']['first_name']} {order['billing']['last_name']}",  # Customer Name
                    order['billing']['phone'],  # Phone
                    order['billing']['address_1'],  # Address
                    item['name'],  # Product
                    item['quantity'],  # Quantity
                    item['price']  # Price
                ])
    print(f"Stride orders saved to {file_name}")

# Main function
if __name__ == "__main__":
    # Load processed orders from file
    processed_orders = load_processed_orders()

    # Fetch all orders for today
    all_orders = fetch_all_orders_for_today()

    # Filter out already processed orders
    new_orders = [order for order in all_orders if order['id'] not in processed_orders]

    if new_orders:
        print(f"Fetched {len(new_orders)} new orders for today.")

        # Add new orders to the processed set
        processed_orders.update(order['id'] for order in new_orders)

        # Determine the current run number
        existing_files = [f for f in os.listdir() if f.startswith(f"new_orders_{today_csv_date}")]
        run_number = len(existing_files) + 1

        # Save new orders to JSON
        save_orders_to_json(new_orders, run_number)

        # Save new orders to VDL CSV
        save_orders_to_vdl_csv(new_orders, run_number)

        # Save new orders to Stride CSV
        save_orders_to_stride_csv(new_orders, run_number)

        # Update the processed orders log
        save_processed_orders(processed_orders)
    else:
        print("No new orders found.")
