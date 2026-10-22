"""Step 2: a Flask app that reads the database and serves a dashboard.

Run:  python app.py      then open http://127.0.0.1:5000
"""
import sqlite3

import pandas as pd
from flask import Flask, jsonify, render_template

app = Flask(__name__)
DB = "telecom.db"
INACTIVE_DAYS = 30  # "at risk" = no calls for this many days


def query(sql):
    """Run a SQL query and return the result as a pandas DataFrame (a table in Python)."""
    with sqlite3.connect(DB) as conn:
        return pd.read_sql_query(sql, conn)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/dashboard")
def dashboard():
    # --- SQL does the heavy lifting: filtering, grouping, joining -------------

    kpis = query("""
        SELECT COUNT(DISTINCT customer_id) AS active_customers,
               COUNT(*)                    AS total_calls,
               ROUND(SUM(duration_sec) / 60.0) AS total_minutes,
               ROUND(SUM(cost_da))         AS revenue_da
        FROM calls
    """).iloc[0]

    # Calls per hour of day (strftime pulls the hour out of the timestamp)
    hourly = query("""
        SELECT CAST(strftime('%H', start_time) AS INTEGER) AS hour,
               COUNT(*) AS calls
        FROM calls
        GROUP BY hour
        ORDER BY hour
    """)

    # JOIN calls to customers, then GROUP BY plan
    by_plan = query("""
        SELECT c.plan, ROUND(SUM(k.cost_da)) AS revenue_da
        FROM calls k
        JOIN customers c ON c.id = k.customer_id
        GROUP BY c.plan
        ORDER BY revenue_da DESC
    """)

    top_customers = query("""
        SELECT c.name, c.wilaya, c.plan,
               COUNT(*) AS calls,
               ROUND(SUM(k.cost_da)) AS spend_da
        FROM calls k
        JOIN customers c ON c.id = k.customer_id
        GROUP BY c.id
        ORDER BY spend_da DESC
        LIMIT 10
    """)

    # --- pandas does the analysis that is awkward in SQL: churn risk ----------

    customers = query("SELECT id, name, wilaya, plan FROM customers")
    last_call = query("SELECT customer_id, MAX(start_time) AS last_call FROM calls GROUP BY customer_id")

    df = customers.merge(last_call, left_on="id", right_on="customer_id", how="left")
    df["last_call"] = pd.to_datetime(df["last_call"])
    df["days_inactive"] = (pd.Timestamp.now() - df["last_call"]).dt.days
    df["days_inactive"] = df["days_inactive"].fillna(999).astype(int)  # never called

    at_risk = df[df["days_inactive"] > INACTIVE_DAYS].sort_values("days_inactive", ascending=False)
    churn_rate = round(len(at_risk) / len(df) * 100, 1)

    return jsonify(
        kpis={
            "active_customers": int(kpis["active_customers"]),
            "total_calls": int(kpis["total_calls"]),
            "total_minutes": int(kpis["total_minutes"]),
            "revenue_da": int(kpis["revenue_da"]),
            "churn_rate": churn_rate,
        },
        hourly=hourly.to_dict(orient="records"),
        by_plan=by_plan.to_dict(orient="records"),
        top_customers=top_customers.to_dict(orient="records"),
        at_risk=at_risk[["name", "wilaya", "plan", "days_inactive"]].head(10).to_dict(orient="records"),
        inactive_days=INACTIVE_DAYS,
    )


if __name__ == "__main__":
    app.run(debug=True)
