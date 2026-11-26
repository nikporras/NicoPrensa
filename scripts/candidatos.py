#!/usr/bin/env python3
"""Mensajero de NicoPrensa, versión 2.

Cada mañana lee los feeds de feeds.json, descarta lo viejo y lo ya publicado,
junta en un mismo grupo los titulares que hablan de la misma noticia (aunque
estén escritos distinto o en otro idioma), decide a qué sección pertenece cada
grupo y los ordena por importancia. Guarda el resultado en
data/candidatos/YYYY-MM-DD.json (fecha en Europe/London).

La importancia sale de: cuántos medios cubren la noticia, si aparece en los
titulares de Google Noticias, si es tendencia de búsqueda, si está en la
portada de un medio y qué tan reciente es.

No usa IA ni claves. Única dependencia externa: feedparser.
Uso: python scripts/candidatos.py
"""
import calendar
import html
import json
import math
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
SALIDA = DATA / "candidatos"
FEEDS = RAIZ / "feeds.json"

# ---------- Ajustes generales ----------
VENTANA_HORAS = 48          # se descarta lo más viejo que esto
EDICIONES_A_COMPARAR = 3    # ediciones recientes contra las que se evita repetir
POR_SECCION = 40            # candidatos por sección
EN_TOP = 12                 # candidatos en el bloque "top"
TOP_MAX_POR_SECCION = 4     # para que una sola sección no llene el "top"
MAX_DE_UN_MEDIO = 8         # por sección, tope de noticias que solo trae un mismo medio
MAX_LINKS = 8               # links directos que se guardan por noticia
DIAS_A_GUARDAR = 7          # se borran candidatos más viejos que esto
ESPERA = 20                 # segundos máximos por feed
PAUSA_GOOGLE = 2.5          # segundos entre pedidos a Google, que bloquea las ráfagas
DEPURAR = False             # el medidor lo enciende para ver los miembros de cada grupo
NAVEGADOR = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

# Una noticia va a una sola sección. Las temáticas ganan a las geográficas.
SECCIONES = ["futbol", "juegos", "cine", "tec", "colombia", "latam", "politica"]
TEMATICAS = ["futbol", "juegos", "cine", "tec"]
GEOGRAFICAS = ["colombia", "latam", "politica"]

# ---------- Ajustes para juntar titulares ----------
UMBRAL = 0.40               # parecido mínimo entre titulares de medios distintos
UMBRAL_MISMO_MEDIO = 0.60   # más exigente si los dos son del mismo medio
UMBRAL_ES_PT = 0.36         # español contra portugués
UMBRAL_IGUAL = 0.80         # prácticamente el mismo titular
PARTE_DEL_GRUPO = 1 / 3     # un titular entra a un grupo si se parece a un tercio de sus miembros
MUESTRA = 9                 # miembros de un grupo contra los que se compara
PESO_RESUMEN = 0.35         # cuánto pesa el resumen frente al titular
PESO_ANCLAS = 9.0           # peso mínimo de nombres propios y cifras en común para unir idiomas distintos
PESO_ANCLAS_FUSION = 8.0    # lo mismo, para unir dos grupos del mismo idioma
UMBRAL_PARIENTE = 0.25      # parecido mínimo para aceptar que dos notas que Google junta son la misma noticia
UMBRAL_FUSION = 0.33        # parecido mínimo entre dos grupos que comparten nombres propios
UMBRAL_FUSION_ALTO = 0.55   # parecido que basta por sí solo para unir dos grupos

VACIAS = set("""
a al algo ante asi aun aunque cada como con contra cual cuando de del desde donde dos el ella ellos en entre era es esa
ese eso esta estan estas este esto estos fue ha hace hacia han hasta hay hoy la las le les lo los mas me mi mientras muy
ni no nos o otra otro otros otras para pero por que quien quienes se segun ser si sin sobre son su sus tambien tiene tienen
todo toda todos todas tras tu un una uno unos unas y ya tres cuatro cinco ano anos dia dias nuevo nueva nuevos nuevas dice
dijo sera seria puede pueden video videos fotos foto resumen vivo directo ayer manana menos durante porque sido estar
habia habra hacer hizo tan tanto solo cuales aqui vez veces primer primera primero ultima ultimo ultimas ultimos
ao aos as com da das do em essa esse isso na nas nao nem os ou pela pelo qual sao seu sua um uma apos diz mais ate tem
vai foi pode novo nova seus suas isto estao pelos pelas
the of and to in on for with at by from is are was were be been has have had its it this that these those after over
new says say said will would can could into about than more what why how who whom amid but not you our out off his her
their they them may just also when while
""".split())


