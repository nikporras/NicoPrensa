#!/usr/bin/env python3
"""Mensajero de NicoPrensa.

Lee los feeds RSS de feeds.json, descarta lo viejo y lo ya publicado,
agrupa titulares parecidos entre medios y guarda los candidatos del día
en data/candidatos/YYYY-MM-DD.json (fecha en Europe/London).

No usa IA ni claves. Única dependencia externa: feedparser.
Uso: python scripts/candidatos.py
"""
import calendar
import html
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
SALIDA = DATA / "candidatos"
FEEDS = RAIZ / "feeds.json"

VENTANA_HORAS = 48          # se descarta lo más viejo que esto
EDICIONES_A_COMPARAR = 3    # ediciones recientes contra las que se evita repetir
POR_SECCION = 15            # candidatos por sección
EN_TOP = 12                 # candidatos en el bloque "top"
TOP_MAX_POR_SECCION = 4     # para que una sola sección no llene el "top"
DIAS_A_GUARDAR = 7          # se borran candidatos más viejos que esto
ESPERA = 20                 # segundos máximos por feed
NAVEGADOR = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

# Si una noticia aparece en feeds de varias secciones, gana la más específica.
SECCIONES = ["futbol", "juegos", "cine", "tec", "colombia", "latam", "politica"]

VACIAS = set("""
a al algo ante asi aun aunque cada como con contra cual cuando de del desde donde dos el ella ellos en entre era es esa
ese eso esta estan estas este esto estos fue ha hace hacia han hasta hay hoy la las le les lo los mas me mi mientras muy
ni no nos o otra otro para pero por que quien se segun ser si sin sobre son su sus tambien tiene todo tras tu un una uno
unos y ya tres ano anos dia dias nuevo nueva nuevos nuevas dice dijo sera puede video fotos foto
ao aos as com da das do dos em essa esse isso na nas nao nem no nos os ou pela pelo por qual sao seu sua um uma apos diz
the of and to in on for with at by from as is are was be has have its it this that after over new says say will
""".split())


def sin_tildes(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def palabras(texto):
    """Palabras útiles de un texto: minúsculas, sin tildes, sin palabras vacías."""
    limpio = sin_tildes(str(texto or "").lower())
    return {p for p in re.findall(r"[a-z0-9]+", limpio) if (len(p) >= 3 or p.isdigit()) and p not in VACIAS}


def url_base(url):
    """URL sin protocolo, www, parámetros ni barra final, para comparar links."""
    p = urllib.parse.urlsplit(str(url or "").strip())
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host + p.path.rstrip("/")


def texto_plano(crudo, largo=300):
    t = re.sub(r"<[^>]+>", " ", str(crudo or ""))
    t = re.sub(r"\s+", " ", html.unescape(t)).strip()
    return t if len(t) <= largo else t[:largo].rsplit(" ", 1)[0] + "…"


def descargar(url):
    pedido = urllib.request.Request(url, headers={
        "User-Agent": NAVEGADOR,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    })
    with urllib.request.urlopen(pedido, timeout=ESPERA) as r:
        return r.read()


def leer_feed(feed, ahora):
    """Devuelve (estado, noticias) de un feed. Nunca lanza errores."""
    estado = {"medio": feed["medio"], "seccion": feed["seccion"], "url": feed["url"],
              "ok": False, "total": 0, "recientes": 0, "sin_fecha": 0, "error": None}
    noticias = []
    try:
        datos = feedparser.parse(descargar(feed["url"]))
        if not datos.entries:
            raise ValueError("el feed no trae noticias" + (f" ({datos.bozo_exception})" if datos.bozo else ""))
        limite = ahora - timedelta(hours=VENTANA_HORAS)
        for e in datos.entries:
            titular = texto_plano(e.get("title"), 400)
            link = str(e.get("link") or "").strip()
            if not titular or not link.startswith("http"):
                continue
            estado["total"] += 1
            t = e.get("published_parsed") or e.get("updated_parsed") or e.get("created_parsed")
            if not t:
                estado["sin_fecha"] += 1
                continue
            fecha = datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)
            if fecha < limite or fecha > ahora + timedelta(hours=3):
                continue
            estado["recientes"] += 1
            noticias.append({
                "titular": titular, "url": link, "fecha": fecha, "medio": feed["medio"],
                "seccion": feed["seccion"], "idioma": feed.get("idioma", "es"),
                "resumen": texto_plano(e.get("summary") or e.get("description")),
                "palabras": palabras(titular),
            })
        estado["ok"] = True
    except Exception as err:  # un feed caído no debe frenar a los demás
        estado["error"] = f"{type(err).__name__}: {err}"[:200]
    return estado, noticias


