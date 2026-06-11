# api/review.py
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.hitl import get_pending_review, resolve_review
from agents.poster import post_pr_comment

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/review", tags=["review"])


class EditRequest(BaseModel):
    edited_report: str


@router.get("/{review_id}")
async def get_review(review_id: str):
    """Fetch a pending review so the human can read it."""
    review = await get_pending_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found or expired")
    return review


@router.post("/{review_id}/approve")
async def approve_review(review_id: str):
    """Approve the review — posts it to GitHub as-is."""
    review = await resolve_review(review_id, "approve")
    if not review:
        raise HTTPException(status_code=404, detail="Review not found or expired")

    success = await post_pr_comment(
        review["repo"],
        review["pr_number"],
        review["final_report"],
    )

    if not success:
        raise HTTPException(status_code=502, detail="Failed to post comment to GitHub")

    logger.info("Review %s approved and posted", review_id)
    return {"status": "approved", "posted": True, "review_id": review_id}


@router.post("/{review_id}/edit")
async def edit_review(review_id: str, body: EditRequest):
    """Edit the review text, then post the edited version to GitHub."""
    review = await resolve_review(review_id, "edit", body.edited_report)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found or expired")

    success = await post_pr_comment(
        review["repo"],
        review["pr_number"],
        review["final_report"],
    )

    if not success:
        raise HTTPException(status_code=502, detail="Failed to post comment to GitHub")

    logger.info("Review %s edited and posted", review_id)
    return {"status": "edited", "posted": True, "review_id": review_id}


@router.post("/{review_id}/reject")
async def reject_review(review_id: str):
    """Reject the review — nothing gets posted to GitHub."""
    review = await resolve_review(review_id, "reject")
    if not review:
        raise HTTPException(status_code=404, detail="Review not found or expired")

    logger.info("Review %s rejected — not posting to GitHub", review_id)
    return {"status": "rejected", "posted": False, "review_id": review_id}
