#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roteiro otimizado para os PDVs de uma UNB da base embutida em
https://carlosorledo.github.io/mapa-rota/

Modelo hibrido (park-and-walk): o carro para no ancora do bolsao, o miolo do
bolsao e feito a pe em circuito fechado, volta-se ao carro e segue para o
proximo bolsao.

Saidas (em --saida):
  rota_otimizada.csv        ordem global, 1 linha por PDV
  bolsoes.csv               1 linha por bolsao (ponto de estacionamento)
  mymaps_completo.csv       importavel no Google My Maps
  mymaps_setor_<s>.csv      idem, quebrado por setor
  links_google_maps.md      links de rota de carro (ancoras) e a pe (circuitos)
"""
import csv, math, os, sys, argparse
from collections import defaultdict

R_TERRA = 6371.0088
MAX_PARADAS_LINK = 9          # limite pratico de waypoints por rota no Google Maps
FATOR_RUA = 1.35              # linha reta -> distancia aproximada por via

CAMPOS = ["unb","setor","pdv","id_vd","address_complete","name","city","lat","lon",
          "nationalPhoneNumber","uf","score_threshold","open_probability_score",
          "visitas_tt","visitas_tt_gps_ok","motivos_nao_cadastro_str","melhor_dia_semana"]


def haversine(a, b):
    la1, lo1 = math.radians(a[0]), math.radians(a[1])
    la2, lo2 = math.radians(b[0]), math.radians(b[1])
    h = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*R_TERRA*math.asin(math.sqrt(h))


def carrega_base(caminho_html, unb_alvo):
    """Extrai o bloco TSV embutido na pagina (var BASE = `...`)."""
    with open(caminho_html, encoding="utf-8") as fh:
        linhas = fh.read().split("\n")
    try:
        ini = next(i for i, l in enumerate(linhas) if l.startswith("unb\tsetor\tpdv\t"))
    except StopIteration:
        sys.exit("cabecalho da base nao encontrado no HTML")
    registros = []
    for linha in linhas[ini+1:]:
        col = linha.split("\t")
        if len(col) < len(CAMPOS) - 3:
            break
        if col[0] != unb_alvo:
            continue
        col += [""] * (len(CAMPOS) - len(col))
        r = dict(zip(CAMPOS, col[:len(CAMPOS)]))
        try:
            r["lat"], r["lon"] = float(r["lat"]), float(r["lon"])
        except ValueError:
            continue
        for k in ("city", "nationalPhoneNumber"):
            if r[k] == "null":
                r[k] = ""
        registros.append(r)
    return registros


def clusteriza(pdvs, raio_km, teto):
    """Bolsoes caminhaveis: guloso, ancorado no PDV livre mais ao norte."""
    livres = sorted(range(len(pdvs)), key=lambda i: (-pdvs[i]["lat"], pdvs[i]["lon"]))
    pendentes = set(livres)
    clusters = []
    for semente in livres:
        if semente not in pendentes:
            continue
        pendentes.discard(semente)
        grupo = [semente]
        ancora = (pdvs[semente]["lat"], pdvs[semente]["lon"])
        vizinhos = sorted(pendentes,
                          key=lambda j: haversine(ancora, (pdvs[j]["lat"], pdvs[j]["lon"])))
        for j in vizinhos:
            if len(grupo) >= teto:
                break
            if haversine(ancora, (pdvs[j]["lat"], pdvs[j]["lon"])) <= raio_km:
                grupo.append(j)
                pendentes.discard(j)
            else:
                break
        clusters.append(grupo)
    return clusters


def _vizinho_mais_proximo(coords, origem):
    restantes = set(range(len(coords)))
    atual, ordem = origem, []
    while restantes:
        prox = min(restantes, key=lambda i: haversine(atual, coords[i]))
        ordem.append(prox)
        restantes.discard(prox)
        atual = coords[prox]
    return ordem


def _dois_opt(ordem, coords, origem, fim=None, max_passes=50):
    """2-opt. origem e fixa; se `fim` for dado a rota e um circuito que volta a ele."""
    def custo_borda(p, q):
        return haversine(p, q)
    melhorou, passe = True, 0
    while melhorou and passe < max_passes:
        melhorou, passe = False, passe + 1
        n = len(ordem)
        for i in range(n - 1):
            ant = origem if i == 0 else coords[ordem[i-1]]
            for k in range(i + 1, n):
                depois = coords[ordem[k+1]] if k + 1 < n else fim
                antes = custo_borda(ant, coords[ordem[i]])
                agora = custo_borda(ant, coords[ordem[k]])
                if depois is not None:
                    antes += custo_borda(coords[ordem[k]], depois)
                    agora += custo_borda(coords[ordem[i]], depois)
                if agora < antes - 1e-9:
                    ordem[i:k+1] = reversed(ordem[i:k+1])
                    melhorou = True
    return ordem


def resolve(coords, origem, fim=None):
    if not coords:
        return []
    return _dois_opt(_vizinho_mais_proximo(coords, origem), coords, origem, fim)


def _xml(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def escreve_kml(caminho, linhas, bolsoes, origem, rotulo_origem, titulo):
    """KML para importar no Google My Maps em um clique.

    Duas pastas = duas camadas: os PDVs (com ExtendedData, que o My Maps vira
    coluna e permite estilizar por setor/dia) e a linha do trajeto de carro.
    """
    campos = [("Ordem", "ordem"), ("Bolsao", "bolsao"), ("Modo", "modo"),
              ("Setor", "setor"), ("Cidade", "cidade"), ("Melhor dia", "melhor_dia"),
              ("Telefone", "telefone"), ("Endereco", "endereco"), ("id_vd", "id_vd")]
    p = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
         "<name>%s</name>" % _xml(titulo),
         '<Style id="parar"><IconStyle><color>ff0000ff</color><scale>1.1</scale>'
         '<Icon><href>http://maps.google.com/mapfiles/kml/paddle/red-circle.png</href></Icon>'
         "</IconStyle></Style>",
         '<Style id="andar"><IconStyle><color>ff00aa00</color><scale>0.9</scale>'
         '<Icon><href>http://maps.google.com/mapfiles/kml/paddle/grn-blank.png</href></Icon>'
         "</IconStyle></Style>",
         '<Style id="linha"><LineStyle><color>ffff6414</color><width>3</width></LineStyle></Style>',
         "<Folder><name>PDVs na ordem da rota</name>",
         "<Placemark><name>0000 - ORIGEM</name><description>%s</description>"
         "<Point><coordinates>%s,%s,0</coordinates></Point></Placemark>"
         % (_xml(rotulo_origem), origem[1], origem[0])]
    for l in linhas:
        p.append("<Placemark><name>%04d - %s</name><styleUrl>#%s</styleUrl>"
                 % (l["ordem"], _xml(l["nome"]),
                    "andar" if l["modo"] == "a pe" else "parar"))
        p.append("<description>%s%s | setor %s | %s | bolsao %d</description>"
                 % (_xml(l["endereco"]),
                    " | tel " + _xml(l["telefone"]) if l["telefone"] else "",
                    _xml(l["setor"]), _xml(l["melhor_dia"]), l["bolsao"]))
        p.append("<ExtendedData>")
        for rotulo, chave in campos:
            p.append("<Data name=\"%s\"><value>%s</value></Data>"
                     % (rotulo, _xml(l[chave])))
        p.append("</ExtendedData>")
        p.append("<Point><coordinates>%s,%s,0</coordinates></Point></Placemark>"
                 % (l["lon"], l["lat"]))
    p.append("</Folder>")
    p.append("<Folder><name>Trajeto de carro</name><Placemark>"
             "<name>Trajeto entre bolsoes</name><styleUrl>#linha</styleUrl><LineString>"
             "<tessellate>1</tessellate><coordinates>")
    p.append(" ".join(["%s,%s,0" % (origem[1], origem[0])]
                      + ["%s,%s,0" % (b["estacionar_lon"], b["estacionar_lat"])
                         for b in bolsoes]))
    p.append("</coordinates></LineString></Placemark></Folder>")
    p.append("</Document></kml>")
    with open(caminho, "w", encoding="utf-8") as fh:
        fh.write("\n".join(p))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True)
    ap.add_argument("--unb", default="216")
    ap.add_argument("--origem", required=True, help="lat,lon do ponto de partida")
    ap.add_argument("--rotulo-origem", default="Origem")
    ap.add_argument("--raio-bolsao", type=float, default=0.15, help="km caminhaveis")
    ap.add_argument("--max-pdv-bolsao", type=int, default=8)
    ap.add_argument("--saida", default=".")
    args = ap.parse_args()

    origem = tuple(float(x) for x in args.origem.split(","))
    pdvs = carrega_base(args.html, args.unb)
    print("PDVs carregados (UNB %s): %d" % (args.unb, len(pdvs)))

    clusters = clusteriza(pdvs, args.raio_bolsao, args.max_pdv_bolsao)
    # ancora = PDV do bolsao mais proximo do centroide: e onde o carro para
    ancoras = []
    for g in clusters:
        cy = sum(pdvs[i]["lat"] for i in g) / len(g)
        cx = sum(pdvs[i]["lon"] for i in g) / len(g)
        melhor = min(g, key=lambda i: haversine((cy, cx), (pdvs[i]["lat"], pdvs[i]["lon"])))
        ancoras.append((pdvs[melhor]["lat"], pdvs[melhor]["lon"]))
    print("bolsoes caminhaveis: %d (media %.1f PDVs/bolsao)"
          % (len(clusters), len(pdvs) / len(clusters)))

    ordem_bolsoes = resolve(ancoras, origem)

    linhas, bolsoes_out = [], []
    km_carro = km_pe = 0.0
    ponto_carro, seq = origem, 0
    for pos_bolsao, ic in enumerate(ordem_bolsoes, 1):
        grupo, ancora = clusters[ic], ancoras[ic]
        km_carro += haversine(ponto_carro, ancora)
        coords = [(pdvs[i]["lat"], pdvs[i]["lon"]) for i in grupo]
        # circuito a pe: sai do carro (ancora), passa por todos, volta ao carro
        ordem_interna = resolve(coords, ancora, fim=ancora)
        anterior, km_loop = ancora, 0.0
        primeiro_seq = seq + 1
        for pos_local, idx_local in enumerate(ordem_interna, 1):
            p = pdvs[grupo[idx_local]]
            atual = (p["lat"], p["lon"])
            trecho = haversine(anterior, atual)
            km_loop += trecho
            seq += 1
            linhas.append({
                "ordem": seq,
                "bolsao": pos_bolsao,
                "parada_no_bolsao": pos_local,
                "modo": "carro (estacionar)" if pos_local == 1 else "a pe",
                "km_do_anterior_a_pe": round(trecho, 3),
                "nome": p["name"],
                "endereco": p["address_complete"],
                "cidade": p["city"],
                "uf": p["uf"],
                "lat": p["lat"],
                "lon": p["lon"],
                "telefone": p["nationalPhoneNumber"],
                "setor": p["setor"],
                "id_vd": p["id_vd"],
                "melhor_dia": p["melhor_dia_semana"],
                "place_id_ambev": p["pdv"],
                "link_maps": "https://www.google.com/maps/search/?api=1&query=%s,%s"
                             % (p["lat"], p["lon"]),
            })
            anterior = atual
        km_loop += haversine(anterior, ancora)   # volta ao carro
        km_pe += km_loop
        bolsoes_out.append({
            "bolsao": pos_bolsao,
            "pdvs": len(grupo),
            "primeira_ordem": primeiro_seq,
            "ultima_ordem": seq,
            "estacionar_lat": ancora[0],
            "estacionar_lon": ancora[1],
            "km_de_carro_ate_aqui": round(haversine(ponto_carro, ancora), 3),
            "km_do_circuito_a_pe": round(km_loop, 3),
            "setores": "/".join(sorted({pdvs[i]["setor"] for i in grupo})),
            "cidades": "/".join(sorted({pdvs[i]["city"] for i in grupo if pdvs[i]["city"]})),
            "link_estacionamento": "https://www.google.com/maps/search/?api=1&query=%s,%s"
                                   % (ancora[0], ancora[1]),
        })
        ponto_carro = ancora

    os.makedirs(args.saida, exist_ok=True)

    def grava(nome, dados):
        with open(os.path.join(args.saida, nome), "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=list(dados[0].keys()))
            w.writeheader(); w.writerows(dados)

    grava("rota_otimizada.csv", linhas)
    grava("bolsoes.csv", bolsoes_out)

    def escreve_mymaps(nome, dados):
        with open(os.path.join(args.saida, nome), "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.writer(fh)
            w.writerow(["Nome", "Latitude", "Longitude", "Endereco", "Telefone",
                        "Setor", "Cidade", "Melhor dia", "Ordem", "Bolsao", "Modo"])
            for l in dados:
                w.writerow(["%04d - %s" % (l["ordem"], l["nome"]), l["lat"], l["lon"],
                            l["endereco"], l["telefone"], l["setor"], l["cidade"],
                            l["melhor_dia"], l["ordem"], l["bolsao"], l["modo"]])

    escreve_mymaps("mymaps_completo.csv", linhas)
    escreve_kml(os.path.join(args.saida, "rota_mymaps.kml"), linhas, bolsoes_out,
                origem, args.rotulo_origem, "Rota otimizada - UNB %s" % args.unb)
    por_setor = defaultdict(list)
    for l in linhas:
        por_setor[l["setor"]].append(l)
    for setor, dados in sorted(por_setor.items()):
        escreve_mymaps("mymaps_setor_%s.csv" % setor, dados)

    por_bolsao = defaultdict(list)
    for l in linhas:
        por_bolsao[l["bolsao"]].append(l)

    with open(os.path.join(args.saida, "links_google_maps.md"), "w", encoding="utf-8") as fh:
        fh.write("# Roteiro otimizado - UNB %s\n\n" % args.unb)
        fh.write("Origem: **%s** (`%s`)\n\n" % (args.rotulo_origem, args.origem))
        fh.write("Modelo hibrido: o carro para no ponto de estacionamento de cada bolsao, "
                 "o miolo e feito a pe em circuito e volta-se ao carro.\n"
                 "O Google Maps aceita ~%d paradas por rota, entao o trajeto de carro vai "
                 "em blocos de %d bolsoes.\n\n" % (MAX_PARADAS_LINK, MAX_PARADAS_LINK))

        fh.write("## Trajeto de carro (entre bolsoes)\n\n")
        anteriores = args.origem
        rotulo_anterior = args.rotulo_origem
        for ini in range(0, len(bolsoes_out), MAX_PARADAS_LINK):
            bloco = bolsoes_out[ini:ini + MAX_PARADAS_LINK]
            pontos = [anteriores] + ["%s,%s" % (b["estacionar_lat"], b["estacionar_lon"])
                                     for b in bloco]
            url = ("https://www.google.com/maps/dir/?api=1&origin=%s&destination=%s"
                   "&waypoints=%s&travelmode=driving"
                   % (pontos[0], pontos[-1], "%7C".join(pontos[1:-1])))
            fh.write("### Carro, bloco %d - bolsoes %d a %d\n\n"
                     % (ini // MAX_PARADAS_LINK + 1, bloco[0]["bolsao"], bloco[-1]["bolsao"]))
            fh.write("Sai de: %s\n\n" % rotulo_anterior)
            for b in bloco:
                fh.write("- **Bolsao %d** - %d PDV(s), paradas %d a %d, circuito a pe %.2f km "
                         "(setor %s | %s)\n"
                         % (b["bolsao"], b["pdvs"], b["primeira_ordem"], b["ultima_ordem"],
                            b["km_do_circuito_a_pe"], b["setores"], b["cidades"] or "-"))
            fh.write("\n<%s>\n\n" % url)
            anteriores = pontos[-1]
            rotulo_anterior = "Bolsao %d" % bloco[-1]["bolsao"]

        fh.write("\n## Circuitos a pe (dentro de cada bolsao)\n\n")
        for b in bolsoes_out:
            paradas = por_bolsao[b["bolsao"]]
            fh.write("### Bolsao %d - %d PDV(s), %.2f km a pe\n\n"
                     % (b["bolsao"], b["pdvs"], b["km_do_circuito_a_pe"]))
            fh.write("Estacionar em: <%s>\n\n" % b["link_estacionamento"])
            for l in paradas:
                fh.write("%d. **%s** - %s%s\n"
                         % (l["ordem"], l["nome"], l["endereco"],
                            " - tel %s" % l["telefone"] if l["telefone"] else ""))
            if len(paradas) > 1:
                pontos = ["%s,%s" % (b["estacionar_lat"], b["estacionar_lon"])]
                pontos += ["%s,%s" % (l["lat"], l["lon"]) for l in paradas]
                pontos.append(pontos[0])
                pontos = pontos[:MAX_PARADAS_LINK + 2]
                fh.write("\n<https://www.google.com/maps/dir/?api=1&origin=%s&destination=%s"
                         "&waypoints=%s&travelmode=walking>\n"
                         % (pontos[0], pontos[-1], "%7C".join(pontos[1:-1])))
            fh.write("\n")

    print("paradas no roteiro: %d" % len(linhas))
    print("linha reta: %.1f km de carro + %.1f km a pe" % (km_carro, km_pe))
    print("estimativa por via (x%.2f): %.0f km de carro + %.0f km a pe"
          % (FATOR_RUA, km_carro * FATOR_RUA, km_pe * FATOR_RUA))
    print("arquivos gravados em %s" % os.path.abspath(args.saida))


if __name__ == "__main__":
    main()
