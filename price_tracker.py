# Real-Time Product Tracker - A portfolio project showcasing advanced scraping.
import argparse, re, time, random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import quote_plus
import matplotlib.pyplot as plt

import pandas as pd
from bs4 import BeautifulSoup

# ---- Selenium/UC (guarded) ----
try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SEL_OK = True
    try: setattr(uc.Chrome, "__del__", lambda self: None)
    except Exception: pass
except Exception:
    SEL_OK = False
    uc = By = WebDriverWait = EC = TimeoutException = WebDriverException = None
    print("[WARN] Selenium and undetected_chromedriver not found. Web scraping functionality is disabled.")

# Base URL for the e-commerce site (eBay)
PRODUCT_URL_TEMPLATE = "https://www.ebay.com/sch/i.html?_nkw={query}"

@dataclass
class ProductData:
    product_name: str
    is_found: bool = False
    timestamp: str = time.strftime("%Y-%m-%d %H:%M:%S")
    product_url: Optional[str] = None
    status: str = "ok"
    notes: Optional[str] = None
    price: Optional[str] = None

    def row(self) -> Dict[str, Any]:
        return {
            "product_name": self.product_name,
            "is_found": self.is_found,
            "timestamp": self.timestamp,
            "product_url": self.product_url,
            "status": self.status,
            "notes": self.notes,
            "price": self.price
        }

def get_products_to_track(file_path: Path) -> Optional[pd.DataFrame]:
    """Reads product queries from a CSV file, accepting only a 'product' column name."""
    if not file_path.exists():
        print(f"[ERROR] Product configuration file not found at: {file_path}")
        return None
    try:
        df = pd.read_csv(file_path)
        # Check for 'product' column only
        if 'product' in df.columns:
            df.rename(columns={'product': 'product_query'}, inplace=True)
            print("[INFO] Using column 'product' as the product query source.")
        else:
            print("[ERROR] CSV file must contain a column named 'product'.")
            return None
        return df
    except Exception as e:
        print(f"[ERROR] Could not read CSV file: {e}")
        return None

def save_historical_data(file_path: Path, df: pd.DataFrame):
    """Saves the DataFrame to a CSV file."""
    try:
        df.to_csv(file_path, index=False)
        print(f"[INFO] Historical data saved to '{file_path}'.")
    except Exception as e:
        print(f"[ERROR] Could not save data to CSV: {e}")

def check_product_existence(dr: uc.Chrome, product_query: str) -> ProductData:
    import time
    if not dr:
        return ProductData(product_query, status="error", notes="WebDriver not initialized.")

    encoded_query = quote_plus(product_query)
    search_url = PRODUCT_URL_TEMPLATE.format(query=encoded_query) + "&_sop=15"

    try:
        dr.get(search_url)

        # Wait for main content to load
        WebDriverWait(dr, 15).until(
            EC.presence_of_element_located((By.ID, "srp-river-results"))
        )
        time.sleep(2)

        soup = BeautifulSoup(dr.page_source, 'html.parser')
        product_cards = soup.find_all('li', class_=re.compile(r'\bs-card\b'))

        for card in product_cards:
            # Skip auction listings
            attributes = card.find('div', class_='su-card-container__attributes')
            if attributes and 'bid' in attributes.get_text(strip=True).lower():
                continue

            # Extract price robustly
            price_spans = card.find_all('span', class_='s-card__price')
            price = None
            for p in price_spans:
                text = p.get_text(strip=True)
                if text and "$" in text and "bid" not in text.lower():
                    price = text
                    break
            if not price:
                continue  # skip if no valid price

            # Extract title
            title_div = card.find('div', class_='s-card__title')
            product_name = title_div.get_text(strip=True) if title_div else "Unknown Product"

            # Extract product link
            link = card.find('a', class_='image-treatment')
            product_url = link['href'] if link else None

            return ProductData(
                product_name=product_name,
                is_found=True,
                product_url=product_url,
                notes=f"Product found. Price: {price}",
                price=price
            )

        return ProductData(product_query, is_found=False, notes="Only auctions or no valid listings found.")

    except TimeoutException:
        return ProductData(product_query, is_found=False, notes="Timeout waiting for elements.")
    except Exception as e:
        return ProductData(product_query, is_found=False, notes=f"Error: {str(e)}")

