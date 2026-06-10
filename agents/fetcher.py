from github import Github
import os

def fetch_pr_data(repo_name: str, pr_number: int) -> dict:
    """Fetch PR diff and metadata from GitHub."""
    g = Github(os.getenv("GITHUB_TOKEN"))
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    files = []
    for f in pr.get_files():
        files.append({
            "filename": f.filename,
            "status": f.status,
            "patch": f.patch or "",
            "additions": f.additions,
            "deletions": f.deletions,
        })

    return {
        "title": pr.title,
        "body": pr.body or "",
        "author": pr.user.login,
        "base_branch": pr.base.ref,
        "head_branch": pr.head.ref,
        "files": files,
    }