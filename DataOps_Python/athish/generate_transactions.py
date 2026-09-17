import csv
import random
from datetime import datetime, timedelta

def generate_random_date(start_date_str="2024-07-01"):
    """Generates a random date from July 1, 2024, up to today."""
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.now()
    
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    
    random_number_of_days = random.randint(0, days_between_dates)
    random_date = start_date + timedelta(days=random_number_of_days)
    
    return random_date.strftime("%Y-%m-%d")


def generate_transactions(num_records=1000, output_file="data/raw_transactions.csv"):
    """
    Generates mock transaction records based on specification rules
    and exports them to a CSV file.
    """
    print(f"[1/3] Generating {num_records} synthetic transaction records...")

    # Fixed ID Ranges & Values
    PYRAID_RANGE = (100001, 100100)
    PYEAID_RANGE = (200001, 200100)
    TRNAMT_RANGE = (500, 15000)
    TRANSACTION_TYPES = ["INFLOW", "OUTFLOW"]
    
    # Generate unique OTRN_IDs
    START_OTRN_ID = 3000001
    
    fieldnames = [
        "OTRN_ID",
        "OTRN_PYRAID",
        "OTRN_PYEAID",
        "OTRN_TRNTYP",
        "OTRN_TRNAMT",
        "OTRN_TRNDAT"
    ]
    
    records = []
    
    for i in range(num_records):
        record = {
            "OTRN_ID": START_OTRN_ID + i,  # Ensures 100% uniqueness
            "OTRN_PYRAID": random.randint(*PYRAID_RANGE),
            "OTRN_PYEAID": random.randint(*PYEAID_RANGE),
            "OTRN_TRNTYP": random.choice(TRANSACTION_TYPES),
            "OTRN_TRNAMT": round(random.uniform(*TRNAMT_RANGE), 2),
            "OTRN_TRNDAT": generate_random_date("2024-07-01")
        }
        records.append(record)

    print(f"[2/3] Writing generated data to '{output_file}'...")
    
    # Export to CSV
    with open(output_file, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"  --> [PASS] File saved successfully at '{output_file}'!")
    return output_file


if __name__ == "__main__":
    # Generate 1,000 records by default
    generate_transactions(num_records=1000)