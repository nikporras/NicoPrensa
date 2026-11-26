#!/usr/bin/env python3
"""Mide al mensajero contra una edición ya publicada.

Para cada noticia de la edición dice si estaba entre lo que el mensajero
leyó esa mañana, en qué puesto de su sección quedó y con cuántos medios.
También lista las noticias con más cobertura que la edición no trae.

Uso: python scripts/evaluar.py [YYYY-MM-DD]   (sin fecha: la última edición)
     python scripts/evaluar.py edicion.json   (una edición aún sin publicar)
Solo muestra el informe; no cambia ningún archivo.
"""
import json
import math
import re
import sys
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime, time, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import candidatos as c  # noqa: E402

HORA_DE_CORTE = time(5, 45)   # UTC: hora a la que corre el mensajero cada mañana
SEGURA, DUDOSA = 0.6, 0.4     # parte del titular que debe aparecer en el texto publicado


def dominio(url):
    host = (urllib.parse.urlsplit(str(url or "")).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def corto(texto, largo):
    texto = " ".join(str(texto or "").split())
    return texto if len(texto) <= largo else texto[:largo - 1] + "…"


def main():
    ediciones = sorted(p.stem for p in c.DATA.glob("*.json") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem))
    pedido = sys.argv[1].strip() if len(sys.argv) > 1 else ""
    if pedido.endswith(".json"):   # una edición que todavía no está publicada en data/
        edicion = json.loads(Path(pedido).read_text(encoding="utf-8"))
        fecha = edicion["date"]
    else:
        fecha = pedido or ediciones[-1]
        edicion = json.loads((c.DATA / f"{fecha}.json").read_text(encoding="utf-8"))
    dia = datetime.strptime(fecha, "%Y-%m-%d").date()
    corte = datetime.combine(dia, HORA_DE_CORTE, tzinfo=timezone.utc)

    # Lo mismo que habría visto el mensajero a la hora de corte de ese día.
    estados, noticias = c.recoger(corte)
    noticias = [n for n in noticias if n["fecha"] <= corte]
    _, todos = c.armar(noticias, dia, corte)

    cuenta, por_link, indice = Counter(), {}, defaultdict(set)
    for i, k in enumerate(todos):
        cuenta[k["seccion"]] += 1
        k["puesto"] = cuenta[k["seccion"]]
        k["titulos"] = [c.palabras(l["titular"]) for l in k["links"]]
        k["pal"] = set().union(*k["titulos"]) | c.palabras(k.get("resumen"))
        for l in k["links"]:
            por_link[c.url_base(l["url"])] = i
        for p in k["pal"]:
            indice[p].add(i)
    frecuencia = Counter(p for k in todos for p in k["pal"])
    total = len(todos)

    def peso(p):   # las palabras raras (nombres, cifras) pesan más
        return math.log((total + 1) / (frecuencia.get(p, 0) + 0.5))

    def buscar(texto, url=None):
        if url and c.url_base(url) in por_link:
            return "link", 1.0, por_link[c.url_base(url)]
        pal = c.palabras(texto)
        vecinos = Counter()
        for p in pal:
            for i in indice.get(p, ()):
                vecinos[i] += peso(p)
        mejor, cual = 0.0, None
        for i, _ in vecinos.most_common(40):
            for titulo in todos[i]["titulos"]:
                comunes = pal & titulo
                if len(comunes) < 2 or not titulo:
                    continue
                parte = sum(peso(p) for p in comunes) / sum(peso(p) for p in titulo)
                if parte > mejor:
                    mejor, cual = parte, i
        if mejor >= SEGURA:
            return "texto", mejor, cual
        if mejor >= DUDOSA:
            return "duda", mejor, cual
        return "no", mejor, None

    medios_leidos = {dominio(n["url"]) for n in noticias}
    usados, filas, resumen = set(), [], defaultdict(Counter)
    for sec in edicion.get("sections") or []:
        for nota in sec.get("stories") or []:
            como, parte, i = buscar(nota.get("text"), nota.get("url"))
            resumen[sec["id"]][como] += 1
            if i is not None:
                usados.add(i)
            filas.append((sec["id"], como, parte, i, nota))
    omitidas = []
    for o in edicion.get("omitidas") or []:
        como, parte, i = buscar(o.get("title"))
        if i is not None:
            usados.add(i)
        omitidas.append((como, parte, i, o))

    print("=== INFORME ===")
    fallidos = [e for e in estados if not e["ok"]]
    print(f"Edición {fecha}. Corte {corte:%Y-%m-%d %H:%M} UTC. Feeds leídos: {len(estados) - len(fallidos)}"
          f" de {len(estados)}. Titulares: {len(noticias)}. Noticias distintas: {total}."
          f" Con 2 o más medios: {sum(1 for k in todos if k['n_medios'] >= 2)}.")
    for e in fallidos:
        print(f"  FALLÓ {e['medio']} ({e['seccion']}): {e['error']}"[:150])

    print("\nLOS 6 PRIMEROS DE CADA SECCIÓN (puntaje, medios directos + otros, señal)")
    for sec in c.SECCIONES:
        for k in [x for x in todos if x["seccion"] == sec][:6]:
            senal = (k.get("senales") or [""])[0][:34]
            print(f"  {sec:8s} {k['puntaje']:5.2f} {k['n_medios']}m+{len(k.get('otros_medios') or [])} "
                  f"{senal:34s} | {corto(k['titular'], 78)}")

    print("\nNOTICIAS CON 3 O MÁS MEDIOS QUE LA EDICIÓN NO TRAE (las 20 primeras)")
    faltan = [(i, k) for i, k in enumerate(todos) if k["n_medios"] >= 3 and i not in usados]
    for i, k in faltan[:20]:
        print(f"  {k['n_medios']}m {k['seccion']:8s} #{k['puesto']:<3d} | {corto(k['titular'], 100)}")
    print(f"  (en total {len(faltan)})")

    print("\nNOTICIAS PUBLICADAS (cómo | sección publicada | sección, puesto y medios en el mensajero)")
    for sec, como, parte, i, nota in filas:
        if i is None:
            dom = dominio(nota.get("url"))
            donde = "medio leído" if dom in medios_leidos else "medio fuera de los feeds"
            print(f"[NO   ] {sec:8s} | {dom} ({donde}) | {corto(nota.get('text'), 90)}")
        else:
            k = todos[i]
            print(f"[{como:5s}] {sec:8s} | {k['seccion']:8s} #{k['puesto']:<3d} {k['n_medios']}m {parte:.2f} | "
                  f"{corto(nota.get('text'), 60)} <= {corto(k['titular'], 60)}")
    print("\nOMITIDAS POR LA EDICIÓN")
    for como, parte, i, o in omitidas:
        if i is None:
            print(f"[NO   ] {o.get('level', ''):5s} | {corto(o.get('title'), 100)}")
        else:
            k = todos[i]
            print(f"[{como:5s}] {o.get('level', ''):5s} | {k['seccion']:8s} #{k['puesto']:<3d} {k['n_medios']}m {parte:.2f} | "
                  f"{corto(o.get('title'), 55)} <= {corto(k['titular'], 55)}")

    print("\nRESUMEN POR SECCIÓN (link + texto = encontradas)")
    suma = Counter()
    for sec, r in resumen.items():
        suma.update(r)
        print(f"  {sec:8s} publicadas {sum(r.values()):2d} | encontradas {r['link'] + r['texto']:2d}"
              f" | dudosas {r['duda']:2d} | no {r['no']:2d}")
    print(f"  TOTAL    publicadas {sum(suma.values()):2d} | encontradas {suma['link'] + suma['texto']:2d}"
          f" (por link {suma['link']}) | dudosas {suma['duda']:2d} | no {suma['no']:2d}")
    puestos = [todos[i]["puesto"] for _, como, _, i, _ in filas if como in ("link", "texto")]
    print(f"  Puesto de las encontradas: hasta 5: {sum(p <= 5 for p in puestos)}, hasta 15: {sum(p <= 15 for p in puestos)},"
          f" hasta 40: {sum(p <= 40 for p in puestos)}, más abajo: {sum(p > 40 for p in puestos)}")
    print("=== FIN ===")


if __name__ == "__main__":
    main()
