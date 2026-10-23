# Restaurant Order Management System (Flask + SQLite)

## Included
- Table/flexible tab view and open orders per table
- Product menu with category and price
- Add products and quantities to a table order
- Separate Kitchen and Bar tickets based on product category
- Browser print button for kitchen, bar, and customer tickets
- Close orders and simple closed-order sales report
- Manage menu items and tables
- SQLite database stored locally in `restaurant.db`

## Run on Windows
1. Install Python 3.10 or newer from https://www.python.org/downloads/
2. Extract this ZIP to a folder.
3. Open Command Prompt in that folder.
4. Run:
   ```bat
   py -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   py app.py
   ```
5. On the same computer open http://127.0.0.1:5000

## Test on a phone on the same Wi-Fi
1. Connect the phone and computer to the same Wi-Fi network.
2. On Windows, run `ipconfig` and find the computer's IPv4 Address (example `192.168.1.25`).
3. On the phone browser, open `http://COMPUTER-IP:5000`, for example `http://192.168.1.25:5000`.
4. If it does not open, allow Python through Windows Firewall on Private networks.

## Printer routing
The app separates tickets by category:
- Categories `Drink`, `Drinks`, `Beverage`, `Beverages`, or `Bar` go to the Bar ticket.
- All other categories go to the Kitchen ticket.
- On an order screen, press **Send new items to Kitchen** and **Send new drinks to Bar**. This marks items sent and opens the relevant ticket page for printing.
- The print action uses the browser's print dialog. Select the correct printer there.

## Important limitations / next production steps
This is a local MVP, not a cloud multi-user POS yet. It does not automatically print silently to a specific printer. For automatic printing to separate physical printers, install a local print bridge/service (for example QZ Tray) or implement a dedicated print agent on the POS computer and configure kitchen/bar printer names. For multiple devices outside the same Wi-Fi, deploy behind HTTPS to a server and use a production database such as PostgreSQL. Add authentication, backups, permissions, and tax/payment integrations before real commercial use.
