# Roteiro otimizado — PDVs do CDD Diadema (UNB 216)

Gera uma lista de PDVs em ordem otimizada, pronta para importar no Google My Maps
e para abrir como rota no Google Maps.

Fonte dos dados: base TSV embutida na página <https://carlosorledo.github.io/mapa-rota/>
(bloco `var BASE = ...` no `index.html`). Nenhum dado é inventado — o script lê a
página e filtra pela UNB.

## O recorte

| Nível | PDVs |
|---|---|
| Base inteira do site (8 operações, 58 setores) | 7.096 |
| **CDD Diadema — UNB 216** (usado aqui) | **1.459** |
| Só o município de Diadema | 123 |

O CDD Diadema atende São Paulo zona sul (746), Santo André (295), São Bernardo do
Campo (283), Diadema (123), São Caetano do Sul (10) e 2 registros sem cidade.
O mapeamento `216 → CDD Diadema` vem da própria função `operacaoDe()` do site.
Os números conferem com o que o app mostra na tela: `1459 PDV(s) exibido(s) de 7096`.

## Modelo de rota (híbrido: carro entre bolsões, a pé dentro)

PDVs a até 150 m um do outro viram um **bolsão**. O carro para no PDV mais central
do bolsão, o miolo é feito a pé em circuito fechado e volta-se ao carro.

O raio de 150 m não foi chutado: foi calibrado varrendo raios de 0 a 600 m e
estimando o tempo total (22 km/h no trânsito urbano, 4,5 km/h a pé, 4 min de
estacionamento por parada, distância por via ≈ 1,35× a linha reta).

| Raio do bolsão | Bolsões | km carro | km a pé | Tempo estimado |
|---|---|---|---|---|
| 0 m (só carro) | 1.459 | 762 | 0 | 131,9 h |
| **150 m** | **1.105** | **727** | **71** | **122,4 h** |
| 300 m | 786 | 668 | 243 | 136,9 h |
| 600 m | 430 | 531 | 545 | 173,8 h |

Bolsões maiores reduzem o tempo dirigindo, mas o que se ganha aí se perde andando.
O ótimo é raso (100–200 m) e o ganho sobre a rota só de carro é de ~8%.

## Como rodar

```bash
git clone --depth 1 https://github.com/carlosorledo/mapa-rota /tmp/mapa-rota

python3 build_rota.py \
  --html /tmp/mapa-rota/index.html \
  --unb 216 \
  --origem="-23.6862,-46.6222" \
  --rotulo-origem "Minha origem" \
  --saida saida
```

O `=` em `--origem=` é obrigatório: sem ele o `-23...` é lido como nome de opção.

Opções: `--raio-bolsao` (km, padrão 0.15), `--max-pdv-bolsao` (padrão 8),
`--unb`. UNBs presentes na base: 216 Diadema, 301 Mauá, 401 Mooca/Capital
(divide pelo setor: <500 Mooca, >=500 Capital), 538 Jacarepaguá, 541 Santa Luzia,
710 Brasília, 928 Blumenau. A função `operacaoDe()` do site também define 71
Salvador e 352 Fortaleza, mas nenhum PDV da base pertence a essas duas — daí o
cabeçalho do app dizer 8 operações, e não 9.

## Saídas

| Arquivo | O que é |
|---|---|
| `rota_otimizada.csv` | 1.459 linhas na ordem da rota: ordem, bolsão, modo de chegada, nome, endereço, cidade, lat/lon, telefone, setor, id_vd, melhor dia |
| `bolsoes.csv` | 1 linha por bolsão: onde estacionar, quantos PDVs, km do circuito a pé |
| `mymaps_completo.csv` | importável no Google My Maps (nome já prefixado com a ordem) |
| `mymaps_setor_<s>.csv` | idem, um por setor — útil porque o My Maps só aceita 10 camadas |
| `links_google_maps.md` | links `maps/dir/` prontos: blocos de carro entre bolsões + um circuito a pé por bolsão |

### Importar no Google My Maps

1. <https://mymaps.google.com> → **Criar novo mapa** → **Importar**
2. Suba `mymaps_completo.csv` (ou um `mymaps_setor_*.csv`)
3. Colunas de posição: `Latitude` e `Longitude`; título do marcador: `Nome`
4. Estilize por `Setor`, `Melhor dia` ou `Bolsao`

O My Maps plota os pontos mas **não traça nem otimiza rota** — a ordem já vem
resolvida no nome (`0001 - ...`) e nos links de `links_google_maps.md`.

## Limitações conhecidas

- Distâncias são em linha reta (haversine) com fator 1,35 para aproximar a via.
  Não há chamada a API de rotas, então rio, viaduto e mão de direção não entram na conta.
- A otimização é vizinho-mais-próximo + 2-opt: uma boa heurística, não o ótimo global.
- O Google Maps aceita ~9 paradas por rota, daí os blocos.
- Sem janelas de atendimento: o campo `melhor_dia` vai no CSV mas não restringe a ordem.
