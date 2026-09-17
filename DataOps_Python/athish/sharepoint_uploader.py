import os
from office365.runtime.auth.user_credential import UserCredential
from office365.sharepoint.client_context import ClientContext

# ==========================================
# CONFIGURATION
# ==========================================
LOCAL_FILE_PATH = "data/raw_source_empl_pers.csv"  # File to upload
SHAREPOINT_SITE_URL = "https://yourcompany.sharepoint.com/sites/YourSite"
TARGET_FOLDER_URL = "Shared Documents/General/DataOps"  # Path inside SharePoint

# Authentication details (Use Environment Variables for security)
SHAREPOINT_USER = os.getenv("SHAREPOINT_USER", "your_email@yourcompany.com")
SHAREPOINT_PASSWORD = os.getenv("SHAREPOINT_PASSWORD", "your_password")


def validate_file(file_path):
    """Validates that the local CSV file exists and is not empty."""
    if not os.path.exists(file_path):
        return False, f"Error: Local file '{file_path}' does not exist."
    if os.path.getsize(file_path) == 0:
        return False, f"Error: Local file '{file_path}' is empty."
    return True, "File validation passed."


def authenticate_sharepoint(site_url, username, password):
    """Authenticates to SharePoint and returns a ClientContext instance."""
    try:
        user_credentials = UserCredential(username, password)
        ctx = ClientContext(site_url).with_credentials(user_credentials)
        # Test connection by querying web title
        web = ctx.web
        ctx.load(web)
        ctx.execute_query()
        return ctx, None
    except Exception as e:
        return None, f"Authentication Failed: {str(e)}"


def upload_csv_to_sharepoint(ctx, file_path, target_folder_url):
    """Uploads the specified local file to the target SharePoint folder."""
    try:
        file_name = os.path.basename(file_path)
        target_folder = ctx.web.get_folder_by_server_relative_url(target_folder_url)

        with open(file_path, "rb") as content_file:
            file_content = content_file.read()

        # Execute Upload
        uploaded_file = target_folder.upload_file(file_name, file_content)
        ctx.execute_query()

        return True, uploaded_file, None
    except Exception as e:
        return False, None, f"Upload Failed: {str(e)}"


def verify_upload(ctx, target_folder_url, file_name):
    """Verifies that the uploaded file exists in the target SharePoint directory."""
    try:
        file_url = f"{target_folder_url}/{file_name}"
        remote_file = ctx.web.get_file_by_server_relative_url(file_url)
        ctx.load(remote_file)
        ctx.execute_query()

        if remote_file.properties:
            return True, file_url
        return False, None
    except Exception:
        return False, None


def main():
    print("==========================================")
    print("    SHAREPOINT CSV UPLOADER FRAMEWORK    ")
    print("==========================================")

    # 1. Validate File
    print("\n[1/4] Validating Local CSV File...")
    is_valid, msg = validate_file(LOCAL_FILE_PATH)
    if not is_valid:
        print(f"  --> [FAIL] {msg}")
        return
    print(f"  --> [PASS] {msg}")

    # 2. Authenticate
    print("\n[2/4] Authenticating with SharePoint...")
    ctx, auth_err = authenticate_sharepoint(
        SHAREPOINT_SITE_URL, SHAREPOINT_USER, SHAREPOINT_PASSWORD
    )
    if auth_err:
        print(f"  --> [FAIL] {auth_err}")
        return
    print("  --> [PASS] Authenticated successfully!")

    # 3. Upload File
    file_name = os.path.basename(LOCAL_FILE_PATH)
    print(f"\n[3/4] Uploading '{file_name}' to '{TARGET_FOLDER_URL}'...")
    success, _, upload_err = upload_csv_to_sharepoint(
        ctx, LOCAL_FILE_PATH, TARGET_FOLDER_URL
    )
    if not success:
        print(f"  --> [FAIL] {upload_err}")
        return
    print("  --> [PASS] File uploaded to stage.")

    # 4. Verify Upload
    print("\n[4/4] Verifying file existence on SharePoint...")
    is_verified, remote_url = verify_upload(ctx, TARGET_FOLDER_URL, file_name)

    # Print Summary Report
    print("\n==========================================")
    print("             UPLOAD SUMMARY               ")
    print("==========================================")
    if is_verified:
        print(" Upload Status : SUCCESS")
        print(f" File          : {file_name}")
        print(f" Location      : {remote_url}")
    else:
        print(" Upload Status : FAILED (Verification Failed)")
        print(f" File          : {file_name}")
    print("==========================================")


if __name__ == "__main__":
    main()