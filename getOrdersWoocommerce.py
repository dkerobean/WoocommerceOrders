import os
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
    except Exception as e:
        print(f"An error occurred: {e}")


# Call the function and print the orders
if __name__ == "__main__":
    orders = fetch_orders_for_today()
    if orders:
        print(f"Orders for {today}:")
        for order in orders:
            print(f"Order ID: {order['id']}, Total: {order['total']}, Status: {order['status']}")
