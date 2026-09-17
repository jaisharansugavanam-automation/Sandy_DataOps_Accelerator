import os
import sys
import snowflake.connector
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def connect_to_snowflake():
    """Establishes and returns a connection to Snowflake."""
    try:
        conn = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA"),
            role=os.getenv("SNOWFLAKE_ROLE")
        )
        print(" --> [PASS] Successfully connected to Snowflake.")
        return conn
    except Exception as e:
        print(f" --> [FAIL] Snowflake Connection Error: {e}")
        sys.exit(1)

def validate_file_exists(file_path):
    """Checks if a local source file exists before processing."""
    if not os.path.exists(file_path):
        print(f" --> [FAIL] File does not exist at path: {file_path}")
        sys.exit(1)
    print(f" --> [PASS] Validated file existence: {file_path}")
    return True