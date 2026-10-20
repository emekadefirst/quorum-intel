from fastapi import Depends, HTTPException

from src.common.base_router import base_router
from src.crypto.jwt import JwtService
from src.modules.account.models import Account
from src.modules.chat.service import ChatRequest, ChatResponse, ChatService

router = base_router(prefix="/api/chat", tags=["Chat"])


@router.post("/message", response_model=ChatResponse)
async def send_message(
    req: ChatRequest,
    user: Account = Depends(JwtService.get_current_user),
) -> ChatResponse:
    try:
        return await ChatService.send(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Agent error: {e}")
