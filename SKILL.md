# PPMaker — PPTX Skill

Guia completo para Claude Code trabalhar com apresentações PowerPoint no projeto ppmaker.

---

## Quando ativar

Qualquer menção a slides, apresentações, deck, PPTX, PowerPoint — seja criação, edição, análise, manutenção ou debugging do pipeline de geração.

---

## Contexto do projeto

**Stack:** Python FastAPI + python-pptx + Anthropic SDK (backend) | Next.js 14 + TailwindCSS (frontend)

**Raiz do projeto:** `ppmaker/`

```
ppmaker/
├── backend/
│   └── services/
│       ├── pptx_service.py         ← orquestrador dos 3 caminhos de renderização
│       ├── render_from_template.py ← StencilRenderer (caminho 2)
│       ├── xml_renderer.py         ← XmlRenderer (caminho 1, preferido)
│       └── visual_director.py      ← seleciona layout do catálogo por slide
├── scripts/
│   ├── office/
│   │   ├── unpack.py               ← extrai PPTX → XML formatado
│   │   └── pack.py                 ← reempacota XML → PPTX válido
│   ├── add_slide.py                ← duplica/adiciona slide (gerencia rIds, Content_Types)
│   ├── clean.py                    ← remove slides órfãos e mídia não referenciada
│   └── thumbnail.py                ← gera grid de thumbnails para QA visual
├── template_padrao/
│   ├── local/
│   │   ├── local-corporate.pptx    ← template principal (paleta AB InBev)
│   │   ├── local-corporate.json    ← metadados do template
│   │   ├── logo.png
│   │   └── example/
│   │       └── Template Ambev_atualizado_ - Copia.pptx  ← stencil com 46+ layouts
│   └── global/
│       └── template-01.pptx        ← template corporativo genérico
└── tools/
    ├── layout_catalog.json         ← mapeia cada slide do stencil (SLIDE01..SLIDE46+)
    └── brand_tokens.json           ← tokens de marca (paleta, tipografia)
```

**Paleta AB InBev (local-corporate):**
- primary: `#0766FF`
- secondary: `#00328D`
- accent: `#FFA41B`
- background: `#FFFFFF`
- text: `#00328D`
- fonts: Avantt (título e corpo)

**Dimensões de slide:** 13.33 × 7.50 polegadas (widescreen 16:9)

---

## Os 3 caminhos de renderização

A variável de ambiente `PPTX_RENDERER` controla qual caminho usar. Default: `auto`.

| Prioridade | Caminho | Env var | Quando usar |
|---|---|---|---|
| 1 (melhor) | XML-based | `PPTX_RENDERER=xml` | Criação nova, máxima fidelidade ao template |
| 2 | Stencil-based | `PPTX_RENDERER=stencil` | Quando XML renderer não disponível |
| 3 (fallback) | Programmatic | `PPTX_RENDERER=programmatic` | Última opção, sem fidelidade visual |

**Para forçar um caminho via .env:**
```bash
PPTX_RENDERER=xml        uvicorn main:app --reload  # forçar XML
PPTX_RENDERER=stencil    uvicorn main:app --reload  # forçar stencil
PPTX_RENDERER=programmatic uvicorn main:app --reload  # forçar programmatic
```

---

## Templates disponíveis

| Template ID | Arquivo | Uso |
|---|---|---|
| `local-corporate` | `template_padrao/local/local-corporate.pptx` | Apresentações AB InBev (padrão) |
| `global` | `template_padrao/global/template-01.pptx` | Apresentações corporativas genéricas |
| stencil (interno) | `template_padrao/local/example/Template Ambev_atualizado_ - Copia.pptx` | Usado pelo StencilRenderer como fonte de layouts |

**Layouts disponíveis no local-corporate:** `title`, `content`, `two-column`, `chart-placeholder`, `image-text`, `closing`

**O layout_catalog.json** mapeia cada slide do stencil Ambev para um `layout_id` (SLIDE01, SLIDE02... SLIDE46+) com `features` e `use_for`. Usado pelo `VisualDirector` para selecionar o slide-modelo correto para cada conteúdo.

