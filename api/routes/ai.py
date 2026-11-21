"""Authenticated conversational AI endpoint for FinWell AI."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.auth_dependencies import get_current_user
from services.ai_query_orchestrator import answer_financial_question

router = APIRouter()


class AIChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


@router.post("/ai/chat", tags=["AI Assistant"])
def chat_with_finwell_ai(
    request: AIChatRequest,
    user_id: int = Depends(get_current_user),
):
    """Answer a question using only the authenticated user's data."""
    try:
        result = answer_financial_question(
            user_id=user_id,
            question=request.question,
        )
        return result
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        )
    except Exception:
        # Avoid returning internal DB paths, prompts, or stack traces to clients.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="FinWell AI could not complete the request. Check backend logs.",
        )
