# agents/fetcher.py
import logging
import os

from github import Github, GithubException

logger = logging.getLogger(__name__)

MAX_DIFF_CHARS = 12000


def fetch_pr_data(repo_name: str, pr_number: int) -> dict:
    """Fetch PR diff and metadata from GitHub API."""
    g = Github(os.getenv("GITHUB_TOKEN"))

    try:
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
    except GithubException as e:
        logger.error("GitHub API error fetching PR %s#%s: %s", repo_name, pr_number, e)
        raise

    files = []
    total_diff = []

    for f in pr.get_files():
        patch = f.patch or ""
        files.append({
            "filename": f.filename,
            "status": f.status,
            "additions": f.additions,
            "deletions": f.deletions,
            "patch": patch,
        })
        if patch:
            total_diff.append(f"### {f.filename} ({f.status})\n{patch}")

    full_diff = "\n\n".join(total_diff)

    if len(full_diff) > MAX_DIFF_CHARS:
        full_diff = full_diff[:MAX_DIFF_CHARS] + "\n\n[diff truncated — too large]"
        logger.warning("PR diff truncated for %s#%s", repo_name, pr_number)

    return {
        "title": pr.title,
        "body": pr.body or "",
        "author": pr.user.login,
        "base_branch": pr.base.ref,
        "head_branch": pr.head.ref,
        "files_changed": len(files),
        "additions": pr.additions,
        "deletions": pr.deletions,
        "files": files,
        "diff": full_diff,
    }
