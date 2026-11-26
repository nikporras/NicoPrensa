(function () {
  "use strict";
  var app = document.getElementById("app");
  var menu = document.getElementById("menu");
  var menuBtn = document.getElementById("menuBtn");
  var list = document.getElementById("menuList");
  var DIAS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];
  var MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  var NIVEL = { alta: "Alta", media: "Media", baja: "Baja" };
  var LANG = { en: "en inglés", pt: "en portugués" };
  var FUENTES = {
    "semana.com": "Semana", "eltiempo.com": "El Tiempo", "elespectador.com": "El Espectador", "elcolombiano.com": "El Colombiano",
    "larepublica.co": "La República", "portafolio.co": "Portafolio", "infobae.com": "Infobae", "elpais.com": "El País",
    "bbc.com": "BBC", "bbc.co.uk": "BBC", "theguardian.com": "The Guardian", "cnbc.com": "CNBC", "reuters.com": "Reuters",
    "apnews.com": "AP", "cnn.com": "CNN", "cnnespanol.cnn.com": "CNN en Español", "kyivpost.com": "Kyiv Post",
    "g1.globo.com": "G1", "folha.uol.com.br": "Folha", "estadao.com.br": "Estadão", "uol.com.br": "UOL",
    "xataka.com": "Xataka", "3djuegos.com": "3DJuegos", "vandal.elespanol.com": "Vandal", "sensacine.com": "Sensacine",
    "marca.com": "Marca", "as.com": "AS", "espn.com": "ESPN", "winsports.co": "Win Sports", "futbolred.com": "Futbolred"
  };
  // Ciudades de la familia: debajo del clima se muestran las que no son la tuya.
  var CIUDADES = [
    { nombre: "Londres", lat: 51.5074, lon: -0.1278 },
    { nombre: "Bogotá", lat: 4.711, lon: -74.0721 },
    { nombre: "São Paulo", lat: -23.5505, lon: -46.6333 }
  ];

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }
  function fechaLarga(iso) {
    var p = String(iso).split("-").map(Number);
    var d = new Date(p[0], p[1] - 1, p[2]);
    return DIAS[d.getDay()] + " " + p[2] + " de " + MESES[p[1] - 1] + " de " + p[0];
  }
  function mayus(s) { return s.charAt(0).toUpperCase() + s.slice(1); }
  function cargar(url, opts) {
    return fetch(url, opts || { cache: "no-cache" }).then(function (r) {
      if (!r.ok) throw new Error(String(r.status));
      return r.json();
    });
  }
  function esHttps(u) { return /^https:\/\//i.test(String(u || "")); }
  function error() {
    app.textContent = "";
    app.appendChild(el("p", "note", "No pudimos cargar esta edición. Revisa tu conexión y vuelve a abrir la página."));
  }
  function plural(n) { return n + (n === 1 ? " noticia" : " noticias"); }
  function fuente(url) {
    try {
      var h = new URL(url).hostname.replace(/^www\./, "");
      if (FUENTES[h]) return FUENTES[h];
      var partes = h.split(".");
      for (var i = 1; i < partes.length - 1; i++) {
        var base = partes.slice(i).join(".");
        if (FUENTES[base]) return FUENTES[base];
      }
      return mayus(partes[0]);
    } catch (e) { return ""; }
  }
  // Ediciones nuevas: cuántos medios traen la noticia. Ediciones viejas: confirmada o una fuente.
  function etiqueta(st) {
    if (typeof st.medios === "number" && st.medios > 0) {
      var clase = st.medios >= 5 ? "big" : st.medios >= 2 ? "mid" : "few";
      return el("span", "chip " + clase, st.medios + (st.medios === 1 ? " medio" : " medios"));
    }
    return chip(st.verified);
  }
  function chip(verificada) {
    return el("span", "chip " + (verificada ? "ok" : "one"), verificada ? "Confirmada" : "Una fuente");
  }
  function boton(cls, url) {
    var a = el("a", cls, "Leer noticia");
    a.href = url;
    a.target = "_blank";
    a.rel = "noopener";
    return a;
  }
  function momento(h) { return h >= 5 && h < 12 ? 0 : h >= 12 && h < 19 ? 1 : 2; }

  /* ---------- Saludo ---------- */
  function saludo(ed, esUltima) {
    var s = el("section", "hello");
    if (esUltima) {
      var h1 = el("h1", "", ["Buenos días", "Buenas tardes", "Buenas noches"][momento(new Date().getHours())]);
      h1.id = "saludo";
      s.appendChild(h1);
      s.appendChild(el("p", "", "Esto es lo que pasa hoy."));
    } else {
      s.appendChild(el("span", "past", "Edición anterior"));
      s.appendChild(el("h1", "", mayus(fechaLarga(ed.date).replace(/ de \d{4}$/, ""))));
      s.appendChild(el("p", "", ed.title));
    }
    var when = el("p", "when", mayus(fechaLarga(ed.date)));
    when.id = "cuando";
    s.appendChild(when);
    return s;
  }

  /* ---------- Carrusel ---------- */
  function dividir(texto) {
    var m = String(texto).match(/^(.{30,}?[.:])\s+(.+)$/);
    if (m) return [m[1].replace(/[.:]$/, ""), mayus(m[2])];
    return [texto, ""];
  }
  function carrusel(sec) {
    var g = el("section", "group");
    g.setAttribute("aria-label", sec.title);
    g.appendChild(el("p", "lead", "Lo más importante del día"));
    var rail = el("div", "rail");
    var dots = el("div", "dots");
    (sec.stories || []).forEach(function (st, i) {
      var c = el("article", "story-card art-" + (i % 3));
      var partes = dividir(st.text);
      var src = esHttps(st.url) ? fuente(st.url) : "";
      if (LANG[st.lang]) src += (src ? " · " : "") + LANG[st.lang];
      if (src) c.appendChild(el("span", "src", src));
      c.appendChild(el("h3", "", partes[0]));
      if (partes[1]) c.appendChild(el("p", "more", partes[1]));
      var row = el("div", "row");
      row.appendChild(etiqueta(st));
      if (esHttps(st.url)) row.appendChild(boton("ghost", st.url));
      c.appendChild(row);
      rail.appendChild(c);
      var d = el("button");
      d.type = "button";
      d.setAttribute("aria-label", "Noticia " + (i + 1) + " de " + sec.stories.length);
      if (i === 0) d.setAttribute("aria-current", "true");
      d.addEventListener("click", function () { rail.scrollTo({ left: i * rail.clientWidth, behavior: "smooth" }); });
      dots.appendChild(d);
    });
    rail.addEventListener("scroll", function () {
      var i = Math.round(rail.scrollLeft / Math.max(1, rail.clientWidth));
      Array.prototype.forEach.call(dots.children, function (d, k) {
        if (k === i) d.setAttribute("aria-current", "true"); else d.removeAttribute("aria-current");
      });
    }, { passive: true });
    g.appendChild(rail);
    if ((sec.stories || []).length > 1) g.appendChild(dots);
    return g;
  }

  /* ---------- Tarjetas rápidas ---------- */
  function enPocas(items) {
    var c = el("section", "card");
    c.appendChild(el("h2", "", "En pocas palabras"));
    var ul = el("ul", "brief");
    items.forEach(function (r) {
      var li = el("li");
      li.appendChild(el("span", "e", r.emoji));
      li.appendChild(el("span", "", r.text));
      ul.appendChild(li);
    });
    c.appendChild(ul);
    return c;
  }
  function numero(s) {
    var t = String(s || "").replace(/[^\d.,]/g, "").replace(/\./g, "").replace(",", ".");
    var n = parseFloat(t);
    return isNaN(n) ? null : n;
  }
  function tasas(rates) {
    var c = el("section", "card");
    c.appendChild(el("h2", "", "Tasas de hoy"));
    var dl = el("dl", "rates");
    var cajas = {};
    [["dolar", "Dólar TRM"], ["libra", "Libra"], ["real", "£ a real"]].forEach(function (x) {
      var w = el("div", "rate");
      w.appendChild(el("dt", "", x[1]));
      var val = (rates && rates[x[0]]) || "No disponible";
      var n = numero(val);
      // Los pesos se muestran sin centavos para que quepan en el celular.
      if (n !== null && n >= 1000) val = val.replace(/,\d+\s*$/, "");
      var dd = el("dd", "", val);
      dd.title = (rates && rates[x[0]]) || "";
      w.appendChild(dd);
      dl.appendChild(w);
      cajas[x[0]] = dd;
    });
    c.appendChild(dl);
    c.comparar = function (antes) {
      Object.keys(cajas).forEach(function (k) {
        var a = numero(antes && antes[k]), b = numero(rates && rates[k]);
        if (a === null || b === null || !a) return;
        var p = (b - a) / a * 100;
        var txt = Math.abs(p) < 0.05 ? "= igual" : (p > 0 ? "▲ " : "▼ ") + Math.abs(p).toFixed(1).replace(".", ",") + "%";
        var v = el("span", "var", txt);
        v.title = "Frente a la edición anterior";
        cajas[k].appendChild(v);
      });
    };
    return c;
  }

  /* ---------- Clima ---------- */
  var WMO = [
    [[0], "Despejado", "☀️", "🌙", "soleada", "despejada"],
    [[1], "Mayormente despejado", "🌤️", "🌙", "soleada", "despejada"],
    [[2], "Parcialmente nublado", "⛅", "☁️", "parcialmente nublada", "parcialmente nublada"],
    [[3], "Nublado", "☁️", "☁️", "nublada", "nublada"],
    [[45, 48], "Niebla", "🌫️", "🌫️", "con niebla", "con niebla"],
    [[51, 53, 55, 56, 57], "Llovizna", "🌦️", "🌧️", "con llovizna", "con llovizna"],
    [[61, 63, 65, 66, 67, 80, 81, 82], "Lluvia", "🌧️", "🌧️", "lluviosa", "lluviosa"],
    [[71, 73, 75, 77, 85, 86], "Nieve", "🌨️", "🌨️", "con nieve", "con nieve"],
    [[95, 96, 99], "Tormenta", "⛈️", "⛈️", "con tormenta", "con tormenta"]
  ];
  function wmo(code) {
    for (var i = 0; i < WMO.length; i++) if (WMO[i][0].indexOf(code) !== -1) return WMO[i];
    return WMO[3];
  }
  function icono(code, dia) { var w = wmo(code); return dia ? w[2] : w[3]; }
  function grados(t) { return Math.round(t) + "°"; }
  function hora12(iso) {
    var h = Number(String(iso).slice(11, 13));
    return (h % 12 || 12) + (h < 12 ? " am" : " pm");
  }
  function distancia(a, b, c, d) {
    var r = Math.PI / 180, x = (c - a) * r, y = (d - b) * r;
    var s = Math.sin(x / 2) * Math.sin(x / 2) + Math.cos(a * r) * Math.cos(c * r) * Math.sin(y / 2) * Math.sin(y / 2);
    return 12742 * Math.asin(Math.sqrt(s));
  }
  function pronostico(lats, lons) {
    return cargar("https://api.open-meteo.com/v1/forecast?latitude=" + lats.join(",") + "&longitude=" + lons.join(",") +
      "&current=temperature_2m,weather_code,is_day&hourly=temperature_2m,weather_code,is_day" +
      "&daily=temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=2", {}).then(function (r) {
      return Array.isArray(r) ? r : [r];
    });
  }
  function nombreLugar(lat, lon) {
    return cargar("https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=" + lat + "&longitude=" + lon + "&localityLanguage=es", {})
      .then(function (r) { return r.city || r.locality || r.principalSubdivision || "Tu ubicación"; })
      .catch(function () { return "Tu ubicación"; });
  }
  function ciudadesBox(cercana) {
    var otras = CIUDADES.filter(function (c) { return c !== cercana; });
    var box = el("div", "cities");
    if (otras.length > 2) box.className += " three";
    pronostico(otras.map(function (c) { return c.lat; }), otras.map(function (c) { return c.lon; })).then(function (rs) {
      rs.forEach(function (r, i) {
        var cur = r.current;
        var d = el("div", "city");
        d.appendChild(el("span", "i", icono(cur.weather_code, cur.is_day)));
        var t = el("div");
        t.appendChild(el("b", "", grados(cur.temperature_2m)));
        t.appendChild(el("span", "", otras[i].nombre));
        d.appendChild(t);
        box.appendChild(d);
      });
    }).catch(function () { box.hidden = true; });
    return box;
  }
  function clima() {
    var g = el("section", "group");
    var lead = el("p", "lead", "¿Qué tiempo hace donde estás?");
    var c = el("div", "card weather");
    var h2 = el("h2", "", "El tiempo");
    var lugar = el("small");
    lugar.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s-6.5-6.1-6.5-11a6.5 6.5 0 0 1 13 0c0 4.9-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/></svg>';
    var lugarTxt = el("span");
    lugar.appendChild(lugarTxt);
    lugar.hidden = true;
    h2.appendChild(lugar);
    c.appendChild(h2);
    var cuerpo = el("div");
    c.appendChild(cuerpo);
    g.appendChild(lead);
    g.appendChild(c);

    // La ubicación se guarda en este teléfono para no volver a pedirla en cada visita.
    function recordar(lat, lon) {
      try { localStorage.setItem("nicoprensa-ubicacion", JSON.stringify({ lat: lat, lon: lon })); } catch (e) {}
    }
    function recordada() {
      try {
        var u = JSON.parse(localStorage.getItem("nicoprensa-ubicacion") || "null");
        return u && typeof u.lat === "number" && typeof u.lon === "number" ? u : null;
      } catch (e) { return null; }
    }
    function pedir() {
      if (!navigator.geolocation) return sinPermiso("Este navegador no puede compartir la ubicación.");
      btn.disabled = true;
      btn.textContent = "Buscando tu ubicación…";
      navigator.geolocation.getCurrentPosition(function (pos) {
        recordar(pos.coords.latitude, pos.coords.longitude);
        mostrar(pos.coords.latitude, pos.coords.longitude);
      }, function (e) {
        sinPermiso(e && e.code === 1
          ? "No diste permiso de ubicación. Puedes activarlo en los ajustes del navegador para este sitio."
          : "No pudimos encontrar tu ubicación. Inténtalo de nuevo.");
      }, { enableHighAccuracy: false, timeout: 15000, maximumAge: 1800000 });
    }
    function sinPermiso(msg) {
      cuerpo.textContent = "";
      cuerpo.appendChild(el("p", "", msg));
      btn.disabled = false;
      btn.textContent = "Usar mi ubicación";
      cuerpo.appendChild(btn);
      cuerpo.appendChild(ciudadesBox(null));
    }
    function mostrar(lat, lon) {
      var cercana = null;
      CIUDADES.forEach(function (ci) { if (distancia(lat, lon, ci.lat, ci.lon) < 150) cercana = ci; });
      Promise.all([pronostico([lat], [lon]), cercana ? Promise.resolve(cercana.nombre) : nombreLugar(lat, lon)]).then(function (res) {
        var r = res[0][0], nombre = res[1];
        var cur = r.current, w = wmo(cur.weather_code);
        var horaLocal = Number(String(cur.time).slice(11, 13));
        var m = momento(horaLocal);
        var saludo = document.getElementById("saludo");
        if (saludo) saludo.textContent = ["Mañana", "Tarde", "Noche"][m] + " " + (cur.is_day ? w[4] : w[5]);
        var cuando = document.getElementById("cuando");
        if (cuando && !cuando.dataset.t) { cuando.dataset.t = "1"; cuando.textContent += " · " + grados(cur.temperature_2m) + " en " + nombre; }
        lead.textContent = w[1] + " en " + nombre + ". Máxima " + grados(r.daily.temperature_2m_max[0]) + "C, mínima " + grados(r.daily.temperature_2m_min[0]) + "C.";
        lugarTxt.textContent = nombre;
        lugar.hidden = false;
        cuerpo.textContent = "";
        var hrs = el("div", "hours");
        var desde = r.hourly.time.indexOf(String(cur.time).slice(0, 13) + ":00");
        if (desde < 0) desde = 0;
        for (var i = desde; i < desde + 6 && i < r.hourly.time.length; i++) {
          var d = el("div");
          d.appendChild(el("span", "", i === desde ? "Ahora" : hora12(r.hourly.time[i])));
          d.appendChild(el("span", "i", icono(r.hourly.weather_code[i], r.hourly.is_day[i])));
          d.appendChild(el("b", "", grados(i === desde ? cur.temperature_2m : r.hourly.temperature_2m[i])));
          hrs.appendChild(d);
        }
        cuerpo.appendChild(hrs);
        cuerpo.appendChild(ciudadesBox(cercana));
        var otra = el("button", "relocate", "Actualizar mi ubicación");
        otra.type = "button";
        otra.addEventListener("click", function () { otra.disabled = true; otra.textContent = "Buscando tu ubicación…"; pedir(); });
        cuerpo.appendChild(otra);
      }).catch(function () { sinPermiso("No pudimos cargar el clima. Inténtalo de nuevo."); });
    }

    var btn = el("button", "locbtn", "Usar mi ubicación");
    btn.type = "button";
    btn.addEventListener("click", pedir);
    cuerpo.appendChild(el("p", "", "Comparte tu ubicación para ver el clima de tu ciudad hora por hora."));
    cuerpo.appendChild(btn);
    cuerpo.appendChild(ciudadesBox(null));

    // Si ya diste permiso antes, el clima aparece solo.
    var guardada = recordada();
    if (guardada) mostrar(guardada.lat, guardada.lon);
    return g;
  }

  /* ---------- Secciones ---------- */
  function seccion(s, abierta) {
    var d = el("details", "sec c-" + s.id);
    d.id = "sec-" + s.id;
    d.open = abierta;
    var sum = el("summary");
    sum.appendChild(el("span", "ico", s.emoji));
    sum.appendChild(el("span", "t", s.title));
    sum.appendChild(el("span", "n", plural((s.stories || []).length + (s.tambien || []).length)));
    d.appendChild(sum);
    var ul = el("ul");
    (s.stories || []).forEach(function (st) {
      var li = el("li");
      li.appendChild(el("p", "", st.text));
      var meta = el("div", "meta");
      meta.appendChild(etiqueta(st));
      if (esHttps(st.url)) meta.appendChild(boton("read", st.url));
      if (LANG[st.lang]) meta.appendChild(el("span", "lang", LANG[st.lang]));
      li.appendChild(meta);
      ul.appendChild(li);
    });
    d.appendChild(ul);
    var mas = (s.tambien || []).filter(function (t) { return t && t.text && esHttps(t.url); });
    if (mas.length) {   // titulares con link, sin resumen
      var caja = el("div", "also");
      caja.appendChild(el("h4", "", "También hoy"));
      var lista = el("ul");
      mas.forEach(function (t) {
        var li = el("li");
        var a = el("a");
        a.href = t.url;
        a.target = "_blank";
        a.rel = "noopener";
        a.appendChild(el("span", "", t.text));
        var dato = [fuente(t.url)];
        if (LANG[t.lang]) dato.push(LANG[t.lang]);
        if (typeof t.medios === "number" && t.medios > 1) dato.push(t.medios + " medios");
        a.appendChild(el("span", "", dato.filter(Boolean).join(" · ")));
        li.appendChild(a);
        lista.appendChild(li);
      });
      caja.appendChild(lista);
      d.appendChild(caja);
    }
    return d;
  }
  function omitidas(items) {
    var d = el("details", "sec");
    d.id = "sec-omitidas";
    var sum = el("summary");
    sum.appendChild(el("span", "ico", "🗂️"));
    sum.appendChild(el("span", "t", "Lo que quedó por fuera"));
    sum.appendChild(el("span", "n", plural(items.length)));
    d.appendChild(sum);
    var ul = el("ul");
    items.forEach(function (o) {
      var li = el("li");
      li.appendChild(el("p", "", o.title));
      li.appendChild(el("p", "why", (NIVEL[o.level] ? "Importancia " + NIVEL[o.level].toLowerCase() + ". " : "") + mayus(String(o.reason || "")) + "."));
      ul.appendChild(li);
    });
    d.appendChild(ul);
    return d;
  }

  function pintar(ed, esUltima, anterior) {
    app.textContent = "";
    app.appendChild(saludo(ed, esUltima));
    var secs = ed.sections || [];
    var top = secs.filter(function (s) { return s.id === "top"; })[0];
    var resto = secs.filter(function (s) { return s !== top; });
    if (top && top.stories && top.stories.length) app.appendChild(carrusel(top));
    if (ed.resumen && ed.resumen.length) app.appendChild(enPocas(ed.resumen));
    var t = tasas(ed.rates);
    app.appendChild(t);
    if (anterior) anterior.then(function (a) { t.comparar(a.rates); }).catch(function () {});
    if (esUltima) app.appendChild(clima());
    var g = el("section", "group");
    g.appendChild(el("p", "lead", "Todas las noticias"));
    var box = el("div", "secs");
    resto.forEach(function (s, i) { box.appendChild(seccion(s, i === 0)); });
    if (ed.omitidas && ed.omitidas.length) box.appendChild(omitidas(ed.omitidas));
    g.appendChild(box);
    app.appendChild(g);
    // El pie explica las etiquetas de esta edición.
    var pie = document.getElementById("pie");
    var conMedios = secs.some(function (s) { return (s.stories || []).some(function (st) { return typeof st.medios === "number"; }); });
    if (pie) {
      pie.textContent = "";
      if (conMedios) {
        pie.appendChild(el("span", "", "El número de medios indica cuántos periódicos y portales traen la misma noticia. Cuantos más, más grande es."));
      } else {
        pie.appendChild(el("span", "chip ok", "Confirmada"));
        pie.appendChild(el("span", "", "2 o más fuentes"));
        pie.appendChild(el("span", "chip one", "Una fuente"));
        pie.appendChild(el("span", "", "sin segunda confirmación"));
      }
    }
    document.title = "NicoPrensa · " + fechaLarga(ed.date);
    window.scrollTo(0, 0);
  }

  function menuDias(eds, actual) {
    list.textContent = "";
    var meses = [];
    eds.forEach(function (e, i) {
      var clave = String(e.date).slice(0, 7);
      var g = meses[meses.length - 1];
      if (!g || g.clave !== clave) { g = { clave: clave, eds: [] }; meses.push(g); }
      g.eds.push({ date: e.date, ultima: i === 0 });
    });
    meses.forEach(function (g, i) {
      var p = g.clave.split("-").map(Number);
      var li = el("li");
      var d = el("details", "mes");
      d.open = i === 0 || g.eds.some(function (e) { return e.date === actual; });
      var sum = el("summary");
      sum.appendChild(el("span", "", mayus(MESES[p[1] - 1]) + " " + p[0]));
      sum.appendChild(el("span", "n", g.eds.length + (g.eds.length === 1 ? " día" : " días")));
      d.appendChild(sum);
      var ul = el("ul");
      g.eds.forEach(function (e) {
        var di = el("li");
        var dd = new Date(e.date + "T12:00:00");
        var a = el("a", "", mayus(DIAS[dd.getDay()]).slice(0, 3) + " " + Number(e.date.slice(8)));
        a.href = e.ultima ? "./" : "?fecha=" + encodeURIComponent(e.date);
        a.title = fechaLarga(e.date);
        if (e.date === actual) a.setAttribute("aria-current", "page");
        di.appendChild(a);
        ul.appendChild(di);
      });
      d.appendChild(ul);
      li.appendChild(d);
      list.appendChild(li);
    });
  }
  menuBtn.addEventListener("click", function () {
    menu.hidden = !menu.hidden;
    menuBtn.setAttribute("aria-expanded", String(!menu.hidden));
  });
  cargar("data/index.json").then(function (idx) {
    var eds = idx.editions || [];
    if (!eds.length) throw new Error("vacío");
    var pedida = new URLSearchParams(location.search).get("fecha");
    var pos = 0;
    eds.forEach(function (x, i) { if (x.date === pedida) pos = i; });
    var e = eds[pos];
    menuDias(eds, e.date);
    var anterior = eds[pos + 1] ? cargar("data/" + eds[pos + 1].date + ".json") : null;
    return cargar("data/" + e.date + ".json").then(function (ed) { pintar(ed, pos === 0, anterior); });
  }).catch(error);
})();
