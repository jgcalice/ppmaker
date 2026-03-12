export interface Template {
  id: string;
  name: string;
  scope: "global" | "local";
  palette: {
    primary: string;
    secondary: string;
    accent: string;
    background: string;
    text: string;
  };
  layouts: string[];
  font_title: string;
  font_body: string;
}

export interface TemplatesResponse {
  templates: Template[];
}

export interface StorytellingRequest {
  content: string;
  template_id: string;
  audience?: string;
  objective?: string;
  tone?: "professional" | "casual" | "executive";
}

export interface Slide {
  index: number;
  layout:
    | "title"
    | "content"
    | "two-column"
    | "chart-placeholder"
    | "image-text"
    | "closing";
  title: string;
  talking_points: string[];
  has_placeholder: boolean;
  placeholder_hint: string;
}

export interface StorytellingOutline {
  title: string;
  objective: string;
  audience: string;
  total_slides: number;
  slides: Slide[];
}

export interface GeneratePptxRequest {
  storytelling: StorytellingOutline;
  template_id: string;
}

export type SSEEvent =
  | {
      type: "progress";
      step:
        | "planner"
        | "architect"
        | "story_builder"
        | "visual_director"
        | "content_gen"
        | "editor";
      message: string;
    }
  | { type: "outline"; data: StorytellingOutline }
  | { type: "done" };