---

## Abordagem 1: XML-based (preferida)

Edita diretamente o XML interno do PPTX. Preserva 100% da formatação original — fontes, animações, SmartArt, estilos. Cada slide é um arquivo XML separado (permite edição paralela por subagentes).

### Fluxo completo

```
1. Analisar o template
   python scripts/thumbnail.py template_padrao/local/local-corporate.pptx

2. Extrair conteúdo do template (inspecionar texto e estrutura)
   python -m markitdown template_padrao/local/local-corporate.pptx

3. Desempacotar o template para edição XML
   python scripts/office/unpack.py template_padrao/local/local-corporate.pptx /tmp/unpacked/

4. Planejar mapeamento de slides
   - Listar slides desempacotados: ls /tmp/unpacked/ppt/slides/
   - Inspecionar XML de um slide: cat /tmp/unpacked/ppt/slides/slide1.xml
   - Mapear conteúdo desejado → slide-modelo do stencil

5. MUDANÇAS ESTRUTURAIS PRIMEIRO (antes de editar conteúdo)
   - Adicionar slides: python scripts/add_slide.py /tmp/unpacked/ <slide_idx>
   - Remover slides: editar ppt/presentation.xml e apagar o arquivo slide*.xml
   - Reordenar: editar a ordem em ppt/presentation.xml

6. Editar conteúdo XML de cada slide
   - Usar EditTool diretamente nos arquivos XML, NÃO usar sed/python para edição inline
   - Seguir as regras de edição XML abaixo (seção "Regras de formatação XML")

7. Limpar arquivos órfãos
   python scripts/clean.py /tmp/unpacked/

8. Empacotar de volta
   python scripts/office/pack.py /tmp/unpacked/ output.pptx --original template_padrao/local/local-corporate.pptx

9. QA visual (obrigatório — ver seção "QA visual")
   python scripts/thumbnail.py output.pptx
```

### Estrutura do diretório desempacotado

Após `unpack.py`, a estrutura é:

```
/tmp/unpacked/
├── [Content_Types].xml
├── _rels/
│   └── .rels
└── ppt/
    ├── presentation.xml        ← ordem dos slides, dimensões
    ├── slides/
    │   ├── slide1.xml          ← conteúdo do slide 1
    │   ├── slide2.xml          ← conteúdo do slide 2
    │   └── _rels/
    │       ├── slide1.xml.rels ← relacionamentos do slide 1 (imagens, layouts)
    │       └── slide2.xml.rels
    ├── slideLayouts/           ← layouts de slide (não editar)
    ├── slideMasters/           ← slide masters (não editar)
    └── media/                  ← imagens e mídia
```

---

## Abordagem 2: Stencil-based (via StencilRenderer)

Clona slides do stencil Ambev via python-pptx e substitui texto preservando formatação.

### Uso direto via API

```bash
# Forçar caminho stencil
PPTX_RENDERER=stencil uvicorn main:app --reload

curl -X POST http://localhost:8000/api/v1/generate-pptx \
  -H "Content-Type: application/json" \
  -d '{"storytelling": {...}, "template_id": "local-corporate"}' \
  --output output.pptx
```

### Uso programático

```python
from backend.services.render_from_template import StencilRenderer
from backend.services.visual_director import VisualDirector
import json

with open("tools/layout_catalog.json") as f:
    catalog = json.load(f)
with open("tools/brand_tokens.json") as f:
    brand_tokens = json.load(f)

stencil_path = "template_padrao/local/example/Template Ambev_atualizado_ - Copia.pptx"
renderer = StencilRenderer(stencil_path, catalog, brand_tokens)
vd = VisualDirector("tools/layout_catalog.json", "tools/brand_tokens.json")

buf = renderer.render(outline, visual_director=vd)
with open("output.pptx", "wb") as f:
    f.write(buf.read())
```

### Limitações conhecidas do StencilRenderer

- Pode corromper namespaces ao clonar slides com AnimatedSmartArt ou efeitos avançados
- Substituição de texto usa heurísticas de zona (TITLE, BODY, LABEL, CAPTION, HIGHLIGHT)
- OneDrive pode bloquear o arquivo stencil — usar `cp` para copiar para `$TEMP/ambev.pptx` antes

