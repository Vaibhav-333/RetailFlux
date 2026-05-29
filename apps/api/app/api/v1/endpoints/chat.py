from fastapi import APIRouter, Depends, Request

from app.core.limiter import limiter
from app.domains.auth.dependencies import get_current_user
from app.domains.chat.chat_service import handle_chat_message
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/message", response_model=ChatResponse)
@limiter.limit("60/hour")
async def chat_message(
    request: Request,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    return await handle_chat_message(
        company_id=str(current_user.company_id),
        role=current_user.role.value if hasattr(current_user.role, "value") else current_user.role,
        message=body.message,
    )
