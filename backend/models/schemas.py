from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ToneEnum(str, Enum):
    professional = "professional"
    casual = "casual"
    executive = "executive"


class StorytellingRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    template_id: str
    audience: Optional[str] = None
    objective: Optional[str] = None
    tone: ToneEnum = ToneEnum.professional


class SlideOutline(BaseModel):
    index: int
    layout: str
    title: str
    talking_points: list[str]
    has_placeholder: bool = False
    placeholder_hint: str = ""


class StorytellingOutline(BaseModel):
    title: str
    objective: str
    audience: str
    total_slides: int
    slides: list[SlideOutline]


class GeneratePptxRequest(BaseModel):
    storytelling: StorytellingOutline
    template_id: str


class TemplatePalette(BaseModel):
    primary: str
    secondary: str
    accent: str
    background: str
    text: str


class TemplateInfo(BaseModel):
    id: str
    name: str
    scope: str
    palette: TemplatePalette
    layouts: list[str]
    font_title: str
    font_body: str
    layout_map: Optional[dict[str, str]] = None  # maps generic name → actual layout name in PPTX