---

## Scripts disponíveis

### `scripts/office/unpack.py` — Extrair PPTX para XML

Extrai o arquivo PPTX (que é um ZIP) e formata o XML de cada slide para edição humana.

```bash
python scripts/office/unpack.py <input.pptx> <output_dir/>

# Exemplos:
python scripts/office/unpack.py template_padrao/local/local-corporate.pptx /tmp/unpacked/
python scripts/office/unpack.py test_output.pptx /tmp/debug_output/
```

**O que faz:** descompacta o PPTX, formata cada XML com `defusedxml.minidom` (indentação legível), salva em `output_dir/`.

---

### `scripts/office/pack.py` — Reempacotar XML em PPTX

Reempacota o diretório editado de volta para um PPTX válido.

```bash
python scripts/office/pack.py <unpacked_dir/> <output.pptx> [--original <template.pptx>]

# Exemplos:
python scripts/office/pack.py /tmp/unpacked/ output.pptx \
  --original template_padrao/local/local-corporate.pptx

python scripts/office/pack.py /tmp/unpacked/ /tmp/repack_test.pptx \
  --original template_padrao/local/local-corporate.pptx
```

**O flag `--original`:** copia metadados do template original (thumbnails, propriedades do documento) para o PPTX final. Sempre use quando disponível.

---

### `scripts/add_slide.py` — Adicionar/duplicar slide

Duplica um slide existente no diretório desempacotado, gerenciando corretamente rIds e Content_Types.

```bash
python scripts/add_slide.py <unpacked_dir/> <slide_index>

# Exemplos:
python scripts/add_slide.py /tmp/unpacked/ 2   # duplica slide 2 (0-based)
python scripts/add_slide.py /tmp/unpacked/ 0   # duplica slide de capa
```

**Usar ANTES de editar conteúdo.** Todas as mudanças estruturais (adicionar, remover, reordenar) devem ser feitas antes de editar XML de conteúdo.

---

### `scripts/clean.py` — Remover arquivos órfãos

Remove slides não referenciados em `presentation.xml` e mídia não referenciada por nenhum slide.

```bash
python scripts/clean.py <unpacked_dir/>

# Exemplos:
python scripts/clean.py /tmp/unpacked/
```

**Sempre rodar antes de `pack.py`** para evitar que o PPTX final carregue mídia desnecessária.

---

### `scripts/thumbnail.py` — Gerar thumbnails para QA

Converte o PPTX em um grid de imagens para inspeção visual. Requer LibreOffice (`soffice`) e `pdftoppm`. Degrada graciosamente se ausentes (retorna aviso, não falha).

```bash
python scripts/thumbnail.py <input.pptx> [output_image.jpg]

# Exemplos:
python scripts/thumbnail.py output.pptx
python scripts/thumbnail.py output.pptx /tmp/qa_grid.jpg
python scripts/thumbnail.py template_padrao/local/local-corporate.pptx  # inspecionar template
```

**Saída:** imagem JPEG com todos os slides em grid (4 colunas por padrão). Se LibreOffice não estiver disponível, exibe aviso e sugere instalação.

---

## QA visual — loop obrigatório

Todo PPTX gerado ou editado DEVE passar pelo loop de QA antes de ser entregue.

### Loop de QA

```
1. Gerar ou editar o PPTX
   python scripts/office/pack.py /tmp/unpacked/ output.pptx --original template.pptx

2. Converter para thumbnails
   python scripts/thumbnail.py output.pptx

3. Inspecionar CADA slide no thumbnail
   - Título visível e legível?
   - Bullets aparecem (não colados em string única)?
   - Sem texto placeholder (lorem ipsum, "Clique para editar")?
   - Sem shapes fora dos limites do slide?
   - Formatação preservada (fontes, cores, negrito)?
   - Smart quotes corretas (não aspas retas)?

4. Documentar todos os problemas encontrados
   - Ex: "Slide 3: bullets colados em string única"
   - Ex: "Slide 5: título truncado com '...'"

5. Corrigir no XML e re-empacotar

6. Repetir a partir do passo 1 até ZERO novos problemas
```

