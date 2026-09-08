#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Roteiro de um turno para UM dia da semana, terminando perto de um destino.

Diferencas para o solver geral:
  - so entram PDVs cujo `melhor_dia_semana` e o dia pedido
  - o trajeto de volta ate o destino e pago DENTRO do orcamento, entao a rota
    prefere terminar do lado certo da cidade
"""
import argparse, csv, os, unicodedata

import build_rota as br
import hotspot as hs

H = br.haversine


def normaliza(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def custo_a_pe(tour, coords, mpk, t_visita):
    t = t_visita * len(tour)
    for k in range(len(tour) - 1):
        t += H(coords[tour[k]], coords[tour[k+1]]) * mpk
    return t


def total(tour, coords, mpk, mpk_car, t_visita, t_ida, destino):
    """Ida de carro + campo a pe + volta de carro ate o destino."""
    return (t_ida + custo_a_pe(tour, coords, mpk, t_visita)
            + H(coords[tour[-1]], destino) * mpk_car)


def perna_maxima(tour, coords):
    return max((H(coords[tour[k]], coords[tour[k+1]])
                for k in range(len(tour) - 1)), default=0.0)


def melhora(tour, coords, raio):
    """2-opt que so aceita trocas sem criar perna acima do raio caminhavel."""
    if len(tour) < 4:
        return tour
    cand = [tour[0]] + br._dois_opt(list(tour[1:]), coords, coords[tour[0]])
    return cand if perna_maxima(cand, coords) <= raio else tour


def insere(tour, coords, grade, mpk, mpk_car, t_visita, t_ida, destino,
           minutos, raio, do_dia, peso_dia):
    """Insercao que respeita o orcamento JA CONTANDO a volta ao destino."""
    vistos = set(tour)
    cand = set()
    for j in tour:
        for c in grade.perto(coords[j][0], coords[j][1], raio):
            if c not in vistos:
                cand.add(c)
    melhor = None
    for v in cand:
        for pos in range(1, len(tour) + 1):
            a = coords[tour[pos-1]]
            if H(a, coords[v]) > raio:
                continue
            if pos < len(tour) and H(coords[v], coords[tour[pos]]) > raio:
                continue
            novo = tour[:pos] + [v] + tour[pos:]
            t = total(novo, coords, mpk, mpk_car, t_visita, t_ida, destino)
            if t > minutos:
                continue
            # PDV no dia certo entra com custo descontado, sem furar o orcamento
            peso = t / (1.0 + peso_dia) if do_dia[v] else t
            if melhor is None or peso < melhor[0]:
                melhor = (peso, novo)
    return melhor[1] if melhor else None


def resolve(inicio, coords, grade, mpk, mpk_car, t_visita, t_ida, destino,
            minutos, raio, do_dia, peso_dia, rodadas=60):
    tour = [inicio]
    if total(tour, coords, mpk, mpk_car, t_visita, t_ida, destino) > minutos:
        return []
    for _ in range(rodadas):
        tour = melhora(tour, coords, raio)
        novo = insere(tour, coords, grade, mpk, mpk_car, t_visita, t_ida,
                      destino, minutos, raio, do_dia, peso_dia)
        if novo is None:
            break
        tour = novo
    return melhora(tour, coords, raio)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True)
    ap.add_argument("--unb", default="216")
    ap.add_argument("--origem", required=True)
    ap.add_argument("--destino", required=True)
    ap.add_argument("--dia", required=True, help="ex: Terca-feira")
    ap.add_argument("--minutos", type=float, default=180.0)
    ap.add_argument("--t-visita", type=float, default=7.0)
    ap.add_argument("--conversao", type=float, default=0.10)
    ap.add_argument("--v-pe", type=float, default=4.5)
    ap.add_argument("--v-carro", type=float, default=22.0)
    ap.add_argument("--max-carro", type=float, default=20.0)
    ap.add_argument("--raio-pe", type=float, default=0.6)
    ap.add_argument("--modo", choices=("filtro", "bonus"), default="bonus",
                    help="filtro: so PDVs do dia. bonus: todos, com preferencia pelo dia")
    ap.add_argument("--excluir", default=None,
                    help="CSV(s) separados por virgula com PDVs ja visitados, a excluir")
    ap.add_argument("--peso-dia", type=float, default=0.35,
                    help="o quanto o PDV do dia vale de desconto no custo de inseri-lo")
    ap.add_argument("--saida", default="saida")
    ap.add_argument("--arquivo", default="rota_do_dia.csv")
    args = ap.parse_args()

    origem = tuple(float(x) for x in args.origem.split(","))
    destino = tuple(float(x) for x in args.destino.split(","))
    todos = br.carrega_base(args.html, args.unb)
    alvo = normaliza(args.dia)
    if args.excluir:
        feitos = set()
        for caminho in args.excluir.split(","):
            with open(caminho.strip(), encoding="utf-8-sig") as fh:
                for l in csv.DictReader(fh):
                    feitos.add((l["nome"], round(float(l["lat"]), 6)))
        antes = len(todos)
        todos = [p for p in todos
                 if (p["name"], round(p["lat"], 6)) not in feitos]
        print("excluidos %d PDVs ja visitados (%d -> %d)"
              % (antes - len(todos), antes, len(todos)))
    casa_dia = [normaliza(p["melhor_dia_semana"]) == alvo for p in todos]
    if args.modo == "filtro":
        pdvs = [p for p, c in zip(todos, casa_dia) if c]
        do_dia = [True] * len(pdvs)
    else:
        pdvs, do_dia = todos, casa_dia
    print("PDVs da UNB %s com melhor dia = %s: %d de %d (modo: %s)"
          % (args.unb, args.dia, sum(casa_dia), len(todos), args.modo))
    coords = [(p["lat"], p["lon"]) for p in pdvs]
    grade = hs.Grade(coords)
    mpk = 60.0 / args.v_pe * br.FATOR_RUA
    mpk_car = 60.0 / args.v_carro * br.FATOR_RUA

    melhor = None
    for i in range(len(pdvs)):
        t_ida = H(origem, coords[i]) * mpk_car
        if t_ida > args.max_carro:
            continue
        tour = resolve(i, coords, grade, mpk, mpk_car, args.t_visita, t_ida,
                       destino, args.minutos, args.raio_pe, do_dia, args.peso_dia)
        if not tour:
            continue
        t_volta = H(coords[tour[-1]], destino) * mpk_car
        chave = (len(tour), sum(1 for j in tour if do_dia[j]), -(t_ida + t_volta))
        if melhor is None or chave > melhor[0]:
            melhor = (chave, tour, t_ida, t_volta)
    if melhor is None:
        print("nenhuma rota cabe no orcamento")
        return
    _, tour, t_ida, t_volta = melhor
    campo = custo_a_pe(tour, coords, mpk, args.t_visita)
    km = sum(H(coords[tour[k]], coords[tour[k+1]])
             for k in range(len(tour)-1)) * br.FATOR_RUA

    print("\npartida: %s" % pdvs[tour[0]]["address_complete"])
    print("%d visitas | ida %.0f min + campo %.0f min + volta %.0f min = %.0f de %.0f"
          % (len(tour), t_ida, campo, t_volta, t_ida + campo + t_volta, args.minutos))
    n_dia = sum(1 for j in tour if do_dia[j])
    print("caminhada %.2f km (%.0f m por parada) | %.1f conversoes esperadas"
          % (km, km * 1000 / max(len(tour) - 1, 1), len(tour) * args.conversao))
    print("PDVs cujo melhor dia e hoje: %d de %d (%.0f%%)"
          % (n_dia, len(tour), 100.0 * n_dia / len(tour)))
    print("termina em: %s" % pdvs[tour[-1]]["address_complete"])

    linhas, ant, t = [], None, t_ida
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
                       "e_hoje": "SIM" if do_dia[j] else "",
                       "min_ate_o_destino": round(H(coords[j], destino) * mpk_car),
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
        print("%2d | %3d-%3d min | %4dm | %-32s | %-40s | volta %2d min"
              % (l["parada"], l["chega_min"], l["sai_min"], l["caminhada_m"],
                 l["nome"][:32], l["endereco"][:40], l["min_ate_o_destino"]))


if __name__ == "__main__":
    main()
