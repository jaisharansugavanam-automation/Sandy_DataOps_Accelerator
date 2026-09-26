import os
import re
import subprocess


def run_git_command(args: list[str], cwd: str | None = None) -> str:
    """Run Git and turn common failures into actionable messages."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except FileNotFoundError as error:
        raise RuntimeError("Git was not found. Install Git and reopen the terminal.") from error
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip() or error.stdout.strip()
        if any(text in message.lower() for text in ("permission denied", "authentication failed", "could not read username")):
            raise PermissionError("GitHub authentication failed. Check your Git credentials and try again.") from error
        if "repository not found" in message.lower():
            raise RuntimeError("GitHub could not find that repository. Check the owner, repository name, and access permissions.") from error
        if "rejected" in message.lower() or "fetch first" in message.lower():
            raise RuntimeError(f"GitHub rejected the push because the remote has commits not in this checkout. Sync the branch, then retry. Details: {message}") from error
        raise RuntimeError(f"Git failed: {message}") from error


def get_repository_root() -> str:
    """Return the root of the Git checkout containing the current directory."""
    try:
        return run_git_command(["rev-parse", "--show-toplevel"])
    except RuntimeError as error:
        raise RuntimeError("This terminal is not inside a Git repository. Open the project folder and try again.") from error


def validate_target_path(path: str, repository_root: str) -> str:
    """Validate a file or folder and return its repository-relative path."""
    cleaned_path = path.strip().strip("\"'")
    if not cleaned_path:
        raise ValueError("Enter a file or folder path, for example DataOps_Python/athish/sample.py.")

    resolved_path = os.path.realpath(os.path.expanduser(cleaned_path))
    resolved_root = os.path.realpath(repository_root)
    if not os.path.exists(resolved_path):
        raise FileNotFoundError(f"I cannot find '{cleaned_path}'. Check the spelling and try again.")
    if not os.path.isfile(resolved_path) and not os.path.isdir(resolved_path):
        raise ValueError(f"'{cleaned_path}' is not a file or folder.")
    if os.path.commonpath([resolved_root, resolved_path]) != resolved_root:
        raise ValueError("That path is outside this Git repository. Choose a file or folder inside the project.")

    return os.path.relpath(resolved_path, resolved_root).replace(os.sep, "/")


def get_remotes(repository_root: str) -> dict[str, str]:
    """Return configured remote names and their URLs."""
    names = run_git_command(["remote"], cwd=repository_root).splitlines()
    return {
        name: run_git_command(["remote", "get-url", name], cwd=repository_root)
        for name in names
    }


def resolve_destination(destination: str, remotes: dict[str, str]) -> tuple[str, str]:
    """Resolve a configured remote or validate a GitHub URL/repository slug."""
    value = destination.strip().strip("\"'")
    for name, url in remotes.items():
        if value.casefold() == name.casefold():
            return name, url
        if value.rstrip("/").removesuffix(".git").casefold() == url.rstrip("/").removesuffix(".git").casefold():
            return value, url
        remote_repo = re.search(r"(?:github\.com[:/])([^/]+/[^/]+?)(?:\.git)?$", url, re.IGNORECASE)
        if remote_repo and value.removesuffix(".git").casefold() == remote_repo.group(1).casefold():
            return name, url

    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        value = f"https://github.com/{value.removesuffix('.git')}.git"
    is_https_github = re.fullmatch(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?", value, re.IGNORECASE)
    is_ssh_github = re.fullmatch(r"git@github\.com:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?", value, re.IGNORECASE)
    if is_https_github or is_ssh_github:
        return value, value

    choices = ", ".join(f"{name} ({url})" for name, url in remotes.items()) or "No remotes are configured"
    raise ValueError(f"I do not recognize '{destination}' as a GitHub repository. Choose a remote or enter owner/repository or a GitHub URL. Available remotes: {choices}.")


def push_path(path: str, destination: str, repository_root: str, remotes: dict[str, str]) -> str:
    """Commit the selected file/folder and push the current branch."""
    relative_path = validate_target_path(path, repository_root)
    remote_name, push_target = resolve_destination(destination, remotes)
    staged_before = run_git_command(["diff", "--cached", "--name-only"], cwd=repository_root)
    if staged_before:
        raise ValueError("There are already staged changes in this repository. Commit or unstage them first so I only push the file or folder you selected.")

    run_git_command(["add", "--", relative_path], cwd=repository_root)
    staged_paths = run_git_command(["diff", "--cached", "--name-only"], cwd=repository_root)
    if not staged_paths:
        raise ValueError(f"No changes to push from '{path}'. It may already be up to date or contain only ignored/empty files.")

    branch = run_git_command(["branch", "--show-current"], cwd=repository_root)
    if not branch:
        raise ValueError("Git is in detached HEAD state. Check out a branch before pushing.")
    commit_message = f"Add {os.path.basename(os.path.normpath(relative_path))} via GitHub Push Agent"
    run_git_command(["commit", "-m", commit_message], cwd=repository_root)
    commit_hash = run_git_command(["rev-parse", "--short", "HEAD"], cwd=repository_root)
    run_git_command(["push", push_target, branch], cwd=repository_root)

    return (
        f"Pushed: {relative_path}\n"
        f"Repository: {remote_name}\n"
        f"Branch: {branch}\n"
        f"Commit: {commit_message} ({commit_hash})\n"
        "Status: SUCCESS"
    )


def ask_for_path(repository_root: str) -> str | None:
    """Prompt until a valid repository file/folder is provided."""
    while True:
        path = input("AGENT: Which file or folder should I push? You can enter a relative or full path.\nYOU: ").strip()
        if path.lower() in ("exit", "quit", "cancel"):
            return None
        try:
            validate_target_path(path, repository_root)
            return path
        except (FileNotFoundError, ValueError) as error:
            print(f"AGENT: {error}")


def ask_for_destination(remotes: dict[str, str]) -> str | None:
    """Prompt until a configured remote or valid GitHub repository is provided."""
    if remotes:
        print("AGENT: Available repositories:")
        for name, url in remotes.items():
            print(f"  {name}: {url}")
    while True:
        destination = input("AGENT: Which GitHub repository should receive it? Enter a remote name, owner/repository, or GitHub URL.\nYOU: ").strip()
        if destination.lower() in ("exit", "quit", "cancel"):
            return None
        try:
            resolve_destination(destination, remotes)
            return destination
        except ValueError as error:
            print(f"AGENT: {error}")


def run_chat() -> None:
    """Run the terminal conversation until the user exits."""
    try:
        repository_root = get_repository_root()
        remotes = get_remotes(repository_root)
        branch = run_git_command(["branch", "--show-current"], cwd=repository_root)
    except RuntimeError as error:
        print(f"AGENT: {error}")
        return

    print("--- GitHub Push Agent ---")
    print(f"AGENT: I can push a file or folder from this checkout. Current branch: {branch or 'detached HEAD'}.")
    print("AGENT: Describe what you want to do, or type 'exit' to quit.")
    while True:
        request = input("YOU: ").strip()
        if request.lower() in ("exit", "quit"):
            print("AGENT: Goodbye.")
            return
        if not request:
            print("AGENT: Tell me what you would like to push, or type 'exit' to quit.")
            continue

        path = ask_for_path(repository_root)
        if path is None:
            print("AGENT: Cancelled.")
            continue
        destination = ask_for_destination(remotes)
        if destination is None:
            print("AGENT: Cancelled.")
            continue
        try:
            print(f"\nAGENT: {push_path(path, destination, repository_root, remotes)}\n")
        except (FileNotFoundError, PermissionError, RuntimeError, ValueError) as error:
            print(f"\nAGENT: I could not complete the push. {error}\n")


if __name__ == "__main__":
    run_chat()