### Checks automáticos do StencilRenderer

O `StencilRenderer._qa_check()` emite warnings nos logs para:
- `ZONE_NOT_REPLACED`: shape com texto placeholder (lorem ipsum) em zona grande (>3% da área)
- `SHAPE_OUT_OF_BOUNDS`: shape com `left < -0.1` ou `top < -0.1`
- `TITLE_TOO_LONG`: título com mais de 80 caracteres
- `TOO_MANY_BULLETS`: mais de 8 bullets em um slide

Monitorar estes warnings nos logs do backend:
```bash
uvicorn main:app --reload --log-level debug 2>&1 | grep "QA \["
```

---

## Regras de formatação XML

Regras críticas para edição direta de XML de slides PPTX. Violações causam renderização incorreta ou PPTX corrompido.

### Regra 1: Parágrafos separados — NUNCA strings concatenadas

Cada item de lista, parágrafo ou linha de conteúdo deve ser um `<a:p>` separado.

**ERRADO** — tudo em uma string:
```xml
<a:p>
  <a:r>
    <a:rPr lang="pt-BR" sz="1800"/>
    <a:t>Passo 1: Fazer X. Passo 2: Fazer Y. Passo 3: Fazer Z.</a:t>
  </a:r>
</a:p>
```

**CORRETO** — parágrafos separados:
```xml
<a:p>
  <a:pPr algn="l"><a:lnSpc><a:spcPts val="3919"/></a:lnSpc></a:pPr>
  <a:r><a:rPr lang="pt-BR" sz="1800" b="1" dirty="0"/><a:t>Passo 1</a:t></a:r>
</a:p>
<a:p>
  <a:pPr algn="l"><a:lnSpc><a:spcPts val="3919"/></a:lnSpc></a:pPr>
  <a:r><a:rPr lang="pt-BR" sz="1800" dirty="0"/><a:t>Fazer X</a:t></a:r>
</a:p>
<a:p>
  <a:pPr algn="l"><a:lnSpc><a:spcPts val="3919"/></a:lnSpc></a:pPr>
  <a:r><a:rPr lang="pt-BR" sz="1800" dirty="0"/><a:t>Fazer Y</a:t></a:r>
</a:p>
```

---

### Regra 2: Bold obrigatório em headers, subheadings e labels inline

Use `b="1"` nos atributos `<a:rPr>` de títulos, subtítulos e labels.

```xml
<!-- Título: b="1" obrigatório -->
<a:r>
  <a:rPr lang="pt-BR" sz="2800" b="1" dirty="0"/>
  <a:t>Resultados do Trimestre</a:t>
</a:r>

<!-- Body/bullets: b="0" ou omitir b -->
<a:r>
  <a:rPr lang="pt-BR" sz="1800" dirty="0"/>
  <a:t>Volume cresceu 12% YoY</a:t>
</a:r>
```

---

### Regra 3: NUNCA usar bullets unicode — usar elementos XML de bullet

**ERRADO** — bullet unicode hardcoded:
```xml
<a:t>• Volume cresceu 12%</a:t>
<a:t>• NPS atingiu 78 pontos</a:t>
```

**CORRETO** — herdar bullet do layout (padrão):
```xml
<a:p>
  <a:pPr marL="342900" indent="-342900">
    <!-- sem <a:buChar> = herda do slideLayout -->
  </a:pPr>
  <a:r><a:rPr lang="pt-BR" sz="1800"/><a:t>Volume cresceu 12%</a:t></a:r>
</a:p>
```

**CORRETO** — especificar bullet explicitamente quando necessário:
```xml
<a:p>
  <a:pPr marL="342900" indent="-342900">
    <a:buChar char="&#x2022;"/>  <!-- bullet •, definido como entidade XML -->
  </a:pPr>
  <a:r><a:rPr lang="pt-BR" sz="1800"/><a:t>Volume cresceu 12%</a:t></a:r>
</a:p>
```

