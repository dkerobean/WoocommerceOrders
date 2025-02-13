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
    new_orders_data = []

    for index, order in enumerate(new_orders, start=1):
        email = order["billing"]["email"]
        phone = format_ghanaian_phone(order["billing"]["phone"])
        location = order["billing"]["address_1"]
        date = datetime.strptime(order["date_created"], "%Y-%m-%dT%H:%M:%S").strftime("%d/%m/%Y")
        products = ", ".join([item["name"] for item in order["line_items"]])
        unit_price = sum(float(item["price"]) for item in order["line_items"])
        delivery_fee = 0  # Default, update if necessary
        net_amount = unit_price
        status = "Not started"
        created_by = "dickson"

        new_orders_data.append({
            "Count": index,
            "Phone": phone,
            "Location": location,
            "Product": products,
            "Price (cedis)": unit_price,
            "Delivery fee": delivery_fee,
            "Net Amount": net_amount,
            "Date": date,
            "Status": status,
            "Created by": created_by
        })

        if email:
            emails.add(email)
        if phone:
            phone_numbers.add(phone)

    # Save new orders as CSV
    new_orders_file = os.path.join(DATA_FOLDER, f"new_orders_{today_csv_date}_run{run_number}.csv")
    new_orders_columns = [
        "Count", "Phone", "Location", "Product", "Price (cedis)", "Delivery fee", "Net Amount", "Date", "Status", "Created by"
    ]
    append_to_csv(new_orders_file, new_orders_data, new_orders_columns)

    # Update emails and phone numbers
    append_to_csv(EMAIL_LIST_FILE, [{"Email": email} for email in emails], ["Email"])
    append_to_csv(PHONE_LIST_FILE, [{"Phone Number": phone} for phone in phone_numbers], ["Phone Number"])

# Main function
if __name__ == "__main__":
    processed_orders = load_processed_orders()
    all_orders = fetch_all_orders_for_today()

    new_orders = [order for order in all_orders if order["id"] not in processed_orders]

    if new_orders:
        print(f"Fetched {len(new_orders)} new orders for today.")
        processed_orders.update(order["id"] for order in new_orders)

        run_number = len([f for f in os.listdir(DATA_FOLDER) if f.startswith(f"new_orders_{today_csv_date}_run")]) + 1
        process_orders(new_orders, run_number)
        save_processed_orders(processed_orders)
    else:
        print("No new orders found.")