def publicado_reciente():
    """Links y textos de las últimas ediciones publicadas."""
    links, textos = set(), []
    ediciones = sorted(p for p in DATA.glob("*.json") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem))
    for ruta in ediciones[-EDICIONES_A_COMPARAR:]:
        try:
            ed = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        frases = [ed.get("title")]
        frases += [r.get("text") for r in ed.get("resumen") or []]
        frases += [o.get("title") for o in ed.get("omitidas") or []]
        for sec in ed.get("sections") or []:
            for nota in sec.get("stories") or []:
                frases.append(nota.get("text"))
                if nota.get("url"):
                    links.add(url_base(nota["url"]))
        textos += [p for p in (palabras(f) for f in frases if f) if len(p) >= 3]
    return links, textos


def ya_publicada(noticia, links, textos):
    if url_base(noticia["url"]) in links:
        return True
    pal = noticia["palabras"]
    if len(pal) < 4:
        return False
    for t in textos:
        comunes = len(pal & t)
        # Casi todo el titular está dentro de un texto ya publicado.
        if comunes >= 4 and comunes / len(pal) >= 0.7:
            return True
    return False


def parecidas(a, b):
    comunes = len(a & b)
    if comunes < 2:
        return False
    jaccard = comunes / len(a | b)
    return (comunes >= 3 and jaccard >= 0.34) or jaccard >= 0.5


def agrupar(noticias):
    """Junta titulares parecidos. Cada grupo es una noticia."""
    grupos, indice = [], defaultdict(set)   # indice: palabra -> grupos que la usan
    for n in sorted(noticias, key=lambda x: x["fecha"]):
        vecinos = Counter(g for p in n["palabras"] for g in indice[p])
        destino = None
        for g, comunes in vecinos.most_common():
            if comunes < 2:
                break
            if any(parecidas(n["palabras"], m["palabras"]) for m in grupos[g]):
                destino = g
                break
        if destino is None:
            destino = len(grupos)
            grupos.append([])
        grupos[destino].append(n)
        for p in n["palabras"]:
            indice[p].add(destino)
    return grupos


def candidato(grupo, ahora):
    grupo = sorted(grupo, key=lambda x: x["fecha"], reverse=True)
    # Un link por URL; el titular principal es el más reciente en español si hay.
    vistos, links = set(), []
    for n in grupo:
        clave = url_base(n["url"])
        if clave in vistos:
            continue
        vistos.add(clave)
        links.append({"medio": n["medio"], "titular": n["titular"], "url": n["url"],
                      "fecha": n["fecha"].isoformat(timespec="minutes"), "idioma": n["idioma"]})
    principal = next((n for n in grupo if n["idioma"] == "es"), grupo[0])
    medios = sorted({n["medio"] for n in grupo})
    votos = Counter(n["seccion"] for n in grupo)
    mejor = max(votos.values())
    seccion = next(s for s in SECCIONES if votos.get(s) == mejor)
    horas = (ahora - grupo[0]["fecha"]).total_seconds() / 3600
    extra = max(0.0, 1 - horas / VENTANA_HORAS)   # entre 0 y 1: lo reciente desempata
    return {
        "titular": principal["titular"], "seccion": seccion,
        "puntaje": round(len(medios) + extra, 2), "n_medios": len(medios), "medios": medios,
        "fecha": grupo[0]["fecha"].isoformat(timespec="minutes"),
        "resumen": principal["resumen"], "links": links,
    }