# ---------- Texto ----------
def sin_tildes(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


# Distintas formas de escribir lo mismo se convierten en una sola palabra.
SIGLAS = [   # con mayúsculas exactas, antes de pasar a minúsculas
    (re.compile(r"\b(?:EE\.?\s?UU\.?|EEUU|EUA|USA|U\.S\.A?\.?|US)(?![\w$])"), " eeuu "),
    (re.compile(r"\b(?:UK|U\.K\.)(?!\w)"), " xuk "),
    (re.compile(r"\b(?:UE|EU)\b"), " xue "),
    (re.compile(r"\b(?:IA|AI)\b"), " xia "),
]
NOMBRES_LARGOS = [   # ya en minúsculas y sin tildes
    (re.compile(r"\b(?:estados unidos|united states)\b"), " eeuu "),
    (re.compile(r"\b(?:reino unido|united kingdom|gran bretana)\b"), " xuk "),
    (re.compile(r"\b(?:union europea|uniao europeia|european union)\b"), " xue "),
    (re.compile(r"\b(?:inteligencia artificial|artificial intelligence)\b"), " xia "),
]
ALIAS_PROPIOS = {"eeuu", "xuk", "xue"}
ETIQUETA = re.compile(
    r"^\s*(?:v[ií]deos?|fotos?|galer[ií]a|en vivo|en directo|[úu]ltima hora|urgente|opini[óo]n|an[áa]lisis"
    r"|podcast|live|watch|exclusiv[ao]|entrevista)\s*[|:–—-]\s*", re.I)
COLA = re.compile(r"\s*[|(]\s*(?:resumen|v[ií]deos?|fotos|en vivo)\s*\)?\s*$", re.I)
PALABRA = re.compile(r"[^\W\d_]+|\d+")
CORTE_DE_FRASE = re.compile(r"[:|.?!¿¡«»\"“”‘’()\-–—]")


def normalizar(texto):
    t = str(texto or "")
    for patron, cambio in SIGLAS:
        t = patron.sub(cambio, t)
    t = sin_tildes(t.lower())
    for patron, cambio in NOMBRES_LARGOS:
        t = patron.sub(cambio, t)
    return t


def palabras(texto):
    """Palabras útiles de un texto: minúsculas, sin tildes, sin palabras vacías."""
    limpio = sin_tildes(str(texto or "").lower())
    return {p for p in re.findall(r"[a-z0-9]+", limpio) if (len(p) >= 3 or p.isdigit()) and p not in VACIAS}


def raiz(p):
    """Recorta la palabra para que 'aranceles' y 'arancel' cuenten como la misma."""
    if p.isdigit():
        return p
    if len(p) > 5:
        return p[:5]
    return p[:-1] if len(p) >= 4 and p.endswith("s") else p   # 'toys' y 'toy', 'goles' y 'gole'… cuentan igual


def raices(texto):
    """Raíces útiles de un texto, en orden. Los números de una sola cifra se ignoran."""
    salida = []
    for p in re.findall(r"[a-z0-9]+", normalizar(texto)):
        if p.isdigit():
            if len(p) >= 2:
                salida.append(p)
        elif len(p) >= 3 and p not in VACIAS:
            salida.append(raiz(p))
    return salida


def limpiar_titulo(titulo):
    return COLA.sub("", ETIQUETA.sub("", str(titulo or ""))).strip()


def formas(texto):
    """Cada palabra con dos datos: si empieza en mayúscula y si abre frase."""
    salida, abre, pos = [], True, 0
    for m in PALABRA.finditer(texto):
        if CORTE_DE_FRASE.search(texto[pos:m.start()]):
            abre = True
        w = m.group(0)
        salida.append((w, w[0].isupper(), abre))
        abre, pos = False, m.end()
    return salida


def todo_con_mayusculas(fs):
    """Titulares al estilo inglés (Casi Todo Con Mayúscula): no sirven para reconocer nombres propios."""
    largas = [f for f in fs if f[0][0].isalpha() and len(f[0]) >= 4]
    return len(largas) >= 4 and sum(1 for f in largas if f[1]) >= 0.7 * len(largas)


def raiz_de_palabra(w):
    p = sin_tildes(w.lower())
    if p.isdigit():
        return p if len(p) >= 2 else None
    if len(p) < 3 or p in VACIAS:
        return None
    return raiz(p)


def nombres_vistos(titulos):
    """Raíces que aparecen con mayúscula en mitad de un titular: nombres propios."""
    vistos = set()
    for t in titulos:
        fs = formas(t)
        if todo_con_mayusculas(fs):
            continue
        for w, mayuscula, abre in fs:
            if mayuscula and not abre and w[0].isalpha():
                r = raiz_de_palabra(w)
                if r:
                    vistos.add(r)
    return vistos


def anclas_de(texto, propias):
    """Nombres propios y cifras de un texto: lo que identifica de qué noticia se trata.
    Devuelve {raíz: número de nombre}; 'Andy Taylor' son dos raíces y un solo nombre."""
    salida, nombre, pegado = {}, 0, False
    for w, mayuscula, abre in formas(texto):
        r = raiz_de_palabra(w)
        if w.isdigit():
            pegado = False
            if r and not (len(w) == 4 and w[:2] in ("19", "20")):   # los años no distinguen noticias
                nombre += 1
                salida.setdefault(r, nombre)
        elif r and mayuscula and r in propias:
            if abre or not pegado:
                nombre += 1
            salida.setdefault(r, nombre)
            pegado = True
        else:
            pegado = False
    for r in sorted(ALIAS_PROPIOS & set(raices(texto))):
        nombre += 1
        salida.setdefault(r, nombre)
    return salida


def cuantos_nombres(comunes, a, b):
    """Cuántos nombres o cifras distintos hay en común (no cuántas palabras)."""
    return min(len({a[r] for r in comunes}), len({b[r] for r in comunes}))


def url_base(url):
    """URL sin protocolo, www, parámetros ni barra final, para comparar links."""
    p = urllib.parse.urlsplit(str(url or "").strip())
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host + p.path.rstrip("/")


def clave_de_medio(nombre):
    """'EL TIEMPO', 'El Tiempo' y 'eltiempo.com' son el mismo medio."""
    n = sin_tildes(str(nombre or "").lower())
    n = re.sub(r"\.(?:com|co|es|net|org|br|uk|ar|mx)\b.*$", "", n)
    return re.sub(r"[^a-z0-9]", "", n.replace("revista ", ""))


def texto_plano(crudo, largo=300):
    t = re.sub(r"<[^>]+>", " ", str(crudo or ""))
    t = re.sub(r"\s+", " ", html.unescape(t)).strip()
    return t if len(t) <= largo else t[:largo].rsplit(" ", 1)[0] + "…"


# ---------- Configuración ----------
def _patron(terminos):
    limpios = sorted({re.escape(sin_tildes(t.lower())) for t in terminos if t and not t.startswith("=")},
                     key=len, reverse=True)
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(limpios) + r")(?![a-z0-9])") if limpios else None


