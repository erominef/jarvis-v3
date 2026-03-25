# tools/git_tools.py — Git operations via Gitea REST API.
#
# Single git_op(action, **kwargs) function dispatches all actions.
#
# Read actions (no side effects):
#   list_repos, get_repo, list_files, read_file, log
#
# Write actions (modify remote state):
#   create_repo, write_file, delete_repo
#
# Env: GITEA_URL, GITEA_TOKEN
# Returns "not configured" immediately if GITEA_TOKEN is unset.


def git_op(action: str, **kwargs) -> str:
    """
    Perform a Gitea operation.

    action:
      list_repos              — list all repos for the authenticated user
      get_repo(repo)          — get repo metadata
      list_files(repo, path, ref) — list directory contents
      read_file(repo, path, ref)  — read file content (max 3000 chars)
      log(repo, limit)        — recent commits
      create_repo(name, description, private) — create new repo
      write_file(repo, path, content, message) — create or update file
      delete_repo(repo)       — delete repo permanently
    """
    # Implementation omitted.
    raise NotImplementedError
