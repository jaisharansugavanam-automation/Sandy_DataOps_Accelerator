import markdown
from atlassian import Confluence

# Credentials
USERNAME = "25ct005@gmail.com"
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")
# Setup
CONFLUENCE_URL = "https://sandydataopsaccelerator.atlassian.net/wiki"
SPACE_KEY = "~71202041729ae922f84e7f84c871977a79d4d4"
PAGE_TITLE = "Test Summary - DDL Check"
MD_FILE_PATH = "models_ddl/reports/test_summary.md"

# Read & Convert
with open(MD_FILE_PATH, "r", encoding="utf-8") as file:
    markdown_text = file.read()

html_body = markdown.markdown(
    markdown_text, extensions=["tables", "fenced_code"]
)

# Connect to Confluence
confluence = Confluence(
    url=CONFLUENCE_URL, username=USERNAME, password=API_TOKEN, cloud=True
)

# Upload or Update Page
try:
    if confluence.page_exists(SPACE_KEY, PAGE_TITLE):
        page_id = confluence.get_page_id(SPACE_KEY, PAGE_TITLE)
        confluence.update_page(
            page_id=page_id,
            title=PAGE_TITLE,
            body=html_body,
            representation="storage",
        )
        print(f"Success! Updated page (ID: {page_id})")
    else:
        response = confluence.create_page(
            space=SPACE_KEY,
            title=PAGE_TITLE,
            body=html_body,
            representation="storage",
        )
        print(f"Success! Created new page (ID: {response['id']})")
except Exception as e:
    print(f"Upload failed. Error details:\n{e}")