def configuracion():
    """Lee feeds.json y prepara las listas de palabras de cada sección."""
    config = json.loads(FEEDS.read_text(encoding="utf-8"))
    temas = {}
    for sec in SECCIONES:
        t = (config.get("_temas") or {}).get(sec) or {}
        todos = (t.get("fuertes") or []) + (t.get("palabras") or [])
        temas[sec] = {
            "rutas": [r.lower() for r in t.get("rutas") or []],
            "fuertes": _patron(t.get("fuertes") or []),
            "palabras": _patron(t.get("palabras") or []),
            # Los términos que empiezan por "=" se buscan con mayúsculas exactas (por ejemplo "=IA").
            "exactos": [re.compile(r"(?<!\w)" + re.escape(x[1:]) + r"(?!\w)") for x in todos if x.startswith("=")],
        }
    return {
        "feeds": [dict(f, seccion=sec) for sec in SECCIONES for f in config.get(sec, [])],
        "ruido": [sin_tildes(str(d).lower()) for d in config.get("_descartar", [])],
        "degradar": [sin_tildes(str(d).lower()) for d in config.get("_degradar", [])],
        # Frases que comparten muchas noticias distintas ("Black Friday"): no sirven para juntarlas.
        "comodines": re.compile("|".join(sorted((re.escape(str(x)) for x in config.get("_no_identifican", [])),
                                               key=len, reverse=True)) or r"(?!x)x", re.I),
        "temas": temas,
    }


# ---------- Lectura de feeds ----------
def descargar(url, intentos=1):
    pedido = urllib.request.Request(url, headers={
        "User-Agent": NAVEGADOR,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    })
    for intento in range(intentos):
        try:
            with urllib.request.urlopen(pedido, timeout=ESPERA) as r:
                return r.read()
        except Exception:
            if intento == intentos - 1:
                raise
            time.sleep(4 * (intento + 1))   # espera un poco más cada vez


def reciente(fecha, ahora):
    return ahora - timedelta(hours=VENTANA_HORAS) <= fecha <= ahora + timedelta(hours=3)


def nueva_noticia(feed, titular, url, fecha, resumen="", medio=None, **extra):
    n = {
        "titular": titular, "url": url, "fecha": fecha, "medio": medio or feed["medio"],
        "seccion": feed["seccion"], "idioma": feed.get("idioma", "es"), "resumen": resumen,
        "portada": bool(feed.get("portada")), "general": bool(feed.get("general")),
        "exige": bool(feed.get("exige")), "edicion": feed.get("edicion", ""),
        "pista": False,      # True: el link pasa por Google y no es el link directo del medio
        "senal": None,       # "google-top", "google-tema" o "tendencia"
        "rango": None, "grupo": None, "trafico": 0,
        "palabras": palabras(titular),
    }
    n.update(extra)
    return n


def es_ruido(titular, ruido):
    t = sin_tildes(titular.lower())
    return any(d in t for d in ruido)


def leer_rss(feed, ahora, estado, ruido):
    noticias = []
    datos = feedparser.parse(descargar(feed["url"]))
    if not datos.entries:
        raise ValueError("el feed no trae noticias" + (f" ({datos.bozo_exception})" if datos.bozo else ""))
    for e in datos.entries:
        titular = texto_plano(e.get("title"), 400)
        link = str(e.get("link") or "").strip()
        if not titular or not link.startswith("http"):
            continue
        if es_ruido(titular, ruido):
            estado["ruido"] += 1
            continue
        estado["total"] += 1
        t = e.get("published_parsed") or e.get("updated_parsed") or e.get("created_parsed")
        if not t:
            estado["sin_fecha"] += 1
            continue
        fecha = datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)
        if not reciente(fecha, ahora):
            continue
        estado["recientes"] += 1
        noticias.append(nueva_noticia(feed, titular, link, fecha,
                                      texto_plano(e.get("summary") or e.get("description"))))
    return noticias


ENLACE_GOOGLE = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>(?:\s|&nbsp;)*<font[^>]*>(.*?)</font>', re.S)


def leer_google(feed, ahora, estado, ruido):
    """Google Noticias. Con "senal" (top o tema) cada entrada trae varios medios que cubren
    la misma noticia y su puesto en la lista. Sin "senal" es una búsqueda site:medio, que
    sirve para leer un medio que bloquea a GitHub. Los links pasan por Google ("pista")."""
    noticias = []
    arbol = ET.fromstring(descargar(feed["url"], intentos=3))
    for puesto, item in enumerate(arbol.iter("item"), 1):
        titulo = texto_plano(item.findtext("title"), 400)
        fuente = texto_plano(item.findtext("source"), 80)
        enlace = (item.findtext("link") or "").strip()
        estado["total"] += 1
        try:
            fecha = parsedate_to_datetime(item.findtext("pubDate")).astimezone(timezone.utc)
        except (TypeError, ValueError):
            estado["sin_fecha"] += 1
            continue
        if not reciente(fecha, ahora):
            continue
        partes = [(html.unescape(h), texto_plano(t, 400), texto_plano(f, 80))
                  for h, t, f in ENLACE_GOOGLE.findall(item.findtext("description") or "")]
        if not partes or not feed.get("senal"):
            if fuente and titulo.endswith(" - " + fuente):
                titulo = titulo[:-len(fuente) - 3]
            partes = [(enlace, titulo, fuente or feed["medio"])]
        estado["recientes"] += 1
        for h, t, f in partes:
            if not t or not h.startswith("http"):
                continue
            if es_ruido(t, ruido):
                estado["ruido"] += 1
                continue
            if feed.get("senal"):
                noticias.append(nueva_noticia(feed, t, h, fecha, medio=f or "Google Noticias", pista=True,
                                              senal="google-" + feed["senal"], rango=puesto,
                                              grupo=f"{feed['url']}#{puesto}"))
            else:
                noticias.append(nueva_noticia(feed, t, h, fecha, pista=True))
    return noticias


