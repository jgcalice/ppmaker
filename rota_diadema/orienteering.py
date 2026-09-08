#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roteiro a pe sob orcamento de tempo (problema de orientacao / prize-collecting).

O guloso puro anda demais porque nunca revisa a ordem. Aqui o ciclo e:
  2-opt para desfazer cruzamentos -> sobra tempo -> insere mais paradas ->
  2-opt de novo -> ate nao caber mais nada.
"""
import argparse, csv, math, os
from collections import defaultdict

import build_rota as br
import hotspot as hs

H = br.haversine


def custo(tour, coords, mpk, t_visita):
    t = t_visita * len(tour)
    for k in range(len(tour) - 1):
        t += H(coords[tour[k]], coords[tour[k+1]]) * mpk
    return t


def melhora_ordem(tour, coords):
    """2-opt no trecho apos a primeira parada, que fica ancorada."""
    if len(tour) < 4:
        return tour
    resto = br._dois_opt(list(tour[1:]), coords, coords[tour[0]])
    return [tour[0]] + resto


def candidatos(tour, coords, grade, raio=0.7):
    vistos, saida = set(tour), set()
    for j in tour:
        for c in grade.perto(coords[j][0], coords[j][1], raio):
            if c not in vistos:
                saida.add(c)
    return saida


def insere_melhor(tour, coords, grade, mpk, t_visita, folga):
    """Insercao mais barata: menor tempo adicional por parada ganha."""
    melhor = None
    for v in candidatos(tour, coords, grade):
        for pos in range(1, len(tour) + 1):
            a = coords[tour[pos-1]]
            if pos == len(tour):
                extra = H(a, coords[v]) * mpk + t_visita
            else:
                b = coords[tour[pos]]
                extra = (H(a, coords[v]) + H(coords[v], b) - H(a, b)) * mpk + t_visita
            if extra <= folga and (melhor is None or extra < melhor[0]):
                melhor = (extra, pos, v)
    if melhor is None:
        return None
    _, pos, v = melhor
    return tour[:pos] + [v] + tour[pos:]


def resolve(inicio, minutos, coords, grade, mpk, t_visita, rodadas=60):
    tour = [inicio]
    for _ in range(rodadas):
        tour = melhora_ordem(tour, coords)
        folga = minutos - custo(tour, coords, mpk, t_visita)
        novo = insere_melhor(tour, coords, grade, mpk, t_visita, folga)
        if novo is None:
            break
        tour = novo
    return melhora_ordem(tour, coords)


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
    ap.add_argument("--sementes", type=int, default=60,
                    help="quantos pontos de partida refinar com o solver")
    ap.add_argument("--saida", default="saida")
    ap.add_argument("--arquivo", default="rota_a_pe.csv")
    args = ap.parse_args()

    origem = tuple(float(x) for x in args.origem.split(","))
    pdvs = br.carrega_base(args.html, args.unb)
    coords = [(p["lat"], p["lon"]) for p in pdvs]
    grade = hs.Grade(coords)
    mpk = 60.0 / args.v_pe * br.FATOR_RUA
    mpk_carro = 60.0 / args.v_carro * br.FATOR_RUA

    # triagem barata com o guloso, refino caro so nas melhores sementes
    triagem = []
    for i in range(len(pdvs)):
        tcar = H(origem, coords[i]) * mpk_carro
        if tcar >= args.minutos - args.t_visita:
            continue
        o, _ = hs.rota_gulosa(i, coords, grade, (), args.minutos - tcar,
                              args.t_visita, mpk)
        triagem.append((len(o), -tcar, i))
    triagem.sort(reverse=True)

    melhor = None
    for _, ntcar, i in triagem[:args.sementes]:
        tcar = -ntcar
        tour = resolve(i, args.minutos - tcar, coords, grade, mpk, args.t_visita)
        gasto = custo(tour, coords, mpk, args.t_visita)
        if melhor is None or (len(tour), -tcar) > (len(melhor[0]), -melhor[1]):
            melhor = (tour, tcar, gasto)
    tour, tcar, gasto = melhor

    km = sum(H(coords[tour[k]], coords[tour[k+1]]) for k in range(len(tour)-1)) \
        * br.FATOR_RUA
    p0 = pdvs[tour[0]]
    print("partida: %s" % p0["address_complete"])
    print("%d visitas | %.0f min de carro + %.0f min a pe = %.0f de %.0f"
          % (len(tour), tcar, gasto, tcar + gasto, args.minutos))
    print("caminhada: %.2f km (%.0f m por parada) | %.1f conversoes esperadas"
          % (km, km * 1000 / len(tour), len(tour) * args.conversao))

    linhas, ant, t = [], None, tcar
    for k, j in enumerate(tour, 1):
        p = pdvs[j]
        atual = coords[j]
        reta = 0.0 if ant is None else H(ant, atual)
        t += reta * mpk
        chega = t
        t += args.t_visita
        linhas.append({"parada": k, "chega_min": round(chega), "sai_min": round(t),
                       "caminhada_m": round(reta * br.FATOR_RUA * 1000),
                       "nome": p["name"], "endereco": p["address_complete"],
                       "telefone": p["nationalPhoneNumber"] or "-",
                       "setor": p["setor"], "melhor_dia": p["melhor_dia_semana"],
                       "lat": p["lat"], "lon": p["lon"],
                       "link": "https://www.google.com/maps/search/?api=1&query=%s,%s"
                               % (p["lat"], p["lon"])})
        ant = atual
    os.makedirs(args.saida, exist_ok=True)
    with open(os.path.join(args.saida, args.arquivo), "w", newline="",
              encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0].keys()))
        w.writeheader(); w.writerows(linhas)
    for l in linhas:
        print("%2d | %3d-%3d min | %4dm | %-34s | %s"
              % (l["parada"], l["chega_min"], l["sai_min"], l["caminhada_m"],
                 l["nome"][:34], l["endereco"][:44]))
    print("\ngravado em %s" % os.path.join(os.path.abspath(args.saida), args.arquivo))


if __name__ == "__main__":
    main()
