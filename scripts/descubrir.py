#!/usr/bin/env python3
"""Busca los feeds que cada sitio anuncia en su portada y en su robots.txt.

Uso: python scripts/descubrir.py https://www.ejemplo.com https://otro.com
     python scripts/descubrir.py =https://www.ejemplo.com/feed.xml   (prueba una dirección exacta)
Solo muestra lo que encuentra; no cambia ningún archivo.
"""
import re
import sys
import urllib.parse
import urllib.request

NAVEGADOR = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"


def leer(url):
    pedido = urllib.request.Request(url, headers={"User-Agent": NAVEGADOR, "Accept": "*/*"})
    with urllib.request.urlopen(pedido, timeout=20) as r:
        return r.read(600000).decode("utf-8", "replace")


def probar(url):
    try:
        cuerpo = leer(url)
        notas = len(re.findall(r"<item[\s>]|<entry[\s>]|<url>", cuerpo))
        fechas = re.findall(r"<(?:pubDate|updated|news:publication_date|lastmod)>([^<]+)<", cuerpo)
        return f"OK   {notas:4d} notas, fecha más nueva: {max(fechas) if fechas else 'sin fecha'}"
    except Exception as err:
        return f"FALLA {type(err).__name__}: {err}"[:90]


for sitio in sys.argv[1:]:
    if sitio.startswith("="):   # "=URL": probar esa dirección tal cual y mostrar una muestra
        print(f"\n=== directo {sitio[1:]}")
        try:
            cuerpo = leer(sitio[1:])
            notas = len(re.findall(r"<item[\s>]|<entry[\s>]", cuerpo))
            trozo = re.search(r"<item[\s>].*?</item>|<entry[\s>].*?</entry>", cuerpo, flags=re.S)
            print(f"  OK {len(cuerpo)} caracteres, {notas} notas")
            titulos = re.findall(r"<item[\s>].*?<title>(.*?)</title>", cuerpo, flags=re.S)
            if titulos:   # los primeros titulares, para ver de qué trata el feed
                for t in titulos[:10]:
                    print("    - " + " ".join(t.split())[:110])
            else:
                print("  MUESTRA: " + " ".join((trozo.group(0) if trozo else cuerpo).split())[:600])
        except Exception as err:
            print(f"  FALLA {type(err).__name__}: {err}"[:200])
        continue
    print(f"\n=== {sitio}")
    hallados = []
    try:
        portada = leer(sitio)
        for etiqueta in re.findall(r"<link[^>]+>", portada, flags=re.I):
            if re.search(r"application/(rss|atom)\+xml", etiqueta, flags=re.I):
                m = re.search(r'href=["\']([^"\']+)', etiqueta, flags=re.I)
                if m:
                    hallados.append(urllib.parse.urljoin(sitio, m.group(1)))
        hallados += [urllib.parse.urljoin(sitio, h) for h in
                     re.findall(r'href=["\']([^"\']*(?:rss|feed)[^"\']*)["\']', portada, flags=re.I)][:15]
    except Exception as err:
        print(f"  portada: FALLA {type(err).__name__}: {err}"[:120])
    try:
        robots = leer(urllib.parse.urljoin(sitio, "/robots.txt"))
        hallados += re.findall(r"(?im)^sitemap:\s*(\S+)", robots)
    except Exception as err:
        print(f"  robots.txt: FALLA {type(err).__name__}: {err}"[:120])
    vistos = []
    for u in hallados:
        if u not in vistos and u.startswith("http"):
            vistos.append(u)
    if not vistos:
        print("  no anuncia feeds")
    for u in vistos[:25]:
        print(f"  {probar(u)}  {u}")
