#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Acha a janela de N minutos que rende o maior numero de visitas a pe, varrendo
todos os PDVs como ponto de partida. Serve para escolher em qual centro urbano
gastar um turno curto.
"""
import argparse, csv, math, os
from collections import defaultdict

import build_rota as br

H = br.haversine


class Grade(object):
    """Indice espacial simples para consultas por raio."""

    def __init__(self, pontos, celula_km=0.5):
        self.celula = celula_km
        self.pontos = pontos
        self.balde = defaultdict(list)
        for i, (la, lo) in enumerate(pontos):
            self.balde[self._chave(la, lo)].append(i)

    def _chave(self, la, lo):
        return (int(la * 111.32 / self.celula), int(lo * 96.5 / self.celula))

    def perto(self, la, lo, raio_km):
        passo = int(raio_km / self.celula) + 1
        cx, cy = self._chave(la, lo)
        saida = []
        for dx in range(-passo, passo + 1):
            for dy in range(-passo, passo + 1):
                saida.extend(self.balde.get((cx + dx, cy + dy), ()))
        return saida


def rota_gulosa(inicio, coords, grade, visitados_fora, minutos, t_visita, min_por_km,
                raio_busca=0.8):
    """Vizinho mais proximo sob orcamento de tempo. Devolve (ordem, minutos gastos)."""
    if minutos < t_visita:
        return [], 0.0
    usados = set(visitados_fora)
    ordem = [inicio]
    usados.add(inicio)
    gasto = t_visita
    atual = coords[inicio]
    while True:
        melhor, melhor_custo = None, None
        for j in grade.perto(atual[0], atual[1], raio_busca):
            if j in usados:
                continue
            custo = H(atual, coords[j]) * min_por_km + t_visita
            if melhor_custo is None or custo < melhor_custo:
                melhor, melhor_custo = j, custo
        if melhor is None or gasto + melhor_custo > minutos:
            break
        gasto += melhor_custo
        ordem.append(melhor)
        usados.add(melhor)
        atual = coords[melhor]
    return ordem, gasto


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True)
    ap.add_argument("--unb", default="216")
    ap.add_argument("--origem", required=True)
    ap.add_argument("--minutos", type=float, default=120.0)
    ap.add_argument("--t-visita", type=float, default=7.0)
    ap.add_argument("--conversao", type=float, default=0.10)
    ap.add_argument("--v-pe", type=float, default=4.5, help="km/h")
    ap.add_argument("--v-carro", type=float, default=22.0, help="km/h")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--saida", default="saida")
    args = ap.parse_args()

    origem = tuple(float(x) for x in args.origem.split(","))
    pdvs = br.carrega_base(args.html, args.unb)
    coords = [(p["lat"], p["lon"]) for p in pdvs]
    grade = Grade(coords)

    min_por_km_pe = 60.0 / args.v_pe * br.FATOR_RUA
    min_por_km_carro = 60.0 / args.v_carro * br.FATOR_RUA

    # 1) varre todos os PDVs como ponto de partida de uma janela so a pe
    candidatos = []
    for i in range(len(pdvs)):
        ordem, gasto = rota_gulosa(i, coords, grade, (), args.minutos,
                                   args.t_visita, min_por_km_pe)
        candidatos.append((len(ordem), -gasto, i, ordem))
    candidatos.sort(reverse=True)

    # 2) tira sobreposicao: dois hotspots nao podem dividir PDVs
    hotspots, tomados = [], set()
    for n, _, i, ordem in candidatos:
        if len(hotspots) >= args.top:
            break
        if any(j in tomados for j in ordem):
            continue
        hotspots.append((n, i, ordem))
        tomados.update(ordem)

    print("Janela de %.0f min | %.0f min por visita | a pe a %.1f km/h (x%.2f por via)"
          % (args.minutos, args.t_visita, args.v_pe, br.FATOR_RUA))
    print("Conversao informada: %.0f%%\n" % (args.conversao * 100))
    print("%-4s %-6s %-34s %-7s %-9s %-9s %s"
          % ("#", "visitas", "onde comeca", "km a pe", "carro ida", "conv.esp", "setores"))
    linhas_rank = []
    for pos, (n, i, ordem) in enumerate(hotspots, 1):
        p = pdvs[i]
        km_pe = sum(H(coords[ordem[k]], coords[ordem[k+1]]) for k in range(len(ordem)-1))
        km_carro = H(origem, coords[i])
        bairro = p["address_complete"].split(" - ")[-1] if " - " in p["address_complete"] \
            else p["city"]
        setores = "/".join(sorted({pdvs[j]["setor"] for j in ordem}))
        print("%-4d %-6d %-34s %-7.2f %-9s %-9.1f %s"
              % (pos, n, bairro[:34], km_pe * br.FATOR_RUA,
                 "%.0f min" % (km_carro * min_por_km_carro), n * args.conversao, setores))
        linhas_rank.append({"posicao": pos, "visitas": n, "ponto_de_partida": p["name"],
                            "endereco_partida": p["address_complete"],
                            "bairro": bairro, "cidade": p["city"],
                            "km_a_pe": round(km_pe * br.FATOR_RUA, 2),
                            "min_de_carro_da_origem": round(km_carro * min_por_km_carro),
                            "conversoes_esperadas": round(n * args.conversao, 2),
                            "setores": setores,
                            "lat": p["lat"], "lon": p["lon"]})

    # 3) melhor opcao contando o deslocamento de carro dentro do orcamento
    print("\nDescontando o trajeto de carro da origem dentro dos %.0f min:" % args.minutos)
    melhor = None
    for n, i, ordem in hotspots:
        t_carro = H(origem, coords[i]) * min_por_km_carro
        sobra = args.minutos - t_carro
        o2, gasto = rota_gulosa(i, coords, grade, (), sobra, args.t_visita, min_por_km_pe)
        if melhor is None or len(o2) > len(melhor[0]):
            melhor = (o2, i, t_carro, gasto)
    o2, i, t_carro, gasto = melhor
    print("  vencedor: %s (%s)" % (pdvs[i]["name"], pdvs[i]["city"]))
    print("  %.0f min de carro + %.0f min em campo = %d visitas, %.1f conversoes esperadas"
          % (t_carro, gasto, len(o2), len(o2) * args.conversao))

    os.makedirs(args.saida, exist_ok=True)
    with open(os.path.join(args.saida, "hotspots_2h.csv"), "w", newline="",
              encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas_rank[0].keys()))
        w.writeheader(); w.writerows(linhas_rank)

    # 4) o roteiro detalhado do melhor hotspot puro (sem gastar a janela no carro)
    n, i, ordem = hotspots[0]
    detalhe, anterior, acum = [], None, 0.0
    for k, j in enumerate(ordem, 1):
        p = pdvs[j]
        atual = coords[j]
        cam = 0.0 if anterior is None else H(anterior, atual) * br.FATOR_RUA
        acum += H(anterior, atual) * min_por_km_pe + args.t_visita if anterior else args.t_visita
        detalhe.append({"parada": k, "chega_min": round(acum - args.t_visita),
                        "sai_min": round(acum), "caminhada_m": round(cam * 1000),
                        "nome": p["name"], "endereco": p["address_complete"],
                        "telefone": p["nationalPhoneNumber"], "setor": p["setor"],
                        "melhor_dia": p["melhor_dia_semana"],
                        "prob_aberto": p["open_probability_score"],
                        "lat": p["lat"], "lon": p["lon"],
                        "link": "https://www.google.com/maps/search/?api=1&query=%s,%s"
                                % (p["lat"], p["lon"])})
        anterior = atual
    with open(os.path.join(args.saida, "rota_2h_melhor_hotspot.csv"), "w", newline="",
              encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(detalhe[0].keys()))
        w.writeheader(); w.writerows(detalhe)
    print("\ngravado em %s" % os.path.abspath(args.saida))


if __name__ == "__main__":
    main()
