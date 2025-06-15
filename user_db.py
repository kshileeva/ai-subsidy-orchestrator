import sqlite3
import json
from tabulate import tabulate
from datetime import datetime

# Step 1: Load data from user_input.json
with open("user_input.json", "r", encoding="utf-8") as file:
    data = json.load(file)

# Step 2: Connect to SQLite DB
conn = sqlite3.connect("subsidy_applications.db")
cursor = conn.cursor()

# Step 3: Create table with new columns for number of children and ages of children
cursor.execute("""
               CREATE TABLE IF NOT EXISTS applications
               (
                   application_nr
                   TEXT,
                   date
                   TEXT,
                   user_name
                   TEXT,
                   employment_status
                   TEXT,
                   household_income
                   INTEGER,
                   childcare_hours
                   INTEGER,
                   num_children
                   INTEGER,
                   ages_of_children
                   TEXT,
                   history
                   TEXT,
                   application_status
                   TEXT
               )
               """)

# Step 4: Insert each record
today = datetime.today().strftime("%Y-%m-%d")

for entry in data:
    application_nr = entry.get("application_id", "N/A")
    user_name = entry.get("applicant_name", "N/A")
    employment_status = entry.get("employment_status", "N/A")
    household_income = entry.get("household_income", 0)
    childcare_hours = entry.get("childcare_hours_requested", entry.get("requested_hours", 0))

    num_children = entry.get("num_children", 0)
    child_ages_list = entry.get("child_ages", [])
    # Convert list of ages to comma-separated string
    ages_of_children = ",".join(str(age) for age in child_ages_list)

    history = ""  # Leave blank for now
    application_status = "Pending"  # Default status

    cursor.execute("""
                   INSERT INTO applications (application_nr, date, user_name,
                                             employment_status, household_income,
                                             childcare_hours, num_children, ages_of_children,
                                             history, application_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   """, (
                       application_nr, today, user_name,
                       employment_status, household_income,
                       childcare_hours, num_children, ages_of_children,
                       history, application_status
                   ))

# Step 5: Print all records
conn.commit()
cursor.execute("SELECT * FROM applications")
rows = cursor.fetchall()

print(tabulate(
    rows,
    headers=[
        "Application Nr", "Date", "User Name",
        "Employment", "Income", "Hours",
        "Num Children", "Ages of Children",
        "History", "Status"
    ],
    tablefmt="grid"
))

conn.close()
