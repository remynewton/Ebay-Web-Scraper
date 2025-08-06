# 🛍️ Ebay Product Price Tracker

A lightweight Python tool to track product prices on eBay and plot historical price trends.

## 🔧 Features

- Scrapes eBay for latest product listings and prices
- Tracks price changes over time
- Outputs results to CSV
- Generates historical price plots for specific keywords

Here is an example results.csv:
<img width="755" height="249" alt="Screenshot 2025-08-05 193203" src="https://github.com/user-attachments/assets/62f68a66-f131-494f-9ef8-a749b01b2335" />

---

📈 Usage
✅ 1. Tracking Prices
Specify your product list in your_products.csv and run:
```
python price_tracker.py --input your_products.csv --historical-output results.csv --limit 5
```
This scrapes the top N (--limit) listings for each product and saves results to results.csv.

<img width="1678" height="313" alt="Screenshot 2025-08-05 191111" src="https://github.com/user-attachments/assets/1b187d44-bde2-4182-bb69-3122c63dd97d" />

📊 2. Plotting Price History
To plot the price history of a specific product:
```
python price_tracker.py --mode plot --output_file plot.csv --plot_keyword "air max"
```
Generates a scatter plot of all historical prices for matching products.

<img width="1426" height="801" alt="Screenshot 2025-08-05 191028" src="https://github.com/user-attachments/assets/a52a2fc7-f90b-44a6-ab3e-ededf23a732a" />
