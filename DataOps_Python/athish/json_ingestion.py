import os
import sys
import json
import snowflake.connector
from utils.snowflake_utils import connect_to_snowflake, validate_file_exists

# ==========================================
# CONFIGURATION
# ==========================================
JSON_FILE_PATH = "data/sample_run_log.json"
TARGET_DATABASE = os.getenv("SNOWFLAKE_DATABASE", "INTERN_DB")
TARGET_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
TARGET_TABLE = "TEST_RUN_LOG"
STAGE_NAME = "JSON_STAGE"
FILE_FORMAT_NAME = "JSON_FILE_FORMAT"

# Snowflake Credentials
SF_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT", "lveaxvw-wl87224")
SF_USER = os.getenv("SNOWFLAKE_USER", "athishdata2026")
SF_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD", "SnowflakeIntern2026!")
SF_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
SF_ROLE = os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN")







def upload_json_to_stage(conn, file_path, stage_name):
    """Uploads JSON file to internal Snowflake stage using PUT."""
    cursor = conn.cursor()
    print(f"[3/6] Uploading JSON to Stage '@{stage_name}'...")
    try:
        formatted_path = file_path.replace("\\", "/")
        put_query = f"PUT file://{formatted_path} @{stage_name} OVERWRITE = TRUE;"
        cursor.execute(put_query)
        print("  --> [PASS] JSON file staged successfully!")
    except Exception as e:
        print(f"  --> [FAIL] Stage upload failed: {e}")
        conn.close()
        sys.exit(1)


def execute_json_copy_into(conn, file_path, stage_name, target_table, file_format):
    """Executes COPY INTO command loading JSON payload into VARIANT column."""
    cursor = conn.cursor()
    file_name = os.path.basename(file_path)
    print(f"[4/6] Ingesting JSON into VARIANT table '{target_table}'...")

    copy_query = f"""
    COPY INTO {TARGET_DATABASE}.{TARGET_SCHEMA}.{target_table} (PAYLOAD)
    FROM @{stage_name}/{file_name}
    FILE_FORMAT = (FORMAT_NAME = '{file_format}')
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
        print(f"  --> [FAIL] Ingestion failed: {e}")
        conn.close()
        sys.exit(1)


def validate_load(conn, target_table, expected_records, rows_loaded):
    """Validates records ingested into the target table."""
    cursor = conn.cursor()
    print("[5/6] Validating load record counts...")
    
    cursor.execute(f"SELECT COUNT(*) FROM {target_table};")
    total_table_count = cursor.fetchone()[0]
    
    print(f"  --> Expected Records : {expected_records}")
    print(f"  --> Rows Loaded      : {rows_loaded}")
    print(f"  --> Total Table Rows : {total_table_count}")
    
    if expected_records == rows_loaded:
        return "SUCCESS", total_table_count
    return "WARNING", total_table_count


def main():
    print("==========================================")
    print("     JSON SNOWFLAKE INGESTION ENGINE     ")
    print("==========================================")
    
    # 1. Validate Local JSON
    json_data, expected_count, run_id = validate_json(JSON_FILE_PATH)
    
    # 2. Connect
    conn = connect_to_snowflake()
    
    try:
        # 3. Upload to Stage
        upload_json_to_stage(conn, JSON_FILE_PATH, STAGE_NAME)
        
        # 4. Copy Into Variant Column
        rows_loaded = execute_json_copy_into(
            conn, JSON_FILE_PATH, STAGE_NAME, TARGET_TABLE, FILE_FORMAT_NAME
        )
        
        # 5. Validate Load
        status, total_count = validate_load(conn, TARGET_TABLE, expected_count, rows_loaded)
        
        # 6. Summary Report
        print("\n==========================================")
        print("          INGESTION LOAD SUMMARY          ")
        print("==========================================")
        print(f" Run ID       : {run_id}")
        print(f" Target Table : {TARGET_TABLE}")
        print(f" Records      : {rows_loaded}")
        print(f" Status       : {status}")
        print("==========================================")
        
    finally:
        conn.close()
        print("\nSnowflake connection closed.")


if __name__ == "__main__":
    main()