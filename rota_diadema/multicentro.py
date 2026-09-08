#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roteiro com carro SO entre grandes centros (concentracoes densas de PDVs) e
tudo a pe dentro de cada centro.

Busca em feixe: a cada passo o estado pode andar ate um PDV vizinho ou dirigir
ate outro centro. Quem decide e o orcamento de tempo, nao uma regra fixa.
"""
import argparse, csv, json, os

import build_rota as br
import hotspot as hs

H = br.haversine


def _peso(est):
    """Desempate entre rotas com o mesmo numero de visitas: menos carro, e mais cedo."""
    return (sum(1 for t in est[3] if t[1] == "carro"), est[0])


def acha_centros(coords, grade, raio, quantos):
    """Centros = maiores concentracoes de PDVs dentro de `raio`, sem sobreposicao."""
    dens = []
    for i, c in enumerate(coords):
        n = sum(1 for j in grade.perto(c[0], c[1], raio) if H(c, coords[j]) <= raio)
        dens.append((n, i))
    dens.sort(reverse=True)
    centros, tomados = [], set()
    for n, i in dens:
        if len(centros) >= quantos:
            break
        c = coords[i]
        membros = [j for j in grade.perto(c[0], c[1], raio) if H(c, coords[j]) <= raio]
        if any(j in tomados for j in membros):
            continue
        centros.append({"n": n, "ancora": i, "membros": membros})
        tomados.update(membros)
    return centros


def busca(origem, coords, grade, centros, minutos, t_visita, mpk_pe, mpk_car,
          raio_pe, feixe, min_carro):
    # o carro so encosta na ancora de um centro, e so se o salto for de verdade:
    # abaixo de `min_carro` a pe resolve, e dirigir vira atalho para cruzar a rua
    alvos_carro = sorted({c["ancora"] for c in centros})
    inicial = (0.0, origem, frozenset(), ())
    nivel = [inicial]
    melhor = inicial
    while nivel:
        prox = {}
        for tempo, pos, feitos, trilha in nivel:
            vizinhos = [(j, "a pe", mpk_pe)
                        for j in grade.perto(pos[0], pos[1], raio_pe)
                        if j not in feitos and H(pos, coords[j]) <= raio_pe]
            vizinhos += [(j, "carro", mpk_car) for j in alvos_carro
                         if j not in feitos and H(pos, coords[j]) >= min_carro]
            for j, modo, mpk in vizinhos:
                custo = H(pos, coords[j]) * mpk + t_visita
                t = tempo + custo
                if t > minutos:
                    continue
                novos = feitos | {j}
                chave = (j, novos)
                est = (t, coords[j], novos, trilha + ((j, modo, round(custo, 2)),))
                if chave not in prox or _peso(est) < _peso(prox[chave]):
                    prox[chave] = est
        if not prox:
            break
        ordenado = sorted(prox.values(), key=lambda e: (-len(e[2]),) + _peso(e))
        nivel = ordenado[:feixe]
        if (len(nivel[0][2]),) + tuple(-x for x in _peso(nivel[0])) > \
           (len(melhor[2]),) + tuple(-x for x in _peso(melhor)):
            melhor = nivel[0]
    return melhor


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True)
    ap.add_argument("--unb", default="216")
    ap.add_argument("--origem", required=True)
    ap.add_argument("--minutos", type=float, default=180.0)
    ap.add_argument("--t-visita", type=float, default=7.0)
    ap.add_argument("--conversao", type=float, default=0.10)
    ap.add_argument("--v-pe", type=float, default=4.5)
    ap.add_argument("--v-carro", type=float, default=22.0)
    ap.add_argument("--raio-centro", type=float, default=0.4, help="km")
    ap.add_argument("--raio-pe", type=float, default=0.8, help="km, salto maximo a pe")
    ap.add_argument("--min-carro", type=float, default=1.5,
                    help="km, salto minimo para justificar pegar o carro")
    ap.add_argument("--centros", type=int, default=20)
    ap.add_argument("--feixe", type=int, default=400)
    ap.add_argument("--saida", default="saida")
    ap.add_argument("--arquivo", default="rota_multicentro.csv")
    args = ap.parse_args()

    origem = tuple(float(x) for x in args.origem.split(","))
    pdvs = br.carrega_base(args.html, args.unb)
    coords = [(p["lat"], p["lon"]) for p in pdvs]
    grade = hs.Grade(coords)
    mpk_pe = 60.0 / args.v_pe * br.FATOR_RUA
    mpk_car = 60.0 / args.v_carro * br.FATOR_RUA

    centros = acha_centros(coords, grade, args.raio_centro, args.centros)
    tempo, _, feitos, trilha = busca(origem, coords, grade, centros, args.minutos,
                                     args.t_visita, mpk_pe, mpk_car, args.raio_pe,
                                     args.feixe, args.min_carro)

    de_carro = [t for t in trilha if t[1] == "carro"]
    km_pe = km_car = 0.0
    pos = origem
    for j, modo, _ in trilha:
        d = H(pos, coords[j])
        if modo == "carro":
            km_car += d
        else:
            km_pe += d
        pos = coords[j]
    print("%d visitas em %.0f de %.0f min | %.1f conversoes esperadas"
          % (len(trilha), tempo, args.minutos, len(trilha) * args.conversao))
    print("%d trechos de carro (%.1f km) | %.2f km a pe (%.0f m por parada)"
          % (len(de_carro), km_car * br.FATOR_RUA, km_pe * br.FATOR_RUA,
             km_pe * br.FATOR_RUA * 1000 / max(len(trilha) - len(de_carro), 1)))

    linhas, pos, t, bloco = [], origem, 0.0, 0
    for k, (j, modo, custo) in enumerate(trilha, 1):
        p = pdvs[j]
        d = H(pos, coords[j])
        if modo == "carro":
            bloco += 1
        t += custo
        linhas.append({"parada": k, "bloco": bloco, "chegada_por": modo,
                       "desloc_min": round(custo - args.t_visita, 1),
                       "desloc_m": round(d * br.FATOR_RUA * 1000),
                       "chega_min": round(t - args.t_visita), "sai_min": round(t),
                       "nome": p["name"], "endereco": p["address_complete"],
                       "cidade": p["city"],
                       "telefone": p["nationalPhoneNumber"] or "-",
                       "setor": p["setor"], "melhor_dia": p["melhor_dia_semana"],
                       "lat": p["lat"], "lon": p["lon"],
                       "link": "https://www.google.com/maps/search/?api=1&query=%s,%s"
                               % (p["lat"], p["lon"])})
        pos = coords[j]
    os.makedirs(args.saida, exist_ok=True)
    with open(os.path.join(args.saida, args.arquivo), "w", newline="",
              encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0].keys()))
        w.writeheader(); w.writerows(linhas)
    for l in linhas:
        marca = ">> CARRO" if l["chegada_por"] == "carro" else "        "
        print("%s %2d | %3d-%3d min | %5s %4dm | %-32s | %s"
              % (marca, l["parada"], l["chega_min"], l["sai_min"],
                 "%.1f'" % l["desloc_min"], l["desloc_m"], l["nome"][:32],
                 l["endereco"][:40]))
    print("\ngravado em %s" % os.path.join(os.path.abspath(args.saida), args.arquivo))


if __name__ == "__main__":
    main()
