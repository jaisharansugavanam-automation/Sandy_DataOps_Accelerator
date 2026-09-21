import os
import re
import subprocess


# ==========================================
# 1. PREDEFINED SDK / GIT FUNCTIONS
# ==========================================

def validate_file(file_path: str) -> bool:
    """Checks if the local file exists and is accessible."""
    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found at path: '{file_path}'")
    if not os.path.isfile(file_path):
        raise ValueError(f"Path is a directory, not a file: '{file_path}'")
    return True

def run_git_command(args: list[str]) -> str:
    """Helper to safely execute git commands using subprocess."""
    try:
        result = subprocess.run(
            ["git"] + args,
            check=True,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() or e.stdout.strip()
        if "Permission denied" in error_msg or "Authentication failed" in error_msg:
            raise PermissionError("Git Authentication failure. Check your credentials.") from e
        elif "rejected" in error_msg:
            raise RuntimeError(f"Git Push rejected: {error_msg}") from e
        elif "pathspec" in error_msg and "did not match any file" in error_msg:
            raise ValueError(f"Target branch or file path spec error: {error_msg}") from e
        else:
            raise RuntimeError(f"Git operation failed: {error_msg}") from e

def checkout_branch(branch_name: str) -> None:
    """Checks out an existing branch or creates it if it doesn't exist."""
    # Check if branch exists locally or remotely
    branches = run_git_command(["branch", "-a"])
    if branch_name in branches:
        run_git_command(["checkout", branch_name])
    else:
        # Create and switch to new branch
        run_git_command(["checkout", "-b", branch_name])

def add_file(file_path: str) -> None:
    """Stages the file for commit."""
    run_git_command(["add", file_path])

def commit_changes(commit_message: str) -> str:
    """Commits staged changes."""
    # Check if there are changes to commit
    status = run_git_command(["status", "--porcelain"])
    if not status:
        raise ValueError("Nothing to commit. No changes detected in the staged file.")
    
    run_git_command(["commit", "-m", commit_message])
    # Get short commit hash
    commit_hash = run_git_command(["rev-parse", "--short", "HEAD"])
    return commit_hash

def push_branch(branch_name: str) -> None:
    """Pushes local commits to the upstream remote branch."""
    run_git_command(["push", "-u", "origin", branch_name])


# ==========================================
# 2. AGENT PARSER & ORCHESTRATOR
# ==========================================

def parse_request(user_prompt: str) -> tuple[str | None, str | None]:
    """
    Extracts file_path and branch_name from natural language prompts.
    Uses basic regex pattern extraction to isolate paths and branch formats.
    """
    file_path = None
    branch_name = None

    # Pattern for file path: windows paths, posix paths, or quoted strings ending with file extensions
    path_match = re.search(r'["\']?([A-Za-z]:[\\/][^"\'\s]+|\b\/?[\w\.-]+(?:\/[\w\.-]+)+\.[\w]+)["\']?', user_prompt)
    if path_match:
        file_path = path_match.group(1).strip()

    # Pattern for branch name: "branch <name>", "to <branch>", or standard git branch naming patterns
    branch_match = re.search(r'(?:branch\s+["\']?([\w\/-]+)["\']?|to\s+["\']?([\w\/-]+)["\']?)', user_prompt, re.IGNORECASE)
    if branch_match:
        branch_name = branch_match.group(1) or branch_match.group(2)
        # Avoid capturing file paths as branch names if keywords overlap
        if branch_name and ("/" in branch_name) and ("." in branch_name.split("/")[-1]):
            branch_name = None

    # Secondary check for explicit quotation marks if regular patterns missed them
    quotes = re.findall(r'["\']([^"\']+)["\']', user_prompt)
    for item in quotes:
        if item.endswith(('.csv', '.py', '.json', '.txt', '.sql', '.yml', '.yaml')) and not file_path:
            file_path = item
        elif '/' in item and not item.endswith(('.csv', '.py', '.json', '.txt', '.sql', '.yml', '.yaml')) and not branch_name:
            branch_name = item

    return file_path, branch_name


def github_push_agent(user_prompt: str) -> str:
    """
    Main Agent Orchestration workflow.
    Validates inputs, handles prompts, and executes SDK tools safely.
    """
    # Step 1: Intent & Parameter Extraction
    file_path, branch_name = parse_request(user_prompt)

    # Step 2: Parameter Validation & Prompt Guard
    missing = []
    if not file_path:
        missing.append("1. File path")
    if not branch_name:
        missing.append("2. Target GitHub branch name")

    if missing:
        if len(missing) == 2:
            return "Please provide:\n" + "\n".join(missing)
        elif not file_path:
            return "Which file should I push? Please provide the file path."
        else:
            return "Which branch should I push the file to?"

    # Step 3: Tool Execution (SDK Pipeline)
    try:
        # 1. Validate File Existence
        validate_file(file_path)

        # 2. Checkout or Create Branch
        checkout_branch(branch_name)

        # 3. Stage File
        add_file(file_path)

        # 4. Commit Changes
        file_name = os.path.basename(file_path)
        commit_msg = f"Add {file_name} via GitHub Push Agent"
        commit_hash = commit_changes(commit_msg)

        # 5. Push to Remote Branch
        push_branch(branch_name)

        # Step 4: Return Agent Result
        return (
            f"File: {file_name}\n"
            f"Branch: {branch_name}\n\n"
            f"GitHub push completed successfully.\n\n"
            f"Commit: {commit_msg} ({commit_hash})\n"
            f"Branch: {branch_name}\n"
            f"Status: SUCCESS"
        )

    except Exception as e:
        return f"Status: FAILED\nError: {str(e)}"


# ==========================================
# 3. VERIFICATION & TEST EXAMPLES
# ==========================================

if __name__ == "__main__":
    print("--- Test 1: Full Prompt ---")
    prompt_1 = 'Hey, take the file from "C:/project/output/ddl_validation_result.csv" and push it to branch "feature/ddl-validation"'
    print("User Prompt:", prompt_1)
    file_p, branch_p = parse_request(prompt_1)
    print(f"Extracted -> Path: {file_p} | Branch: {branch_p}\n")

    print("--- Test 2: Missing Branch ---")
    prompt_2 = 'Push C:/project/result.csv to GitHub.'
    print("User Response:", github_push_agent(prompt_2))
    print()

    print("--- Test 3: Missing File Path ---")
    prompt_3 = 'Push the file to feature/testing.'
    print("User Response:", github_push_agent(prompt_3))
    print()

    print("--- Test 4: Completely Missing Parameters ---")
    prompt_4 = 'Push my validation file to GitHub.'
    print("User Response:", github_push_agent(prompt_4))