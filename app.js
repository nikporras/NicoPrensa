(function () {
  "use strict";
  var app = document.getElementById("app");
  var menu = document.getElementById("menu");
  var menuBtn = document.getElementById("menuBtn");
  var list = document.getElementById("menuList");
  var DIAS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];
  var MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  var NIVEL = { alta: "🔴 Alta", media: "🟡 Media", baja: "🟢 Baja" };
  var LANG = { en: "en inglés", pt: "en portugués" };

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
  function cargar(url) {
    return fetch(url, { cache: "no-cache" }).then(function (r) {
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

  function seccion(s, abierta) {
    var d = el("details");
    d.id = "sec-" + s.id;
    d.open = abierta;
    var sum = el("summary");
    sum.appendChild(el("span", "", s.emoji));
    sum.appendChild(el("span", "", s.title));
    sum.appendChild(el("span", "n", plural((s.stories || []).length)));
    d.appendChild(sum);
    var ul = el("ul", "stories");
    (s.stories || []).forEach(function (st) {
      var li = el("li", "story");
      li.appendChild(el("p", "", (st.verified ? "✅ " : "⚠️ ") + st.text));
      if (esHttps(st.url)) {
        var a = el("a", "btn", "Leer noticia");
        a.href = st.url;
        a.target = "_blank";
        a.rel = "noopener";
        if (LANG[st.lang]) { var s2 = el("span", "lang", " (" + LANG[st.lang] + ")"); a.appendChild(s2); }
        li.appendChild(a);
      }
      ul.appendChild(li);
    });
    d.appendChild(ul);
    return d;
  }
  function omitidas(items) {
    var d = el("details");
    d.id = "sec-omitidas";
    var sum = el("summary");
    sum.appendChild(el("span", "", "🗂️"));
    sum.appendChild(el("span", "", "Lo que quedó por fuera"));
    sum.appendChild(el("span", "n", plural(items.length)));
    d.appendChild(sum);
    var box = el("div", "om");
    items.forEach(function (o) {
      var r = el("div");
      r.appendChild(el("p", "", o.title));
      r.appendChild(el("p", "why", (NIVEL[o.level] || "") + " · " + o.reason));
      box.appendChild(r);
    });
    d.appendChild(box);
    return d;
  }
  function pintar(ed, esUltima) {
    app.textContent = "";
    if (!esUltima) app.appendChild(el("p", "past", "Edición anterior"));
    app.appendChild(el("p", "date", fechaLarga(ed.date)));
    var h = el("h1");
    h.appendChild(el("span", "", ed.title));
    app.appendChild(h);
    var dl = el("dl", "rates");
    [["Dólar TRM", ed.rates && ed.rates.dolar], ["Libra", ed.rates && ed.rates.libra], ["£ a real", ed.rates && ed.rates.real]].forEach(function (x) {
      var w = el("div", "rate");
      w.appendChild(el("dt", "", x[0]));
      w.appendChild(el("dd", "", x[1] || "No disponible"));
      dl.appendChild(w);
    });
    app.appendChild(dl);
    var br = el("ul", "brief");
    (ed.resumen || []).forEach(function (r) {
      var li = el("li");
      li.appendChild(el("span", "", r.emoji));
      li.appendChild(el("span", "", r.text));
      br.appendChild(li);
    });
    app.appendChild(br);
    var secs = el("div", "secs");
    (ed.sections || []).forEach(function (s, i) { secs.appendChild(seccion(s, i === 0)); });
    if (ed.omitidas && ed.omitidas.length) secs.appendChild(omitidas(ed.omitidas));
    app.appendChild(secs);
    document.title = "NicoPrensa · " + fechaLarga(ed.date);
    window.scrollTo(0, 0);
  }
  function menuDias(eds, actual) {
    list.textContent = "";
    eds.forEach(function (e, i) {
      var li = el("li");
      var a = el("a", "", fechaLarga(e.date));
      a.href = i === 0 ? "./" : "?fecha=" + encodeURIComponent(e.date);
      if (e.date === actual) a.setAttribute("aria-current", "page");
      li.appendChild(a);
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
    var e = eds.filter(function (x) { return x.date === pedida; })[0] || eds[0];
    menuDias(eds, e.date);
    return cargar("data/" + e.date + ".json").then(function (ed) { pintar(ed, e.date === eds[0].date); });
  }).catch(error);
})();
