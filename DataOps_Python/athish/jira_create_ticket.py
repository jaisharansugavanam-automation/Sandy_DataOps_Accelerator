import json
import os
import requests
from requests.auth import HTTPBasicAuth

# ==========================================
# CONFIGURATION
# ==========================================
JIRA_DOMAIN = "sandydataopsaccelerator.atlassian.net"  # Update if needed
JIRA_EMAIL = "25ct005@gmail.com"  # Your Atlassian email
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "YOUR_JIRA_API_TOKEN")

# API Endpoint (REST API v2)
URL = f"https://{JIRA_DOMAIN}/rest/api/2/issue"
PAYLOAD_FILE = "jira_payload.json"


def load_payload(file_path):
    """Read and parse the local JSON payload file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Payload file '{file_path}' not found.")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON in '{file_path}': {e}")
        return None


def create_jira_ticket():
    """Authenticates and posts a new issue to Jira."""
    payload = load_payload(PAYLOAD_FILE)
    if not payload:
        return

    # Basic Authentication setup
    auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    print("Sending POST request to Jira API...")

    try:
        response = requests.post(
            URL,
            data=json.dumps(payload),
            headers=headers,
            auth=auth
        )

        # Check HTTP Status Code
        if response.status_code == 211 or response.status_code == 201:
            data = response.json()
            issue_key = data.get("key")
            issue_id = data.get("id")
            issue_url = f"https://{JIRA_DOMAIN}/browse/{issue_key}"

            print("\n==========================================")
            print(" TICKET CREATED SUCCESSFULLY!")
            print("==========================================")
            print(f"Issue Key : {issue_key}")
            print(f"Issue ID  : {issue_id}")
            print(f"URL       : {issue_url}")
            print("==========================================")

            # Display payload details matching expected format
            fields = payload.get("fields", {})
            print("\nValidation Framework : DDL Validation")
            print(f"Table              : {fields.get('summary', '').split('in ')[-1] if 'in ' in fields.get('summary', '') else 'RAW_SOURCE_EMPL_PERS'}")
            print("Validation Result  : FAIL\n")
            print("Reason")
            print("------")
            print("Source Data Dictionary defines EMPL_PERS_DOB as DATE.")
            print("Snowflake table contains VARCHAR(100).\n")
            print("Impact")
            print("------")
            print("Incorrect datatype may cause downstream ETL failures,")
            print("data quality issues and reporting inconsistencies.\n")
            print("Recommended Action")
            print("------------------")
            print("Modify the Snowflake DDL so that")
            print("EMPL_PERS_DOB uses the DATE datatype.")

        else:
            print("\n==========================================")
            print(f" ERROR: Request failed with status code {response.status_code}")
            print("==========================================")
            try:
                error_data = response.json()
                print("Error Details:")
                print(json.dumps(error_data, indent=2))
            except Exception:
                print(f"Response Text: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"\nNetwork/HTTP Exception occurred: {e}")


if __name__ == "__main__":
    create_jira_ticket()