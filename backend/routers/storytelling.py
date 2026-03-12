import logging

from fastapi import APIRouter, HTTPException
from starlette.responses import StreamingResponse

from models.schemas import StorytellingRequest
from services.ai_service import generate_storytelling
from services.template_service import get_known_template_ids
from services.security_service import validate_template_id, SecurityError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/storytelling")
async def create_storytelling(request: StorytellingRequest):
    try:
        validate_template_id(request.template_id, get_known_template_ids())
    except SecurityError:
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        return StreamingResponse(
            generate_storytelling(
                content=request.content,
                template_id=request.template_id,
                audience=request.audience,
                objective=request.objective,
                tone=request.tone.value,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception:
        logger.exception("Storytelling generation failed")
        raise HTTPException(status_code=500, detail="Internal server error")
