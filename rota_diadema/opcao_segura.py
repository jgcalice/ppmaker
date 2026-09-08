#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Variante conservadora: nenhuma perna a pe pode passar de --max-perna metros.

Pernas curtas quase nunca escondem barreira (ferrovia, marginal, rio): a poucos
metros o desvio maximo tambem e pequeno. Custa visitas, compra previsibilidade.
"""
import argparse, csv, os

import build_rota as br
import hotspot as hs

H = br.haversine


def custo(tour, coords, mpk, t_visita):
    t = t_visita * len(tour)
    for k in range(len(tour) - 1):
        t += H(coords[tour[k]], coords[tour[k+1]]) * mpk
    return t


def valido(tour, coords, limite):
    return all(H(coords[tour[k]], coords[tour[k+1]]) <= limite
               for k in range(len(tour) - 1))


def dois_opt(tour, coords, limite):
    """2-opt que so aceita trocas mantendo toda perna dentro do limite."""
    def d(a, b):
        return H(coords[a], coords[b])
    mudou = True
    while mudou:
        mudou = False
        for i in range(1, len(tour) - 1):
            for k in range(i + 1, len(tour)):
                antes = d(tour[i-1], tour[i]) + (d(tour[k], tour[k+1])
                                                 if k + 1 < len(tour) else 0.0)
                depois = d(tour[i-1], tour[k]) + (d(tour[i], tour[k+1])
                                                  if k + 1 < len(tour) else 0.0)
                if depois < antes - 1e-12:
                    cand = tour[:i] + tour[i:k+1][::-1] + tour[k+1:]
                    if valido(cand, coords, limite):
                        tour = cand
                        mudou = True
                        break
            if mudou:
                break
    return tour


def insere(tour, coords, grade, mpk, t_visita, folga, limite):
    melhor = None
    vistos = set(tour)
    alcancaveis = set()
    for j in tour:
        for c in grade.perto(coords[j][0], coords[j][1], limite):
            if c not in vistos:
                alcancaveis.add(c)
    for v in alcancaveis:
        for pos in range(1, len(tour) + 1):
            a = tour[pos-1]
            if H(coords[a], coords[v]) > limite:
                continue
            if pos == len(tour):
                extra = H(coords[a], coords[v]) * mpk + t_visita
            else:
                b = tour[pos]
                if H(coords[v], coords[b]) > limite:
                    continue
                extra = (H(coords[a], coords[v]) + H(coords[v], coords[b])
                         - H(coords[a], coords[b])) * mpk + t_visita
            if extra <= folga and (melhor is None or extra < melhor[0]):
                melhor = (extra, pos, v)
    if melhor is None:
        return None
    _, pos, v = melhor
    return tour[:pos] + [v] + tour[pos:]


def resolve(inicio, minutos, coords, grade, mpk, t_visita, limite, rodadas=80):
    tour = [inicio]
    for _ in range(rodadas):
        tour = dois_opt(tour, coords, limite)
        folga = minutos - custo(tour, coords, mpk, t_visita)
        novo = insere(tour, coords, grade, mpk, t_visita, folga, limite)
        if novo is None:
            break
        tour = novo
    return dois_opt(tour, coords, limite)


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
    ap.add_argument("--max-carro", type=float, default=20.0)
    ap.add_argument("--max-perna", type=float, default=200.0, help="metros")
    ap.add_argument("--saida", default="saida")
    ap.add_argument("--arquivo", default="opcaoC.csv")
    args = ap.parse_args()

    origem = tuple(float(x) for x in args.origem.split(","))
    pdvs = br.carrega_base(args.html, args.unb)
    coords = [(p["lat"], p["lon"]) for p in pdvs]
    grade = hs.Grade(coords)
    mpk = 60.0 / args.v_pe * br.FATOR_RUA
    mpk_car = 60.0 / args.v_carro * br.FATOR_RUA
    # o limite e dado em metros de rua; internamente comparamos linha reta
    limite = args.max_perna / 1000.0 / br.FATOR_RUA

    melhor = None
    for i in range(len(pdvs)):
        tcar = H(origem, coords[i]) * mpk_car
        if tcar > args.max_carro or tcar >= args.minutos - args.t_visita:
            continue
        tour = resolve(i, args.minutos - tcar, coords, grade, mpk,
                       args.t_visita, limite)
        if melhor is None or (len(tour), -tcar) > (len(melhor[0]), -melhor[1]):
            melhor = (tour, tcar)
    tour, tcar = melhor
    gasto = custo(tour, coords, mpk, args.t_visita)
    km = sum(H(coords[tour[k]], coords[tour[k+1]])
             for k in range(len(tour)-1)) * br.FATOR_RUA
    maior = max((H(coords[tour[k]], coords[tour[k+1]]) * br.FATOR_RUA * 1000
                 for k in range(len(tour)-1)), default=0)
    print("partida: %s" % pdvs[tour[0]]["address_complete"])
    print("%d visitas | %.0f min de carro + %.0f min a pe = %.0f de %.0f"
          % (len(tour), tcar, gasto, tcar + gasto, args.minutos))
    print("caminhada %.2f km | maior perna %.0f m (teto %.0f m) | %.1f conversoes"
          % (km, maior, args.max_perna, len(tour) * args.conversao))

    linhas, ant, t = [], None, tcar
    for k, j in enumerate(tour, 1):
        p = pdvs[j]
        reta = 0.0 if ant is None else H(ant, coords[j])
        t += reta * mpk
        chega = t
        t += args.t_visita
        linhas.append({"parada": k, "chega_min": round(chega), "sai_min": round(t),
                       "caminhada_m": round(reta * br.FATOR_RUA * 1000),
                       "nome": p["name"], "endereco": p["address_complete"],
                       "cidade": p["city"],
                       "telefone": p["nationalPhoneNumber"] or "-",
                       "setor": p["setor"], "melhor_dia": p["melhor_dia_semana"],
                       "lat": p["lat"], "lon": p["lon"],
                       "link": "https://www.google.com/maps/search/?api=1&query=%s,%s"
                               % (p["lat"], p["lon"])})
        ant = coords[j]
    os.makedirs(args.saida, exist_ok=True)
    with open(os.path.join(args.saida, args.arquivo), "w", newline="",
              encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0].keys()))
        w.writeheader(); w.writerows(linhas)
    for l in linhas:
        print("%2d | %3d-%3d min | %4dm | %-32s | %s"
              % (l["parada"], l["chega_min"], l["sai_min"], l["caminhada_m"],
                 l["nome"][:32], l["endereco"][:44]))


if __name__ == "__main__":
    main()