def trm_de_hoy(hoy):
    """TRM oficial vigente hoy, desde datos.gov.co. Si falla, None."""
    dia = hoy.isoformat() + "T00:00:00.000"
    consulta = urllib.parse.urlencode({
        "$where": f"vigenciadesde <= '{dia}' AND vigenciahasta >= '{dia}'",
        "$order": "vigenciadesde DESC", "$limit": 1,
    })
    try:
        filas = json.loads(descargar("https://www.datos.gov.co/resource/32sa-8pi3.json?" + consulta))
        fila = filas[0]
        return {"valor": float(fila["valor"]), "vigencia_desde": fila["vigenciadesde"][:10],
                "vigencia_hasta": fila["vigenciahasta"][:10], "fuente": "datos.gov.co"}
    except Exception as err:
        print(f"TRM no disponible: {err}", file=sys.stderr)
        return None


def borrar_viejos(hoy):
    for ruta in SALIDA.glob("*.json"):
        try:
            if (hoy - datetime.strptime(ruta.stem, "%Y-%m-%d").date()).days > DIAS_A_GUARDAR:
                ruta.unlink()
        except ValueError:
            pass


def main():
    ahora = datetime.now(timezone.utc)
    hoy = ahora.astimezone(ZoneInfo("Europe/London")).date()
    config = json.loads(FEEDS.read_text(encoding="utf-8"))
    feeds = [dict(f, seccion=sec) for sec in SECCIONES for f in config.get(sec, [])]

    with ThreadPoolExecutor(max_workers=12) as hilos:
        resultados = list(hilos.map(lambda f: leer_feed(f, ahora), feeds))
    estados = [e for e, _ in resultados]
    noticias = [n for _, lista in resultados for n in lista]

    links, textos = publicado_reciente()
    nuevas = [n for n in noticias if not ya_publicada(n, links, textos)]

    todos = sorted((candidato(g, ahora) for g in agrupar(nuevas)),
                   key=lambda c: (c["puntaje"], c["fecha"]), reverse=True)
    secciones = {s: [c for c in todos if c["seccion"] == s][:POR_SECCION] for s in SECCIONES}

    top, usados = [], Counter()
    for c in todos:
        if c["n_medios"] < 2 or usados[c["seccion"]] >= TOP_MAX_POR_SECCION:
            continue
        top.append(c)
        usados[c["seccion"]] += 1
        if len(top) == EN_TOP:
            break

    salida = {
        "fecha": hoy.isoformat(),
        "generado": ahora.isoformat(timespec="seconds"),
        "ventana_horas": VENTANA_HORAS,
        "tasas": {"trm": trm_de_hoy(hoy)},
        "resumen": {
            "feeds_leidos": sum(e["ok"] for e in estados), "feeds_fallidos": sum(not e["ok"] for e in estados),
            "titulares_recientes": len(noticias), "descartados_ya_publicados": len(noticias) - len(nuevas),
            "noticias_distintas": len(todos),
            "candidatos_por_seccion": {s: len(v) for s, v in secciones.items()},
        },
        "feeds_fallidos": [{"medio": e["medio"], "seccion": e["seccion"], "url": e["url"], "error": e["error"]}
                           for e in estados if not e["ok"]],
        "top": top,
        "secciones": secciones,
        "feeds": estados,
    }
    SALIDA.mkdir(parents=True, exist_ok=True)
    destino = SALIDA / f"{hoy.isoformat()}.json"
    destino.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    borrar_viejos(hoy)

    r = salida["resumen"]
    print(f"Guardado {destino.relative_to(RAIZ)}")
    print(f"Feeds: {r['feeds_leidos']} leídos, {r['feeds_fallidos']} fallidos. "
          f"Titulares recientes: {r['titulares_recientes']}. Ya publicados: {r['descartados_ya_publicados']}.")
    for s in SECCIONES:
        varios = sum(1 for c in secciones[s] if c["n_medios"] >= 2)
        print(f"  {s:9s} {len(secciones[s]):2d} candidatos ({varios} con 2 o más medios)")
    print(f"  top       {len(top):2d} candidatos")
    for e in estados:
        if not e["ok"]:
            print(f"  FALLÓ {e['medio']} ({e['seccion']}): {e['error']}")


if __name__ == "__main__":
    main()
