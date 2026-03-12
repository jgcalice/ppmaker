from fastapi import APIRouter

from services.template_service import get_all_templates

router = APIRouter()


@router.get("/templates")
async def list_templates():
    templates = get_all_templates()
    return {"templates": [t.model_dump() for t in templates]}