def leer_tendencias(feed, ahora, estado, ruido):
    """Google Trends: lo más buscado en un país, con las noticias que lo explican (links directos)."""
    noticias = []
    arbol = ET.fromstring(descargar(feed["url"], intentos=3))

    def campo(nodo, nombre):
        for h in nodo:
            if h.tag.rsplit("}", 1)[-1] == nombre:
                return (h.text or "").strip()
        return ""

    for puesto, item in enumerate(arbol.iter("item"), 1):
        estado["total"] += 1
        try:
            fecha = parsedate_to_datetime(campo(item, "pubDate")).astimezone(timezone.utc)
        except (TypeError, ValueError):
            estado["sin_fecha"] += 1
            continue
        if not reciente(fecha, ahora):
            continue
        trafico = int(re.sub(r"\D", "", campo(item, "approx_traffic")) or 0)
        notas = [h for h in item if h.tag.rsplit("}", 1)[-1] == "news_item"]
        if notas:
            estado["recientes"] += 1
        for nota in notas:
            titulo = texto_plano(campo(nota, "news_item_title"), 400)
            url = campo(nota, "news_item_url")
            if not titulo or not url.startswith("http") or es_ruido(titulo, ruido):
                continue
            noticias.append(nueva_noticia(feed, titulo, url, fecha,
                                          medio=campo(nota, "news_item_source") or feed["medio"],
                                          senal="tendencia", rango=puesto, trafico=trafico,
                                          grupo=f"{feed['url']}#{puesto}"))
    return noticias


LECTORES = {"rss": leer_rss, "google": leer_google, "tendencias": leer_tendencias}


def leer_feed(feed, ahora, ruido):
    """Devuelve (estado, noticias) de un feed. Nunca lanza errores."""
    estado = {"medio": feed["medio"], "seccion": feed["seccion"], "tipo": feed.get("tipo", "rss"),
              "url": feed["url"], "ok": False, "total": 0, "recientes": 0, "sin_fecha": 0, "ruido": 0, "error": None}
    noticias = []
    try:
        noticias = LECTORES[estado["tipo"]](feed, ahora, estado, ruido)
        estado["ok"] = True
    except Exception as err:  # un feed caído no debe frenar a los demás
        estado["error"] = f"{type(err).__name__}: {err}"[:200]
    return estado, noticias


def recoger(ahora):
    """Lee todos los feeds. Devuelve (estado de cada feed, titulares recientes)."""
    config = configuracion()
    normales = [f for f in config["feeds"] if f.get("tipo", "rss") == "rss"]
    de_google = [f for f in config["feeds"] if f.get("tipo", "rss") != "rss"]
    with ThreadPoolExecutor(max_workers=12) as hilos:
        resultados = list(hilos.map(lambda f: leer_feed(f, ahora, config["ruido"]), normales))
    for f in de_google:   # uno por uno y con pausa: Google rechaza las ráfagas (error 429)
        resultados.append(leer_feed(f, ahora, config["ruido"]))
        time.sleep(PAUSA_GOOGLE)
    estados = [e for e, _ in resultados]
    noticias = [n for _, lista in resultados for n in lista]
    return estados, noticias


# ---------- Lo ya publicado ----------
def publicado_reciente(antes_de=None):
    """Links y textos de las últimas ediciones publicadas antes de la fecha dada."""
    links, textos = set(), []
    ediciones = sorted(p for p in DATA.glob("*.json") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem))
    if antes_de:
        ediciones = [p for p in ediciones if p.stem < antes_de]
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


# ---------- Sección de cada titular ----------
def puntos_de_seccion(n, temas):
    """Cuánta evidencia hay de que un titular pertenece a cada sección."""
    puntos = Counter()
    puntos[n["seccion"]] += 0.7 if n["general"] else 2.0   # la sección del feed del que salió
    ruta = "" if n["pista"] else urllib.parse.urlsplit(n["url"]).path.lower()
    texto = sin_tildes(n["titular"].lower())
    for sec, t in temas.items():
        if ruta and any(r in ruta for r in t["rutas"]):    # el link dice /futbol/, /tecnologia/...
            puntos[sec] += 2.5
        fuertes = len(set(t["fuertes"].findall(texto))) if t["fuertes"] else 0
        fuertes += sum(1 for p in t["exactos"] if p.search(n["titular"]))
        if fuertes:                                        # palabras inconfundibles de la sección
            puntos[sec] += 3.0 + 0.5 * min(2, fuertes - 1)
        if t["palabras"]:                                  # palabras que solo dan una pista
            puntos[sec] += 1.2 * min(2, len(set(t["palabras"].findall(texto))))
    return puntos


def seccion_de_noticia(n, temas):
    """Devuelve (sección, peso, evidencia propia de la sección del feed)."""
    puntos = puntos_de_seccion(n, temas)
    base = 0.7 if n["general"] else 2.0
    propia = puntos[n["seccion"]] - base
    tema = max(TEMATICAS, key=lambda s: (puntos[s], -TEMATICAS.index(s)))
    lugar = max(GEOGRAFICAS, key=lambda s: (puntos[s], -GEOGRAFICAS.index(s)))
    evidencia = puntos[tema] - (base if tema == n["seccion"] else 0)
    # La sección temática gana si hay evidencia en el titular o el link, o si el feed es
    # de ese tema y nada fuerte apunta a un país.
    if evidencia >= 2.0 or (puntos[tema] >= 2.0 and puntos[lugar] < 3.0):
        return tema, puntos[tema], propia
    if puntos[lugar] <= 0:   # nada apunta a un país: se queda en la sección de su feed
        return n["seccion"], max(puntos[n["seccion"]], 0.5), propia
    return lugar, max(puntos[lugar], 0.5), propia


