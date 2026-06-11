# agents/poster.py
import logging
import os

from github import Github, GithubException

logger = logging.getLogger(__name__)


async def post_pr_comment(repo_name: str, pr_number: int, comment: str) -> bool:
    """Post a comment on a GitHub PR. Returns True on success."""
    try:
        g = Github(os.getenv("GITHUB_TOKEN"))
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        pr.create_issue_comment(comment)
        logger.info("Posted review comment on %s#%s", repo_name, pr_number)
        return True
    except GithubException as e:
        logger.error("GitHub API error posting comment: %s", e)
        return False
    except Exception:
        logger.exception("Unexpected error posting PR comment")
        return False
