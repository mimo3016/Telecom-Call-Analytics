"""Step 1: create a fake telecom database (SQLite) with customers and calls.

Run once:  python generate_data.py
SQLite is built into Python, so there is nothing to install or set up.
"""
import random
import sqlite3
from datetime import datetime, timedelta

random.seed(42)
DB = "telecom.db"
DAYS = 90
NUM_CUSTOMERS = 500

FIRST = ["Amine", "Yacine", "Sara", "Lina", "Karim", "Nour", "Rania", "Sofiane", "Imane", "Walid", "Meriem", "Adel"]
LAST = ["Benali", "Khelifi", "Messaoud", "Bouzid", "Haddad", "Saidi", "Brahimi", "Cherif", "Mansouri", "Zerrouki"]
WILAYAS = ["Algiers", "Oran", "Constantine", "Annaba", "Blida", "Setif"]
PLANS = {"Basic": 3.0, "Standard": 2.5, "Premium": 2.0}  # price per minute in DA

# Weight for each hour 0-23: lunch peak and an evening peak
HOUR_WEIGHTS = [1, 1, 1, 1, 1, 2, 3, 5, 7, 8, 8, 9, 11, 11, 9, 8, 8, 9, 10, 12, 13, 12, 8, 3]

schema = """
DROP TABLE IF EXISTS calls;
DROP TABLE IF EXISTS customers;
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    wilaya TEXT NOT NULL,
    plan TEXT NOT NULL
);
CREATE TABLE calls (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    start_time TEXT NOT NULL,      -- 'YYYY-MM-DD HH:MM:SS'
    duration_sec INTEGER NOT NULL,
    cost_da REAL NOT NULL
);
CREATE INDEX idx_calls_customer ON calls(customer_id);
CREATE INDEX idx_calls_start ON calls(start_time);
"""

now = datetime.now().replace(minute=0, second=0, microsecond=0)
conn = sqlite3.connect(DB)
conn.executescript(schema)

customers, calls = [], []
for cid in range(1, NUM_CUSTOMERS + 1):
    plan = random.choice(list(PLANS))
    customers.append((cid, f"{random.choice(FIRST)} {random.choice(LAST)}", random.choice(WILAYAS), plan))

    activity = random.uniform(0.3, 4)  # average calls per day for this customer
    # ~15% of customers "churn": they stop calling at some point
    churn_day = random.randint(10, 70) if random.random() < 0.15 else DAYS + 1

    for day in range(min(churn_day, DAYS)):
        n_calls = sum(random.random() < activity / 5 for _ in range(5))
        for _ in range(n_calls):
            hour = random.choices(range(24), weights=HOUR_WEIGHTS)[0]
            start = now - timedelta(days=DAYS - day) + timedelta(
                hours=hour - now.hour, minutes=random.randint(0, 59), seconds=random.randint(0, 59))
            duration = int(random.lognormvariate(4.8, 0.9))  # seconds, mostly 1-4 minutes
            cost = round(duration / 60 * PLANS[plan], 2)
            calls.append((cid, start.strftime("%Y-%m-%d %H:%M:%S"), duration, cost))

conn.executemany("INSERT INTO customers VALUES (?, ?, ?, ?)", customers)
conn.executemany("INSERT INTO calls (customer_id, start_time, duration_sec, cost_da) VALUES (?, ?, ?, ?)", calls)
conn.commit()
conn.close()
print(f"Created {DB}: {len(customers)} customers, {len(calls)} calls")