# ---------- Preparar los titulares ----------
def preparar(noticias, config):
    """Calcula raíces, pesos, nombres propios y sección de cada titular."""
    utiles = []
    for n in noticias:
        n["sec"], n["sec_peso"], propia = seccion_de_noticia(n, config["temas"])
        # Feeds que mezclan temas (por ejemplo la portada de un diario deportivo):
        # solo se queda lo que de verdad es de la sección.
        if n["exige"] and (n["sec"] != n["seccion"] or propia < 1.2):
            continue
        n["limpio"] = config["comodines"].sub(" ", limpiar_titulo(n["titular"]))
        n["_t"] = set(raices(n["limpio"]))
        n["_r"] = set(raices(config["comodines"].sub(" ", n["resumen"]))[:60]) - n["_t"] if n["resumen"] else set()
        n["clave_medio"] = clave_de_medio(n["medio"])
        utiles.append(n)

    propias = nombres_vistos(n["limpio"] for n in utiles)
    frecuencia = Counter()
    for n in utiles:
        frecuencia.update(n["_t"] | n["_r"])
    total = len(utiles)
    idf = {r: math.log(1 + total / c) for r, c in frecuencia.items()}

    for n in utiles:
        n["nombres"] = anclas_de(n["limpio"], propias)
        n["anclas"] = set(n["nombres"])
        n["anclas_todas"] = n["anclas"] | (set(anclas_de(n["resumen"], propias)) if n["resumen"] else set())
        n["todas"] = n["_t"] | n["_r"]
        vt = {r: (1.3 if r in n["anclas"] else 1.0) * math.sqrt(idf[r]) for r in n["_t"]}
        n["vt"], n["nt"] = vt, math.sqrt(sum(v * v for v in vt.values())) or 1.0
        if n["_r"]:
            vf = dict(vt)
            vf.update({r: PESO_RESUMEN * math.sqrt(idf[r]) for r in n["_r"]})
            n["vf"], n["nf"] = vf, math.sqrt(sum(v * v for v in vf.values())) or 1.0
        else:
            n["vf"], n["nf"] = None, 1.0
    return utiles, idf


# ---------- Juntar titulares de la misma noticia ----------
def coseno(va, na, vb, nb):
    if len(va) > len(vb):
        va, vb = vb, va
    return sum(v * vb[r] for r, v in va.items() if r in vb) / (na * nb)


def parecido(a, b):
    """De 0 a 1: se parecen por el titular, o por titular más resumen."""
    s = coseno(a["vt"], a["nt"], b["vt"], b["nt"])
    if a["vf"] and b["vf"]:
        s = max(s, coseno(a["vf"], a["nf"], b["vf"], b["nf"]))
    return s


def peso_de(anclas, idf):
    return sum(idf.get(r, 0.0) for r in anclas)


def misma_noticia(a, b, idf):
    """¿Dos titulares hablan de la misma noticia? Devuelve el parecido, o 0 si no."""
    s = parecido(a, b)
    if s >= UMBRAL_IGUAL:
        return s
    comunes = a["anclas"] & b["anclas"]
    if a["idioma"] != b["idioma"] and "en" in (a["idioma"], b["idioma"]):
        # Inglés contra español o portugués: solo cuentan nombres propios y cifras en común.
        peso = peso_de(comunes, idf)
        menor = min(peso_de(a["anclas"], idf), peso_de(b["anclas"], idf))
        varios = len(comunes) >= 2 and cuantos_nombres(comunes, a["nombres"], b["nombres"]) >= 2
        return 0.5 if varios and peso >= PESO_ANCLAS and peso >= 0.5 * menor else 0.0
    if a["clave_medio"] == b["clave_medio"]:
        # Mismo medio: suelen ser notas distintas con la misma plantilla ("X 3-1 Y | Resumen").
        if a["anclas"] and b["anclas"] and not comunes:
            return 0.0
        return s if s >= UMBRAL_MISMO_MEDIO else 0.0
    if (a["anclas_todas"] and b["anclas_todas"]
            and not (a["anclas_todas"] & b["todas"]) and not (b["anclas_todas"] & a["todas"])):
        return 0.0   # ningún nombre propio ni cifra de uno aparece en el otro
    if a["idioma"] != b["idioma"]:
        return s if s >= UMBRAL_ES_PT and comunes else 0.0
    return s if s >= UMBRAL else 0.0


def pariente(a, b):
    """Para notas que Google presenta juntas: basta un parecido moderado y un nombre o cifra en común."""
    if a["idioma"] != b["idioma"]:
        return bool(a["anclas"] & b["anclas"])
    return parecido(a, b) >= UMBRAL_PARIENTE and bool((a["anclas"] & b["todas"]) or (b["anclas"] & a["todas"]))


def agrupar(noticias, idf):
    """Junta titulares de la misma noticia. Cada grupo es una noticia."""
    grupos, indice, de_google = [], defaultdict(set), {}
    # Primero las entradas de Google y las tendencias, que ya vienen juntas por noticia.
    orden = sorted(noticias, key=lambda n: (n["grupo"] is None, n["fecha"], n["url"]))
    for n in orden:
        destino = de_google.get(n["grupo"]) if n["grupo"] else None
        if destino is not None and not any(pariente(n, m) for m in grupos[destino][:MUESTRA]):
            destino = None   # Google a veces junta notas distintas bajo un mismo tema: no se le cree a ciegas
        if destino is None:
            vecinos = Counter()
            for r in sorted(n["_t"]):
                if len(indice[r]) <= 200:          # las palabras demasiado comunes no orientan
                    for g in indice[r]:
                        vecinos[g] += idf[r]
            mejor = (0.0, 0.0, None)
            for g, _ in sorted(vecinos.items(), key=lambda x: (-x[1], x[0]))[:8]:
                miembros = grupos[g][:MUESTRA]
                notas = [x for x in (misma_noticia(n, m, idf) for m in miembros) if x > 0]
                if not notas:
                    continue
                # Entra si es casi igual a un miembro, o si se parece a una parte del grupo:
                # así un titular suelto no encadena noticias distintas.
                if max(notas) >= UMBRAL_IGUAL or len(notas) >= math.ceil(len(miembros) * PARTE_DEL_GRUPO):
                    clave = (len(notas) / len(miembros), sum(notas) / len(notas))
                    if clave > mejor[:2]:
                        mejor = (clave[0], clave[1], g)
            destino = mejor[2]
        if destino is None:
            destino = len(grupos)
            grupos.append([])
        if n["grupo"]:
            de_google.setdefault(n["grupo"], destino)
        grupos[destino].append(n)
        for r in n["_t"]:
            indice[r].add(destino)
    return grupos


