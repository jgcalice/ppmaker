#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Plano de turno: carro SO para saltar entre grandes centros, tudo a pe dentro.

Estrutura fixa (a que o usuario pediu), otimizada por dentro:
  1. mede o valor de cada centro: quantas visitas ele rende com X minutos a pe
  2. programacao dinamica sobre sequencias de centros, pagando o carro entre eles
"""
import argparse, csv, os

import build_rota as br
import hotspot as hs
import multicentro as mc
import orienteering as ori

H = br.haversine
PASSO = 5.0        # granularidade da tabela de valor, em minutos


def curva_de_valor(centro, coords, grade, mpk_pe, t_visita, teto, raio_giro):
    """Tempo acumulado ate a k-esima visita dentro do centro, andando."""
    sub = [j for j in grade.perto(coords[centro["ancora"]][0],
                                  coords[centro["ancora"]][1], raio_giro)
           if H(coords[centro["ancora"]], coords[j]) <= raio_giro]
    tour = ori.resolve(centro["ancora"], teto, coords, hs.Grade([coords[j] for j in sub])
                       if False else grade, mpk_pe, t_visita)
    tour = [j for j in tour if j in set(sub)] or [centro["ancora"]]
    acum, t = [], 0.0
    for k, j in enumerate(tour):
        if k:
            t += H(coords[tour[k-1]], coords[j]) * mpk_pe
        t += t_visita
        acum.append(t)
    return tour, acum


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
    ap.add_argument("--raio-centro", type=float, default=0.4)
    ap.add_argument("--raio-giro", type=float, default=0.9,
                    help="km, ate onde se anda a partir da ancora do centro")
    ap.add_argument("--centros", type=int, default=30)
    ap.add_argument("--max-centros", type=int, default=4)
    ap.add_argument("--saida", default="saida")
    ap.add_argument("--arquivo", default="rota_centros.csv")
    args = ap.parse_args()

    origem = tuple(float(x) for x in args.origem.split(","))
    pdvs = br.carrega_base(args.html, args.unb)
    coords = [(p["lat"], p["lon"]) for p in pdvs]
    grade = hs.Grade(coords)
    mpk_pe = 60.0 / args.v_pe * br.FATOR_RUA
    mpk_car = 60.0 / args.v_carro * br.FATOR_RUA

    centros = mc.acha_centros(coords, grade, args.raio_centro, args.centros)
    for c in centros:
        c["tour"], c["acum"] = curva_de_valor(c, coords, grade, mpk_pe,
                                              args.t_visita, args.minutos,
                                              args.raio_giro)
        c["carro_da_origem"] = H(origem, coords[c["ancora"]]) * mpk_car

    def visitas(c, t):
        return sum(1 for a in c["acum"] if a <= t + 1e-9)

    # DP: (centros ja usados, centro atual, tempo gasto) -> visitas
    passos = int(args.minutos / PASSO) + 1
    melhor = (0, None)
    def expande(seq, tempo, total):
        nonlocal melhor
        if total > melhor[0] or (total == melhor[0] and melhor[1] and
                                 len(seq) < len(melhor[1])):
            melhor = (total, list(seq))
        if len(seq) >= args.max_centros:
            return
        atual = seq[-1][0] if seq else None
        for c in centros:
            if any(s[0] is c for s in seq):
                continue
            desl = (c["carro_da_origem"] if atual is None
                    else H(coords[atual["ancora"]], coords[c["ancora"]]) * mpk_car)
            base = tempo + desl
            if base + args.t_visita > args.minutos:
                continue
            for passo in range(passos, 0, -1):
                dedic = passo * PASSO
                if base + dedic > args.minutos + 1e-9:
                    continue
                n = visitas(c, dedic)
                if n == 0:
                    continue
                if n < visitas(c, args.minutos) and passo < passos:
                    pass
                seq.append((c, dedic, desl))
                expande(seq, base + dedic, total + n)
                seq.pop()
                break_marker = None
            # tambem tentar dedicar exatamente o necessario para cada k
            for k in range(1, len(c["acum"]) + 1):
                dedic = c["acum"][k-1]
                if base + dedic > args.minutos + 1e-9:
                    break
                seq.append((c, dedic, desl))
                expande(seq, base + dedic, total + k)
                seq.pop()

    expande([], 0.0, 0)
    total, plano = melhor
    print("%d visitas | %.1f conversoes esperadas | %d centro(s), %d trecho(s) de carro"
          % (total, total * args.conversao, len(plano), len(plano)))

    linhas, t, pos = [], 0.0, origem
    for bloco, (c, dedic, desl) in enumerate(plano, 1):
        n = sum(1 for a in c["acum"] if a <= dedic + 1e-9)
        anc = coords[c["ancora"]]
        e = pdvs[c["ancora"]]["address_complete"]
        bairro = e.split(" - ")[-1] if " - " in e else pdvs[c["ancora"]]["city"]
        print("\nCENTRO %d: %s | %.0f min de carro | %d visitas em %.0f min"
              % (bloco, bairro, desl, n, dedic))
        t += desl
        anterior = None
        for k, j in enumerate(c["tour"][:n], 1):
            p = pdvs[j]
            cam = 0.0 if anterior is None else H(anterior, coords[j])
            t += cam * mpk_pe
            chega = t
            t += args.t_visita
            linhas.append({"parada": len(linhas) + 1, "centro": bloco,
                           "bairro_centro": bairro,
                           "chegada_por": "carro" if k == 1 else "a pe",
                           "desloc_m": round((H(pos, coords[j]) if k == 1 else cam)
                                             * br.FATOR_RUA * 1000),
                           "chega_min": round(chega), "sai_min": round(t),
                           "nome": p["name"], "endereco": p["address_complete"],
                           "cidade": p["city"],
                           "telefone": p["nationalPhoneNumber"] or "-",
                           "setor": p["setor"], "melhor_dia": p["melhor_dia_semana"],
                           "lat": p["lat"], "lon": p["lon"],
                           "link": "https://www.google.com/maps/search/?api=1&query=%s,%s"
                                   % (p["lat"], p["lon"])})
            print("   %s %2d | %3d-%3d min | %4dm | %-32s | %s"
                  % (">> CARRO" if k == 1 else "        ", linhas[-1]["parada"],
                     linhas[-1]["chega_min"], linhas[-1]["sai_min"],
                     linhas[-1]["desloc_m"], p["name"][:32],
                     p["address_complete"][:40]))
            anterior = coords[j]
            pos = coords[j]
    os.makedirs(args.saida, exist_ok=True)
    with open(os.path.join(args.saida, args.arquivo), "w", newline="",
              encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(linhas[0].keys()))
        w.writeheader(); w.writerows(linhas)
    km_pe = sum(l["desloc_m"] for l in linhas if l["chegada_por"] == "a pe") / 1000.0
    km_car = sum(l["desloc_m"] for l in linhas if l["chegada_por"] == "carro") / 1000.0
    print("\ntermina em %d min | %.2f km a pe | %.1f km de carro em %d trecho(s)"
          % (linhas[-1]["sai_min"], km_pe, km_car,
             sum(1 for l in linhas if l["chegada_por"] == "carro")))
    print("gravado em %s" % os.path.join(os.path.abspath(args.saida), args.arquivo))


if __name__ == "__main__":
    main()