def plot_price_history(master_file: str, keyword: str, output_file: str):
    """Filter master data by keyword, save to output file, and plot price history."""
    
    master_path = Path(master_file)
    output_path = Path(output_file)

    # Step 1: Load the master CSV
    if not master_path.exists():
        print(f"[plot] Master file '{master_file}' not found. Nothing to plot.")
        return

    df = pd.read_csv(master_path)
    if df.empty:
        print(f"[plot] Master file '{master_file}' is empty.")
        return

    # Step 2: Clean data
    df['price_clean'] = df['price'].apply(lambda x: float(re.sub(r'[^\d.]', '', str(x))) if pd.notnull(x) else None)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Step 3: Filter by keyword
    mask = df['product_name'].str.contains(keyword, case=False, na=False)
    df_filtered = df[mask].sort_values('timestamp')

    if df_filtered.empty:
        print(f"[plot] No matching product found for keyword: '{keyword}'")
        return

    # Step 4: Save filtered data to output_file
    df_filtered.to_csv(output_path, index=False)
    print(f"[plot] Filtered data saved to '{output_file}'.")

    # Step 5: Plot
    plt.figure(figsize=(10, 5))
    plt.plot(df_filtered['timestamp'], df_filtered['price_clean'], marker='o', linestyle='-')
    plt.title(f"Price History: {keyword}")
    plt.xlabel("Timestamp")
    plt.ylabel("Price (USD)")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def main(args: argparse.Namespace):
    """Main function to run the product tracker."""
    print(f"[main] Initializing product tracker at {time.ctime()}")
    
    # Check if Selenium is available
    if not SEL_OK:
        print("[main] Exiting due to missing Selenium/undetected_chromedriver dependencies.")
        return

    # Load products to track from CSV
    products_df = get_products_to_track(Path(args.products_file))
    if products_df is None or products_df.empty:
        print("[main] No products to track. Please check your input file.")
        return
        
    # Apply limit if specified
    if args.limit and args.limit > 0:
        products_df = products_df.head(args.limit)
        print(f"[main] Limiting processing to the first {args.limit} products.")

    out_file = Path(args.output_file)
    historical_df = pd.DataFrame()
    if out_file.exists():
        try:
            historical_df = pd.read_csv(out_file)
            print(f"[main] Loaded existing historical data from '{out_file}'.")
        except Exception as e:
            print(f"[WARN] Could not read existing historical data: {e}. Starting with a new DataFrame.")
            historical_df = pd.DataFrame()

    dr = None
    try:
        # Initialize the WebDriver
        print("[main] Initializing undetected_chromedriver...")
        options = uc.ChromeOptions()
        if args.headless:
            options.add_argument("--headless")
        dr = uc.Chrome(options=options, use_subprocess=True)
        print("[main] WebDriver initialized successfully.")

        total_to_process = len(products_df)
        delay_value = args.delay if args.delay is not None else random.uniform(float(args.delay_min), float(args.delay_max))

        for i, row in products_df.iterrows():
            product_query = row['product_query']

            print(f"[main] ({i + 1}/{total_to_process}) Checking existence for: '{product_query}'")
            
            result = check_product_existence(dr, product_query)
            
            new_row_df = pd.DataFrame([result.row()])
            historical_df = pd.concat([historical_df, new_row_df], ignore_index=True)
            print(f"[main] Result: {'Found' if result.is_found else 'Not Found'}. Notes: {result.notes}")

            # Save progress after each product
            save_historical_data(out_file, historical_df)
            
            # Apply delay
            print(f"[main] Waiting for {delay_value:.2f} seconds before next check.")
            time.sleep(delay_value)
            
            if args.delay is None:
                delay_value = random.uniform(float(args.delay_min), float(args.delay_max))
        
        print("[main] All products checked. Final save complete.")

    except Exception as e:
        print(f"[main] An error occurred during main execution: {e}")
    finally:
        if dr:
            try: 
                dr.quit()
                print("[main] WebDriver closed.")
            except Exception: 
                pass
        
        # Final save
        save_historical_data(out_file, historical_df)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Real-time product tracker with optional plotting.")

    parser.add_argument("--mode", choices=["track", "plot"], default="track",
                        help="Mode to run: 'track' to scrape prices (default), 'plot' to graph price history.")

    parser.add_argument("--products_file", "--input", type=str, default="your_products.csv",
                        help="Path to the CSV file containing product queries.")
    parser.add_argument("--output_file", "--historical-output", type=str, default="historical_products.csv",
                        help="Path to the CSV file to save historical data.")
    parser.add_argument("--delay", type=float, default=None,
                        help="Delay in seconds between product checks. Overrides --delay_min/--delay_max.")
    parser.add_argument("--delay_min", type=float, default=5,
                        help="Minimum delay in seconds for random delay between checks.")
    parser.add_argument("--delay_max", type=float, default=15,
                        help="Maximum delay in seconds for random delay between checks.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit the number of products to process from the input file.")
    parser.add_argument("--headless", action="store_true",
                        help="Run the browser in headless mode (no visible GUI).")

    parser.add_argument("--plot_keyword", type=str, default=None,
                        help="Keyword to use for plotting if mode is 'plot'.")

    args = parser.parse_args()

    if args.mode == "track":
        main(args)
    elif args.mode == "plot":
        keyword = args.plot_keyword or input("Enter a product keyword to graph its price history: ").strip()
        if keyword:
            plot_price_history("results.csv", keyword, args.output_file)
        else:
            print("[plot] No keyword provided. Exiting.")