**CORRETO** — remover bullet (para parágrafo sem bullet):
```xml
<a:p>
  <a:pPr>
    <a:buNone/>
  </a:pPr>
  <a:r><a:rPr lang="pt-BR" sz="1800"/><a:t>Nota de rodapé sem bullet</a:t></a:r>
</a:p>
```

---

### Regra 4: Smart quotes como entidades XML

**ERRADO** — aspas retas ou unicode literal:
```xml
<a:t>"Transformação Digital" é prioridade</a:t>
<a:t>"Transformação Digital" é prioridade</a:t>
```

**CORRETO** — entidades XML:
```xml
<a:t>&#x201C;Transformação Digital&#x201D; é prioridade</a:t>
```

| Caractere | Entidade XML | Nome |
|---|---|---|
| `"` (abre) | `&#x201C;` | left double quotation mark |
| `"` (fecha) | `&#x201D;` | right double quotation mark |
| `'` (abre) | `&#x2018;` | left single quotation mark |
| `'` (fecha) | `&#x2019;` | right single quotation mark |
| `—` (em dash) | `&#x2014;` | em dash |

---

### Regra 5: `xml:space="preserve"` para espaços leading/trailing

```xml
<!-- ERRADO: espaço leading será trimado pelo parser XML -->
<a:t> Volume cresceu 12%</a:t>

<!-- CORRETO: preservar espaço explicitamente -->
<a:t xml:space="preserve"> Volume cresceu 12%</a:t>
```

Usar sempre que o texto tiver espaço no início ou no fim (comum em labels inline e separadores).

---

### Regra 6: Parse XML com `defusedxml.minidom` — NUNCA `xml.etree.ElementTree`

```python
# ERRADO — vulnerável a ataques XML (billion laughs, etc.)
import xml.etree.ElementTree as ET
tree = ET.parse("slide1.xml")

# CORRETO — parse seguro
import defusedxml.minidom
doc = defusedxml.minidom.parse("slide1.xml")
```

---

### Regra 7: Nunca editar slideLayouts ou slideMasters

Os arquivos em `ppt/slideLayouts/` e `ppt/slideMasters/` definem o tema e formatação padrão. Editá-los afeta todos os slides que herdam daquele layout/master.

Edite apenas os arquivos em `ppt/slides/slide*.xml`.

---

### Regra 8: Preservar namespaces XML

Ao inserir novos elementos, preservar os namespaces existentes. O namespace `a:` refere-se ao DrawingML:

```
xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
```

Nunca remover ou alterar declarações `xmlns:` no elemento raiz do XML.

---

## Anti-patterns

| Anti-pattern | Por que é errado | Alternativa correta |
|---|---|---|
| Concatenar bullets em string única | PowerPoint renderiza tudo em uma linha | `<a:p>` separado por item |
| Usar `•` unicode direto no `<a:t>` | Quebra hereditariedade de bullet do layout | `<a:buChar>` ou herdar do layout |
| Usar `xml.etree.ElementTree` | Vulnerável a ataques XML | `defusedxml.minidom` |
| Editar XML com `sed` ou `python -c` | Erro de escape, corrompe XML | EditTool diretamente no arquivo |
| Editar `slideLayouts/` ou `slideMasters/` | Afeta todos os slides | Editar apenas `slides/slide*.xml` |
| Omitir `--original` no `pack.py` | PPTX sem metadados/thumbnail correto | Sempre passar `--original template.pptx` |
| Entregar sem QA visual | Bugs de formatação não detectados | Sempre rodar `thumbnail.py` antes |
| Usar aspas retas `"` no XML | Não são smart quotes; falha no PowerPoint | Entidades `&#x201C;` / `&#x201D;` |
| Mudanças estruturais após editar conteúdo | rIds e Content_Types ficam inconsistentes | Mudanças estruturais PRIMEIRO |
| Copiar stencil Ambev enquanto OneDrive está sincronizando | `PermissionError` | `cp '<stencil.pptx>' $TEMP/ambev.pptx` antes |

---

## Exemplos de uso

### Criar apresentação nova via XML-based

