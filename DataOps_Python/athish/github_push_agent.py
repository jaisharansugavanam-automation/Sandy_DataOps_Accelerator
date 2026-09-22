import os
import re
import subprocess
import sys

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
    branches = run_git_command(["branch", "-a"])
    if branch_name in branches:
        run_git_command(["checkout", branch_name])
    else:
        run_git_command(["checkout", "-b", branch_name])

def add_file(file_path: str) -> None:
    """Stages the file for commit."""
    run_git_command(["add", file_path])

def commit_changes(commit_message: str) -> str:
    """Commits staged changes."""
    status = run_git_command(["status", "--porcelain"])
    if not status:
        raise ValueError("Nothing to commit. No changes detected in the staged file.")

    run_git_command(["commit", "-m", commit_message])
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
    Extracts file_path and branch_name from natural language prompts using Regex.
    """
    file_path = None
    branch_name = None

    # Matches file paths ending in common extensions or standard path formats
    path_match = re.search(r'["\']?([A-Za-z]:[\\/][^"\'\s]+|\b\/?[\w\.-]+(?:\/[\w\.-]+)+\.[\w]+)["\']?', user_prompt)
    if path_match:
        file_path = path_match.group(1).strip()

    # Matches branch names following keywords like 'branch <name>' or 'to <name>'
    branch_match = re.search(r'(?:branch\s+["\']?([\w\/-]+)["\']?|to\s+["\']?([\w\/-]+)["\']?)', user_prompt, re.IGNORECASE)
    if branch_match:
        branch_name = branch_match.group(1) or branch_match.group(2)
        if branch_name and ("/" in branch_name) and ("." in branch_name.split("/")[-1]):
            branch_name = None

    # Secondary check for quotes
    quotes = re.findall(r'["\']([^"\']+)["\']', user_prompt)
    for item in quotes:
        if item.endswith(('.csv', '.py', '.json', '.txt', '.sql', '.yml', '.yaml')) and not file_path:
            file_path = item
        elif '/' in item and not item.endswith(('.csv', '.py', '.json', '.txt', '.sql', '.yml', '.yaml')) and not branch_name:
            branch_name = item

    return file_path, branch_name


def github_push_agent(file_path: str | None, branch_name: str | None) -> str:
    """
    Main Agent Orchestration workflow.
    Validates inputs and executes predefined Git SDK functions.
    """
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

    try:
        validate_file(file_path)
        checkout_branch(branch_name)
        add_file(file_path)

        file_name = os.path.basename(file_path)
        commit_msg = f"Add {file_name} via GitHub Push Agent"
        commit_hash = commit_changes(commit_msg)

        push_branch(branch_name)

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
# 3. SCRIPT ENTRY POINT
# ==========================================

if __name__ == "__main__":
    print("--- Git Copilot Agent --- (type 'exit' to quit)")
    
    while True:
        user_input = input("You > ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue

        file_path, branch_name = parse_request(user_input)
        result = github_push_agent(file_path, branch_name)
        print(f"\n{result}\n")