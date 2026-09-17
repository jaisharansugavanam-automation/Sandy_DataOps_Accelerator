import os
import sys
import pandas as pd
import snowflake.connector
from utils.snowflake_utils import connect_to_snowflake, validate_csv

# ==========================================
# CONFIGURATION / INPUT PARAMETERS
# ==========================================
CSV_FILE_PATH = "data/raw_transactions.csv"  # Local CSV file path
TARGET_DATABASE = os.getenv("SNOWFLAKE_DATABASE", "INTERN_DB")
TARGET_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
TARGET_TABLE = "RAW_SOURCE_TRANSACTIONS"            # Snowflake Target Table
STAGE_NAME = "RAW_STAGE"                         # Internal Stage Name










def upload_csv_to_stage(conn, file_path, stage_name):
    """Creates internal stage if not existing and uploads CSV using PUT."""
    cursor = conn.cursor()
    print(f"[3/6] Setting up Stage '@{stage_name}' & uploading file...")
    try:
        cursor.execute(f"CREATE STAGE IF NOT EXISTS {stage_name};")
        
        # Windows path fix for Snowflake PUT syntax
        formatted_file_path = file_path.replace("\\", "/")
        put_query = f"PUT file://{formatted_file_path} @{stage_name} OVERWRITE = TRUE;"
        
        cursor.execute(put_query)
        print("  --> [PASS] CSV uploaded successfully to internal stage!")
    except Exception as e:
        print(f"  --> [FAIL] Upload to Stage Failed: {e}")
        conn.close()
        sys.exit(1)


def execute_copy_into(conn, stage_name, file_path, target_table):
    """Executes Snowflake COPY INTO statement."""
    cursor = conn.cursor()
    file_name = os.path.basename(file_path)
    print(f"[4/6] Executing COPY INTO for table: {target_table}...")
    
    copy_query = f"""
    COPY INTO {TARGET_DATABASE}.{TARGET_SCHEMA}.{target_table}
    FROM @{stage_name}/{file_name}
    FILE_FORMAT = (
        TYPE = CSV
        SKIP_HEADER = 1
        FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    )
    ON_ERROR = 'ABORT_STATEMENT';
    """
    
    try:
        cursor.execute(copy_query)
        results = cursor.fetchall()
        rows_loaded = results[0][3] if results else 0
        status = results[0][1] if results else "UNKNOWN"
        
        print(f"  --> [PASS] COPY INTO executed. Status: {status}")
        return rows_loaded
    except Exception as e:
        print(f"  --> [FAIL] COPY INTO failed: {e}")
        conn.close()
        sys.exit(1)


def validate_load(conn, target_table, local_row_count, rows_loaded):
    """Validates database row count against local CSV row count."""
    cursor = conn.cursor()
    print("[5/6] Validating load record counts...")
    
    cursor.execute(f"SELECT COUNT(*) FROM {target_table};")
    sf_table_count = cursor.fetchone()[0]
    
    print(f"  --> Local CSV Row Count    : {local_row_count}")
    print(f"  --> Rows Loaded in Batch   : {rows_loaded}")
    print(f"  --> Total Table Row Count  : {sf_table_count}")
    
    if local_row_count == rows_loaded:
        validation_status = "PASS"
        print("  --> [PASS] Batch Record Count matches CSV exactly!")
    else:
        validation_status = "WARNING"
        print("  --> [WARNING] Mismatch between CSV rows and loaded rows.")
        
    return validation_status, sf_table_count


def print_summary(target_table, local_rows, rows_loaded, total_sf_rows, status):
    """Prints a formatted execution summary report."""
    print("\n==================================================")
    print("           DATA INGESTION LOAD SUMMARY            ")
    print("==================================================")
    print(f" Target Table          : {target_table}")
    print(f" Local CSV Record Count: {local_rows}")
    print(f" Rows Loaded (COPY)    : {rows_loaded}")
    print(f" Snowflake Total Rows  : {total_sf_rows}")
    print(f" Load Validation Status: {status}")
    print("==================================================")


def main():
    conn = connect_to_snowflake()
    try:
        local_row_count = validate_csv(CSV_FILE_PATH)
        upload_csv_to_stage(conn, CSV_FILE_PATH, STAGE_NAME)
        rows_loaded = execute_copy_into(conn, STAGE_NAME, CSV_FILE_PATH, TARGET_TABLE)
        status, total_sf_rows = validate_load(conn, TARGET_TABLE, local_row_count, rows_loaded)
        print_summary(TARGET_TABLE, local_row_count, rows_loaded, total_sf_rows, status)
    finally:
        conn.close()
        print("\nSnowflake Connection Closed.")


if __name__ == "__main__":
    main()
    