import os
import json
import csv
import pandas as pd
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

# Define file paths
DATA_FOLDER = "data"
PROCESSED_ORDERS_FILE = os.path.join(DATA_FOLDER, "processed_orders.json")
ALL_ORDERS_FILE = os.path.join(DATA_FOLDER, "all_orders.json")
EMAIL_LIST_FILE = os.path.join(DATA_FOLDER, "emails.csv")
PHONE_LIST_FILE = os.path.join(DATA_FOLDER, "phone_numbers.csv")

# Ensure data folder exists
os.makedirs(DATA_FOLDER, exist_ok=True)

# Get today's date
today = datetime.now().strftime("%Y-%m-%d")
today_csv_date = datetime.now().strftime("%d-%m-%Y")

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

# Format phone number to Ghanaian format
def format_ghanaian_phone(phone):
    phone = "".join(filter(str.isdigit, phone))
    if len(phone) == 9 and phone.startswith("2"):
        return f"+233{phone}"
    elif len(phone) == 10 and phone.startswith("0"):
        return f"+233{phone[1:]}"
    elif len(phone) == 12 and phone.startswith("233"):
        return f"+{phone}"
    return None

# Append to CSV
def append_to_csv(file_path, data, columns):
    file_exists = os.path.exists(file_path)
    with open(file_path, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        if not file_exists:
            writer.writeheader()
        for row in data:
            writer.writerow(row)

# Save JSON data
def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

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

# Process orders and update lists
def process_orders(new_orders, run_number):
    emails = set()
    phone_numbers = set()
    vdl_data = []
    orders_data = []

    for order in new_orders:
        # Extract data
        email = order["billing"]["email"]
        phone = format_ghanaian_phone(order["billing"]["phone"])
        customer_name = order["billing"]["first_name"] + " " + order["billing"]["last_name"]
        region = order["billing"].get("state", "Unknown")
        location = order["billing"]["address_1"]
        date = datetime.strptime(order["date_created"], "%Y-%m-%dT%H:%M:%S").strftime("%d/%m/%Y")
        products = ", ".join([item["name"] for item in order["line_items"]])
        unit_price = sum(float(item["price"]) for item in order["line_items"])
        quantity = sum(item["quantity"] for item in order["line_items"])

        # Prepare order data for JSON
        orders_data.append({
            "Location": location,
            "Product": products,
            "Phone Number": phone,
        })

        # Add to VDL data
        if phone:
            vdl_data.append({
                "DATE [dd/mm/yyyy]": date,
                "PRODUCT": products,
                "UNIT PRICE": unit_price,
                "NAME OF CUSTOMER": customer_name,
                "REGION": region,
                "LOCATION OF CUSTOMER": location,
                "PHONE NUMBER": phone,
                "QUANTITY OF PRODUCTS ORDERED": quantity,
                "COMMENT": ""
            })

        # Update email and phone lists
        if email:
            emails.add(email)
        if phone:
            phone_numbers.add(phone)

    # Save orders data as JSON
    new_orders_file = os.path.join(DATA_FOLDER, f"new_orders_{today_csv_date}_run{run_number}.json")
    save_json(new_orders_file, orders_data)

    # Save VDL data as CSV
    vdl_file = os.path.join(DATA_FOLDER, f"vdl_export_{today_csv_date}_run{run_number}.csv")
    vdl_columns = [
        "DATE [dd/mm/yyyy]", "PRODUCT", "UNIT PRICE", "NAME OF CUSTOMER",
        "REGION", "LOCATION OF CUSTOMER", "PHONE NUMBER",
        "QUANTITY OF PRODUCTS ORDERED", "COMMENT"
    ]
    append_to_csv(vdl_file, vdl_data, vdl_columns)

    # Update emails and phone numbers
    append_to_csv(EMAIL_LIST_FILE, [{"Email": email} for email in emails], ["Email"])
    append_to_csv(PHONE_LIST_FILE, [{"Phone Number": phone} for phone in phone_numbers], ["Phone Number"])

# Main function
if __name__ == "__main__":
    processed_orders = load_processed_orders()
    all_orders = fetch_all_orders_for_today()

    # Save all orders to a JSON file
    save_json(ALL_ORDERS_FILE, all_orders)

    new_orders = [order for order in all_orders if order["id"] not in processed_orders]

    if new_orders:
        print(f"Fetched {len(new_orders)} new orders for today.")
        processed_orders.update(order["id"] for order in new_orders)

        # Determine the run number for the current session
        run_number = len([f for f in os.listdir(DATA_FOLDER) if f.startswith(f"new_orders_{today_csv_date}_run")]) + 1

        # Process new orders
        process_orders(new_orders, run_number)

        # Save new orders to a JSON file
        save_processed_orders(processed_orders)
    else:
        print("No new orders found.")