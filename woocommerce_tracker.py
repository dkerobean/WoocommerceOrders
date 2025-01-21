import os
import json
import csv
from woocommerce import API
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, List, Set
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('woocommerce_tracker.log'),
        logging.StreamHandler()
    ]
)

class WooCommerceTracker:
    def __init__(self):
        # Load environment variables
        load_dotenv()

        # Constants and configurations
        self.STORE_URL = os.getenv("WOOCOMMERCE_STORE_URL")
        self.CONSUMER_KEY = os.getenv("WOOCOMMERCE_CONSUMER_KEY")
        self.CONSUMER_SECRET = os.getenv("WOOCOMMERCE_CONSUMER_SECRET")

        # File paths
        self.DATA_DIR = Path("data")
        self.DATA_DIR.mkdir(exist_ok=True)

        self.PROCESSED_ORDERS_FILE = self.DATA_DIR / "processed_orders.json"
        self.CUSTOMERS_FILE = self.DATA_DIR / "customers_database.json"

        # Initialize WooCommerce API client
        self.wcapi = self._initialize_api()

        # Load existing data
        self.processed_orders = self._load_json_file(self.PROCESSED_ORDERS_FILE, set)
        self.customers_database = self._load_json_file(self.CUSTOMERS_FILE, dict)

        # Get current date
        self.today = datetime.now()
        self.today_str = self.today.strftime("%Y-%m-%d")
        self.today_file_str = self.today.strftime("%d-%m-%Y")

    def _initialize_api(self) -> API:
        """Initialize WooCommerce API client with error handling"""
        try:
            return API(
                url=self.STORE_URL,
                consumer_key=self.CONSUMER_KEY,
                consumer_secret=self.CONSUMER_SECRET,
                version="wc/v3",
                timeout=20
            )
        except Exception as e:
            logging.error(f"Failed to initialize WooCommerce API: {e}")
            raise

    def _load_json_file(self, filepath: Path, default_type) -> any:
        """Load JSON file with error handling"""
        try:
            if filepath.exists():
                with open(filepath, "r") as file:
                    data = json.load(file)
                    return set(data) if default_type == set else data
            return default_type()
        except Exception as e:
            logging.error(f"Error loading {filepath}: {e}")
            return default_type()

    def _save_json_file(self, data: any, filepath: Path, indent: int = 4) -> None:
        """Save data to JSON file with error handling"""
        try:
            with open(filepath, "w") as file:
                if isinstance(data, set):
                    data = list(data)
                json.dump(data, file, indent=indent)
        except Exception as e:
            logging.error(f"Error saving to {filepath}: {e}")

    def update_customer_database(self, order: Dict) -> None:
        """Update customer database with new information"""
        customer_id = str(order['customer_id'])
        billing = order['billing']

        customer_data = {
            'email': billing.get('email', ''),
            'phone': billing.get('phone', ''),
            'first_name': billing.get('first_name', ''),
            'last_name': billing.get('last_name', ''),
            'address': billing.get('address_1', ''),
            'city': billing.get('city', ''),
            'last_order_date': self.today_str,
            'total_orders': self.customers_database.get(customer_id, {}).get('total_orders', 0) + 1
        }

        self.customers_database[customer_id] = customer_data

    def fetch_orders(self) -> List[Dict]:
        """Fetch all orders for today with pagination"""
        all_orders = []
        page = 1

        while True:
            try:
                response = self.wcapi.get("orders", params={
                    "date_created": self.today_str,
                    "per_page": 100,
                    "page": page
                })

                if response.status_code != 200:
                    logging.error(f"Error fetching orders: {response.status_code}")
                    break

                orders = response.json()
                if not orders:
                    break

                all_orders.extend(orders)
                page += 1

            except Exception as e:
                logging.error(f"Error fetching orders page {page}: {e}")
                break

        return all_orders

    def save_orders_report(self, orders: List[Dict], run_number: int) -> None:
        """Save formatted orders report"""
        file_name = self.DATA_DIR / f"new_orders_{self.today_file_str}_run{run_number}.json"

        formatted_orders = [
            {
                "location": order['billing']['address_1'],
                "product": ", ".join([item['name'] for item in order['line_items']]),
                "phone_number": order['billing']['phone'],
                "email": order['billing']['email'],
                "customer_name": f"{order['billing']['first_name']} {order['billing']['last_name']}"
            }
            for order in orders
        ]

        self._save_json_file(formatted_orders, file_name)
        logging.info(f"New orders saved to {file_name}")

    def export_customer_contacts(self) -> None:
        """Export customer contacts to CSV"""
        csv_file = self.DATA_DIR / f"customer_contacts_{self.today_file_str}.csv"

        try:
            with open(csv_file, 'w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=[
                    'customer_id', 'first_name', 'last_name', 'email',
                    'phone', 'address', 'city', 'total_orders', 'last_order_date'
                ])

                writer.writeheader()
                for customer_id, data in self.customers_database.items():
                    row = {'customer_id': customer_id, **data}
                    writer.writerow(row)

            logging.info(f"Customer contacts exported to {csv_file}")
        except Exception as e:
            logging.error(f"Error exporting customer contacts: {e}")

    def run(self) -> None:
        """Main execution method"""
        try:
            # Fetch and process orders
            all_orders = self.fetch_orders()
            new_orders = [order for order in all_orders if order['id'] not in self.processed_orders]

            if not new_orders:
                logging.info("No new orders found.")
                return

            logging.info(f"Fetched {len(new_orders)} new orders for today.")

            # Update processed orders and customer database
            for order in new_orders:
                self.processed_orders.add(order['id'])
                self.update_customer_database(order)

            # Determine run number for this batch
            existing_files = list(self.DATA_DIR.glob(f"new_orders_{self.today_file_str}*.json"))
            run_number = len(existing_files) + 1

            # Save all updates
            self.save_orders_report(new_orders, run_number)
            self._save_json_file(self.processed_orders, self.PROCESSED_ORDERS_FILE)
            self._save_json_file(self.customers_database, self.CUSTOMERS_FILE)
            self.export_customer_contacts()

        except Exception as e:
            logging.error(f"Error in main execution: {e}")

if __name__ == "__main__":
    tracker = WooCommerceTracker()
    tracker.run()