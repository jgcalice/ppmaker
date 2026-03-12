import asyncio
import io
import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from starlette.responses import StreamingResponse

from models.schemas import GeneratePptxRequest
from services.template_service import get_template_pptx_path, get_template_metadata, get_known_template_ids
from services.pptx_service import generate_pptx
from services.security_service import validate_template_id, SecurityError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate-pptx")
async def create_pptx(request: GeneratePptxRequest):
    try:
        validate_template_id(request.template_id, get_known_template_ids())
    except SecurityError:
        raise HTTPException(status_code=404, detail="Template not found")

    template_path = get_template_pptx_path(request.template_id)
    if template_path is None:
        raise HTTPException(status_code=404, detail="Template not found")

    template_meta = get_template_metadata(request.template_id)
    if template_meta is None:
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        buffer = await asyncio.wait_for(
            asyncio.to_thread(
                generate_pptx,
                request.storytelling,
                str(template_path),
                template_meta,
            ),
            timeout=30,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception:
        logger.exception("PPTX generation failed")
        raise HTTPException(status_code=500, detail="Internal server error")

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={
            "Content-Disposition": 'attachment; filename="presentation.pptx"',
        },
    )


def _generate_thumbnail_sync(
    storytelling,
    template_path: str,
    template_meta,
) -> bytes:
    """
    Blocking helper: generate PPTX → thumbnail JPEG grid.

    Returns raw JPEG bytes of the first grid image.

    Raises
    ------
    RuntimeError
        If LibreOffice is not available (caller maps to 503).
    """
    from scripts.thumbnail import generate_thumbnail_grid

    # Generate the PPTX first
    pptx_buffer = generate_pptx(storytelling, template_path, template_meta)

    # Write to a temp file so thumbnail.py can read it
    with tempfile.TemporaryDirectory() as tmp:
        tmp_pptx = Path(tmp) / "presentation.pptx"
        tmp_pptx.write_bytes(pptx_buffer.read())

        output_prefix = str(Path(tmp) / "thumbnails")
        grid_files = generate_thumbnail_grid(tmp_pptx, output_prefix, cols=3)

        if not grid_files:
            raise RuntimeError("Thumbnail generation produced no output files")

        jpeg_bytes = Path(grid_files[0]).read_bytes()

    return jpeg_bytes


@router.post("/generate-pptx/thumbnail")
async def create_pptx_thumbnail(request: GeneratePptxRequest):
    """
    Generate a JPEG thumbnail grid of the presentation slides.

    POST /api/v1/generate-pptx/thumbnail
    Request body: { "storytelling": <StorytellingOutline>, "template_id": "string" }

    Responses:
      200 image/jpeg   — thumbnail grid
      404              — Template not found
      503              — LibreOffice not available
      500              — Internal server error
    """
    try:
        validate_template_id(request.template_id, get_known_template_ids())
    except SecurityError:
        raise HTTPException(status_code=404, detail="Template not found")

    template_path = get_template_pptx_path(request.template_id)
    if template_path is None:
        raise HTTPException(status_code=404, detail="Template not found")

    template_meta = get_template_metadata(request.template_id)
    if template_meta is None:
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        jpeg_bytes = await asyncio.wait_for(
            asyncio.to_thread(
                _generate_thumbnail_sync,
                request.storytelling,
                str(template_path),
                template_meta,
            ),
            timeout=120,  # LibreOffice conversion can be slow
        )
    except asyncio.TimeoutError:
        logger.error("Thumbnail generation timed out")
        raise HTTPException(status_code=500, detail="Internal server error")
    except RuntimeError as exc:
        msg = str(exc)
        if "LibreOffice" in msg or "soffice" in msg or "pdftoppm" in msg:
            logger.warning("Thumbnail unavailable: %s", msg)
            raise HTTPException(
                status_code=503,
                detail="LibreOffice not available for thumbnail generation",
            )
        logger.exception("Thumbnail generation failed")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception:
        logger.exception("Thumbnail generation failed")
        raise HTTPException(status_code=500, detail="Internal server error")

    return StreamingResponse(
        io.BytesIO(jpeg_bytes),
        media_type="image/jpeg",
        headers={
            "Content-Disposition": 'inline; filename="thumbnails.jpg"',
        },
    )