def fusionar(grupos, idf):
    """Une grupos que quedaron separados pero comparten nombres propios y tema."""
    fichas = []
    for g in grupos:
        centro, cuenta, nombres = Counter(), Counter(), {}
        for k, n in enumerate(g):
            for r, v in n["vt"].items():
                centro[r] += v
            cuenta.update(n["anclas"])
            for r, numero in n["nombres"].items():
                nombres.setdefault(r, (k, numero))
        top = dict(sorted(centro.items(), key=lambda x: (-x[1], x[0]))[:12])
        fuertes = {r for r, c in cuenta.items() if c >= max(1, math.ceil(len(g) * 0.3))}
        fichas.append((top, math.sqrt(sum(v * v for v in top.values())) or 1.0, fuertes,
                       {n["idioma"] for n in g}, nombres))

    por_ancla = defaultdict(list)
    for i, ficha in enumerate(fichas):
        for r in ficha[2]:
            por_ancla[r].append(i)
    pares = Counter()
    for r in sorted(por_ancla):
        lista = por_ancla[r]
        if len(lista) > 40:    # un nombre que sale en demasiadas noticias no las identifica
            continue
        for x in range(len(lista)):
            for y in range(x + 1, len(lista)):
                pares[(lista[x], lista[y])] += 1

    padre = list(range(len(grupos)))

    def jefe(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    for (i, j), _ in sorted(pares.items()):
        a, b = fichas[i], fichas[j]
        comunes = a[2] & b[2]
        peso = peso_de(comunes, idf)
        n_comunes = cuantos_nombres(comunes, a[4], b[4])
        if a[3] & b[3]:   # comparten idioma
            s = coseno(a[0], a[1], b[0], b[1])
            unir = s >= UMBRAL_FUSION_ALTO or (n_comunes >= 2 and peso >= PESO_ANCLAS_FUSION and s >= UMBRAL_FUSION)
        else:             # idiomas distintos: solo nombres propios y cifras
            menor = min(peso_de(a[2], idf), peso_de(b[2], idf))
            unir = n_comunes >= 2 and peso >= PESO_ANCLAS and peso >= 0.5 * menor
        if unir:
            padre[jefe(j)] = jefe(i)

    unidos = defaultdict(list)
    for i, g in enumerate(grupos):
        unidos[jefe(i)].extend(g)
    return [unidos[i] for i in sorted(unidos)]


# ---------- De grupo a candidato ----------
def candidato(grupo, ahora, config):
    grupo = sorted(grupo, key=lambda n: (n["fecha"], n["url"]), reverse=True)
    directos = [n for n in grupo if not n["pista"]]
    pistas = [n for n in grupo if n["pista"]]

    medios, claves = [], set()
    for n in directos:
        if n["clave_medio"] not in claves:
            claves.add(n["clave_medio"])
            medios.append(n["medio"])
    otros, claves_otros = [], set()
    for n in pistas:   # medios que Google dice que la cubren, aunque no estén en los feeds
        if n["clave_medio"] not in claves and n["clave_medio"] not in claves_otros:
            claves_otros.add(n["clave_medio"])
            otros.append(n["medio"])

    votos = Counter()
    for n in grupo:
        votos[n["sec"]] += n["sec_peso"]
    seccion = max(SECCIONES, key=lambda s: (votos[s], -SECCIONES.index(s)))

    # Señales de importancia de fuera de los feeds.
    senales, extra_google, ediciones, extra_tendencia = [], 0.0, set(), 0.0
    for n in grupo:
        if n["senal"] == "google-top":
            # Los 10 primeros son la portada de Google; del 11 en adelante son muestras de cada sección.
            extra_google = max(extra_google, 3.0 - 0.1 * (n["rango"] - 1) if n["rango"] <= 10 else 1.2)
            ediciones.add(n["edicion"])
            senales.append((n["rango"], f"Google Noticias {n['edicion']}: puesto {n['rango']}"))
        elif n["senal"] == "google-tema":
            extra_google = max(extra_google, 1.5 * max(0.0, 1 - (n["rango"] - 1) / 60))
            senales.append((100 + n["rango"], f"Google Noticias {n['edicion']}, por tema: puesto {n['rango']}"))
        elif n["senal"] == "tendencia":
            extra_tendencia = max(extra_tendencia, min(2.0, 0.5 * math.log10(max(10, n["trafico"]))))
            senales.append((200 + n["rango"], f"Tendencia de búsqueda en {n['edicion']} ({n['trafico']}+)"))
    extra_google += 0.5 * max(0, len(ediciones) - 1)

    # El titular que mejor representa al grupo, en español y con link directo si se puede.
    centro = Counter()
    for n in grupo:
        for r, v in n["vt"].items():
            centro[r] += v
    norma = math.sqrt(sum(v * v for v in centro.values())) or 1.0
    opciones = ([n for n in directos if n["idioma"] == "es"] or [n for n in pistas if n["idioma"] == "es"]
                or directos or grupo)
    principal = max(opciones, key=lambda n: (round(coseno(n["vt"], n["nt"], centro, norma), 4), n["fecha"], n["url"]))
    horas = (ahora - grupo[0]["fecha"]).total_seconds() / 3600
    idiomas = sorted({n["idioma"] for n in grupo})
    urls_directas = {url_base(n["url"]) for n in directos}
    titulo = sin_tildes(principal["titular"].lower())
    degradada = any(d in titulo for d in config["degradar"])

    cobertura = len(claves) + 0.5 * min(6, len(otros))
    puntaje = (cobertura + extra_google + extra_tendencia
               + (0.5 if any(n["portada"] for n in directos) else 0.0)
               + 0.5 * max(0.0, 1 - horas / VENTANA_HORAS)
               + min(0.5, 0.1 * max(0, len(urls_directas) - len(claves)))
               + 0.4 * min(2, len(idiomas) - 1)
               - (2.5 if degradada else 0.0)
               # Sin link directo y sin versión en español, en una sección temática sirve poco.
               - (2.0 if not directos and "es" not in idiomas and seccion in TEMATICAS else 0.0))

    # Links: primero uno por medio, luego el resto; al final algunos que pasan por Google.
    links, vistos, ya = [], set(), set()
    # Primero los links cuyo titular más se parece al del grupo.
    mejores = sorted(directos, key=lambda n: (-round(coseno(n["vt"], n["nt"], centro, norma), 4), n["url"]))
    for ronda in (1, 2):
        for n in mejores:
            clave = url_base(n["url"])
            if clave in vistos or (ronda == 1 and n["clave_medio"] in ya) or len(links) >= MAX_LINKS:
                continue
            vistos.add(clave)
            ya.add(n["clave_medio"])
            links.append({"medio": n["medio"], "titular": n["titular"], "url": n["url"],
                          "fecha": n["fecha"].isoformat(timespec="minutes"), "idioma": n["idioma"]})
    for n in pistas:   # links que pasan por Google: solo si ningún feed trae la noticia
        if directos or n["clave_medio"] in ya or len(links) >= 2:
            continue
        ya.add(n["clave_medio"])
        links.append({"medio": n["medio"], "titular": n["titular"], "url": n["url"],
                      "fecha": n["fecha"].isoformat(timespec="minutes"), "idioma": n["idioma"], "pista": True})

    extra = {}
    if DEPURAR:   # solo para el medidor: quién quedó en el grupo
        extra["miembros"] = [f"{n['medio']} [{n['idioma']}{' G' if n['grupo'] else ''}] {n['titular'][:75]}" for n in grupo]
    return {
        **extra,
        "titular": principal["titular"], "seccion": seccion, "puntaje": round(puntaje, 2),
        "n_medios": len(claves), "medios": medios, "otros_medios": otros, "idiomas": idiomas,
        "senales": [texto for _, texto in sorted(set(senales))][:4],
        "pista": not directos,   # True: ningún feed la trae; hay que buscar el link directo
        "fecha": grupo[0]["fecha"].isoformat(timespec="minutes"),
        "resumen": principal["resumen"], "links": links,
    }


def armar(noticias, hoy, ahora):
    """Quita lo ya publicado antes de hoy, agrupa y ordena. Devuelve (nuevas, candidatos)."""
    config = configuracion()
    links, textos = publicado_reciente(hoy.isoformat())
    nuevas = [n for n in noticias if not ya_publicada(n, links, textos)]
    utiles, idf = preparar(nuevas, config)
    grupos = fusionar(agrupar(utiles, idf), idf)
    todos = sorted((candidato(g, ahora, config) for g in grupos),
                   key=lambda c: (c["puntaje"], c["fecha"], c["titular"]), reverse=True)
    return nuevas, todos


def elegir(todos, seccion):
    """Los mejores de una sección, sin dejar que un solo medio la llene."""
    lista, de_un_medio = [], Counter()
    for c in todos:
        if c["seccion"] != seccion:
            continue
        if c["n_medios"] + len(c["otros_medios"]) <= 1 and not c["senales"]:
            medio = (c["medios"] or c["otros_medios"] or [""])[0]
            if de_un_medio[medio] >= MAX_DE_UN_MEDIO:
                continue
            de_un_medio[medio] += 1
        lista.append(c)
        if len(lista) == POR_SECCION:
            break
    return lista


# ---------- Tasas y limpieza ----------
def trm_de_hoy(hoy):
    """TRM oficial vigente hoy, desde datos.gov.co. Si falla, None."""
    dia = hoy.isoformat() + "T00:00:00.000"
    consulta = urllib.parse.urlencode({
        "$where": f"vigenciadesde <= '{dia}' AND vigenciahasta >= '{dia}'",
        "$order": "vigenciadesde DESC", "$limit": 1,
    })
    try:
        filas = json.loads(descargar("https://www.datos.gov.co/resource/32sa-8pi3.json?" + consulta, intentos=2))
        fila = filas[0]
        return {"valor": float(fila["valor"]), "vigencia_desde": fila["vigenciadesde"][:10],
                "vigencia_hasta": fila["vigenciahasta"][:10], "fuente": "datos.gov.co"}
    except Exception as err:
        print(f"TRM no disponible: {err}", file=sys.stderr)
        return None


def borrar_viejos(hoy):
    for ruta in list(SALIDA.glob("*.json")) + list(SALIDA.glob("resumen-*.md")):
        try:
            if (hoy - datetime.strptime(ruta.stem[-10:], "%Y-%m-%d").date()).days > DIAS_A_GUARDAR:
                ruta.unlink()
        except ValueError:
            pass


def liviano(c):
    """El candidato tal como se guarda: los links solo llevan titular cuando pasan por Google."""
    d = dict(c)
    d["links"] = [{k: v for k, v in x.items() if k != "fecha" and (k != "titular" or x.get("pista"))}
                  for x in c["links"]]
    return d


def guardar(salida, destino):
    """Escribe el archivo con una noticia por línea, para que pese poco y se pueda leer por partes."""
    def compacto(x):
        return json.dumps(x, ensure_ascii=False, separators=(",", ":"))

    def lista(elementos, sangria):
        if not elementos:
            return "[]"
        return "[\n" + ",\n".join(sangria + " " + compacto(x) for x in elementos) + "\n" + sangria + "]"

    partes = []
    for clave, valor in salida.items():
        if clave == "secciones":
            dentro = ",\n".join(f'  {compacto(s)}: {lista([liviano(c) for c in v], "  ")}' for s, v in valor.items())
            partes.append(f' "secciones": {{\n{dentro}\n }}')
        elif clave == "top":
            partes.append(f' "top": {lista([liviano(c) for c in valor], " ")}')
        elif clave in ("feeds", "feeds_fallidos"):
            partes.append(f' {compacto(clave)}: {lista(valor, " ")}')
        else:
            partes.append(f' {compacto(clave)}: {compacto(valor)}')
    texto = "{\n" + ",\n".join(partes) + "\n}\n"
    json.loads(texto)   # si esto falla, mejor no escribir nada
    destino.write_text(texto, encoding="utf-8")


NOMBRES = {"top": "LO MÁS IMPORTANTE DEL DÍA", "colombia": "COLOMBIA", "latam": "LATINOAMÉRICA", "politica": "POLÍTICA",
           "tec": "TECNOLOGÍA", "juegos": "VIDEOJUEGOS", "cine": "CINE Y SERIES", "futbol": "FÚTBOL"}
IDIOMAS = {"en": " (en inglés)", "pt": " (en portugués)"}
EN_EL_RESUMEN = 12   # noticias por sección en el resumen corto


def resumen_corto(salida):
    """Texto corto para quien arma la edición: lo principal de cada sección con sus links."""
    trm = (salida["tasas"] or {}).get("trm")
    lineas = [f"# Candidatos de NicoPrensa para el {salida['fecha']}",
              f"Generado: {salida['generado']}. Feeds leídos: {salida['resumen']['feeds_leidos']}, "
              f"fallidos: {salida['resumen']['feeds_fallidos']}.",
              "TRM oficial de hoy: " + (f"{trm['valor']:.2f} pesos por dólar (vigente desde {trm['vigencia_desde']})"
                                        if trm else "no disponible"),
              "Cada noticia trae: [número de medios que la cubren: cuáles] titular, y debajo sus links directos.",
              "Las noticias están ordenadas de más a menos importante dentro de cada bloque."]
    bloques = [("top", salida["top"])] + [(s, salida["secciones"][s]) for s in
                                           ("colombia", "latam", "politica", "tec", "juegos", "cine", "futbol")]
    for clave, lista in bloques:
        lineas += ["", f"## {NOMBRES[clave]}"]
        for i, c in enumerate(lista[:EN_EL_RESUMEN], 1):
            total = c["n_medios"] + len(c["otros_medios"])
            medios = ", ".join((c["medios"] + c["otros_medios"])[:6])
            extra = f" | sección: {c['seccion']}" if clave == "top" else ""
            senal = f" | {c['senales'][0]}" if c["senales"] else ""
            lineas.append(f"{i}. [{total} {'medio' if total == 1 else 'medios'}: {medios}] {c['titular']}{extra}{senal}")
            directos = [x for x in c["links"] if not x.get("pista")]
            directos.sort(key=lambda x: x["idioma"] != "es")   # primero los links en español
            for x in directos[:2]:
                lineas.append(f"   {x['url']}{IDIOMAS.get(x['idioma'], '')}")
            if not directos:
                lineas.append("   (sin link directo: hay que buscarlo)")
    return "\n".join(lineas) + "\n"


def main():
    ahora = datetime.now(timezone.utc)
    hoy = ahora.astimezone(ZoneInfo("Europe/London")).date()
    estados, noticias = recoger(ahora)
    nuevas, todos = armar(noticias, hoy, ahora)
    secciones = {s: elegir(todos, s) for s in SECCIONES}

    top, usados = [], Counter()
    for c in todos:
        if c["n_medios"] + len(c["otros_medios"]) < 2 or usados[c["seccion"]] >= TOP_MAX_POR_SECCION:
            continue
        top.append(c)
        usados[c["seccion"]] += 1
        if len(top) == EN_TOP:
            break

    leidos = sum(e["ok"] for e in estados)
    salida = {
        "fecha": hoy.isoformat(),
        "generado": ahora.isoformat(timespec="seconds"),
        "version": 2,
        "ventana_horas": VENTANA_HORAS,
        "tasas": {"trm": trm_de_hoy(hoy)},
        "resumen": {
            "feeds_leidos": leidos, "feeds_fallidos": len(estados) - leidos,
            "titulares_recientes": len(noticias), "descartados_ya_publicados": len(noticias) - len(nuevas),
            "noticias_distintas": len(todos),
            "con_2_o_mas_medios": sum(1 for c in todos if c["n_medios"] >= 2),
            "pistas_sin_link_directo": sum(1 for c in todos if c["pista"]),
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
    guardar(salida, destino)
    (SALIDA / f"resumen-{hoy.isoformat()}.md").write_text(resumen_corto(salida), encoding="utf-8")
    borrar_viejos(hoy)

    r = salida["resumen"]
    print(f"Guardado {destino.relative_to(RAIZ)}")
    print(f"Feeds: {r['feeds_leidos']} leídos, {r['feeds_fallidos']} fallidos. "
          f"Titulares recientes: {r['titulares_recientes']}. Ya publicados: {r['descartados_ya_publicados']}. "
          f"Noticias distintas: {r['noticias_distintas']}.")
    for s in SECCIONES:
        varios = sum(1 for c in secciones[s] if c["n_medios"] >= 2)
        print(f"  {s:9s} {len(secciones[s]):2d} candidatos ({varios} con 2 o más medios)")
    print(f"  top       {len(top):2d} candidatos")
    for e in estados:
        if not e["ok"]:
            print(f"  FALLÓ {e['medio']} ({e['seccion']}): {e['error']}")

    # Si falla demasiado, el resultado se guarda igual pero la tarea termina en error,
    # para que GitHub avise por correo.
    normales = [e for e in estados if e["tipo"] == "rss"]
    if sum(e["ok"] for e in normales) < 0.6 * len(normales) or len(todos) < 100:
        print("ALERTA: fallaron demasiados feeds o salieron muy pocas noticias.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