```bash
# 1. Analisar o template disponível
python scripts/thumbnail.py template_padrao/local/local-corporate.pptx

# 2. Desempacotar
python scripts/office/unpack.py template_padrao/local/local-corporate.pptx /tmp/novo_deck/

# 3. Verificar slides disponíveis no stencil
ls /tmp/novo_deck/ppt/slides/

# 4. Adicionar slides necessários (ex: 5 slides de conteúdo)
python scripts/add_slide.py /tmp/novo_deck/ 1  # duplica slide de conteúdo
python scripts/add_slide.py /tmp/novo_deck/ 1
python scripts/add_slide.py /tmp/novo_deck/ 1

# 5. Editar XML de cada slide (usar EditTool)
# Editar /tmp/novo_deck/ppt/slides/slide2.xml: substituir título e bullets

# 6. Limpar e empacotar
python scripts/clean.py /tmp/novo_deck/
python scripts/office/pack.py /tmp/novo_deck/ output_novo.pptx \
  --original template_padrao/local/local-corporate.pptx

# 7. QA visual
python scripts/thumbnail.py output_novo.pptx
```

---

### Inspecionar e debugar um PPTX existente

```bash
# Ver thumbnails de qualquer PPTX
python scripts/thumbnail.py test_stencil_output.pptx

# Desempacotar para inspecionar XML
python scripts/office/unpack.py test_api_output.pptx /tmp/debug/

# Inspecionar XML de um slide específico
# (usar Read tool em /tmp/debug/ppt/slides/slide3.xml)

# Inspecionar relacionamentos
# (usar Read tool em /tmp/debug/ppt/slides/_rels/slide3.xml.rels)
```

---

### Testar os 3 caminhos de renderização via API

```bash
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Testar caminho XML (preferido)
PPTX_RENDERER=xml curl -X POST http://localhost:8000/api/v1/generate-pptx \
  -H "Content-Type: application/json" \
  -d '{"storytelling": {"title": "Resultados Q1", "slides": [...]}, "template_id": "local-corporate"}' \
  --output test_xml.pptx

# Testar thumbnail endpoint (requer LibreOffice)
curl -X POST http://localhost:8000/api/v1/generate-pptx/thumbnail \
  -H "Content-Type: application/json" \
  -d '{"storytelling": {...}, "template_id": "local-corporate"}' \
  --output thumbnails.jpg

# Verificar scripts diretos
python scripts/thumbnail.py template_padrao/local/local-corporate.pptx
python scripts/office/unpack.py template_padrao/local/local-corporate.pptx /tmp/test_unpack/
python scripts/clean.py /tmp/test_unpack/
python scripts/office/pack.py /tmp/test_unpack/ /tmp/repack_test.pptx \
  --original template_padrao/local/local-corporate.pptx
```

---

### Corrigir OneDrive bloqueando o stencil Ambev

```bash
# Copiar stencil para diretório temporário (fora do OneDrive)
cp "template_padrao/local/example/Template Ambev_atualizado_ - Copia.pptx" \
   "$TEMP/ambev.pptx"

# O _open_pptx_safe() em render_from_template.py detecta automaticamente
# a cópia em $TEMP quando o original está bloqueado
```

---

## Dependências necessárias

```
# requirements.txt do backend
defusedxml>=0.7.1    # parse XML seguro (scripts/office/unpack.py, xml_renderer.py)
Pillow>=10.0.0       # montagem do grid de thumbnails (scripts/thumbnail.py)
python-pptx>=0.6.21  # StencilRenderer e programmatic path

# Ferramentas externas (opcionais — thumbnail.py degrada sem elas)
# LibreOffice (soffice) — converte PPTX → PDF
# pdftoppm (poppler-utils) — converte PDF → imagens PNG
```

Instalar dependências Python:
```bash
cd backend && pip install -r requirements.txt
```

Instalar LibreOffice (para QA visual):
```bash
# Ubuntu/Debian
sudo apt-get install libreoffice poppler-utils

# macOS
brew install libreoffice poppler

# Windows: baixar de https://www.libreoffice.org/download/
# Adicionar C:\Program Files\LibreOffice\program ao PATH
```
