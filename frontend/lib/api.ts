import type {
  TemplatesResponse,
  StorytellingRequest,
  GeneratePptxRequest,
  SSEEvent,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchTemplates(): Promise<TemplatesResponse> {
  const res = await fetch(`${API_URL}/api/v1/templates`);
  if (!res.ok) throw new Error("Falha ao carregar templates");
  return res.json();
}

export async function streamStorytelling(
  request: StorytellingRequest,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/storytelling`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });

  if (!res.ok) throw new Error("Falha ao gerar storytelling");
  if (!res.body) throw new Error("Stream não disponível");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() ?? "";

    for (const chunk of lines) {
      const dataLine = chunk
        .split("\n")
        .find((l) => l.startsWith("data: "));
      if (!dataLine) continue;
      try {
        const event: SSEEvent = JSON.parse(dataLine.slice(6));
        onEvent(event);
      } catch {
        // skip malformed events
      }
    }
  }
}

export async function downloadPptx(request: GeneratePptxRequest): Promise<void> {
  const res = await fetch(`${API_URL}/api/v1/generate-pptx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!res.ok) throw new Error("Falha ao gerar apresentação");

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "presentation.pptx";
  a.click();
  URL.revokeObjectURL(url);
}
