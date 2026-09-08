#!/bin/sh
# Regera o roteiro. Ajuste ORIGEM se o ponto de partida mudar.
set -e

ORIGEM="-23.683943,-46.516692"
ROTULO="R. das Hortencias, 841 - Jardim do Estadio, Santo Andre - SP"
# Coordenada interpolada a partir de 4 PDVs da propria base na mesma rua
# (nos 585, 721, 892 e 906); numeracao linear a ~0.9 m por numero, erro ~20 m.

BASE="${BASE:-/tmp/mapa-rota}"
[ -d "$BASE" ] || git clone --depth 1 https://github.com/carlosorledo/mapa-rota "$BASE"

python3 build_rota.py \
  --html "$BASE/index.html" \
  --unb "${UNB:-216}" \
  --origem="$ORIGEM" \
  --rotulo-origem "$ROTULO" \
  --saida "${SAIDA:-saida}"
