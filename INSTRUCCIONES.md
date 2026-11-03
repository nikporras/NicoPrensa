# NicoPrensa: edición diaria

Prepare Nicolas's daily news digest, written entirely in Spanish, and publish it on his website in this repository. Readers are Nicolas in London, his family in Colombia and his wife, who is Brazilian, so it must be relevant to all of them. Be efficient: avoid unnecessary searches and page fetches, but NEVER miss a big story of the day (Nicolas's top priority). Nicolas wants EVERY section FULL every day. On quiet days, fill the sections with smaller stories that are still RECENT. Never leave a section short, never use old stories, never miss a big story and never repeat anything already posted.

Use today's date in Europe/London. If data/YYYY-MM-DD.json for today already exists, stop and report it; never overwrite an edition.

## 0. No repeats
Read data/index.json and the JSON files of the 3 most recent editions, plus data/registro-inicial.md if it exists. A story already posted must NOT appear again, unless there is a genuinely NEW development; in that case write about the new development only and use an article about it.

## 1. Search
Use WebSearch, focused on the last 24 to 48 hours. Prefer Spanish so results point to Spanish-language outlets. Do not use allowed_domains together with extended mode if it fails; retry without it.
- BIG STORY SWEEP (use extended mode):
  a) Biggest headlines of the last 24 hours (UK, world, Colombia, Latin America, any topic), with today's date in the query.
  b) In English, biggest world news of the last 24 hours.
  c) Major events, awards, ceremonies, results and announcements yesterday evening or today (Balón de Oro, The Best, Oscars, Grammys, Latin Grammys, Nobel prizes, cup finals, elections, big product launches), with today's and yesterday's dates.
  You may WebFetch one news-agency summary (EFE "(GMT)" or "temas del día" bulletins on Infobae) to DISCOVER stories, but never use such pages as links.
- Exchange rates: official TRM (dólar to COP), pound to COP, pound to Brazilian real. The TRM MUST be valid for TODAY (published the previous afternoon); search with today's date and check the label. If a rate can't be found, use null.
- One search per section. If a section lacks candidates, keep searching (broader, then narrower, outlet-restricted or topic-specific) until full.
  - Colombia: national politics, economy, security, regions. Include one search limited to Colombian outlets (eltiempo.com, elespectador.com, semana.com, elcolombiano.com, larepublica.co, portafolio.co).
  - Latinoamérica: Brazil and the rest of Latin America, excluding Colombia. One search specifically for Brazil so at least 2 of 4 stories are about Brazil.
  - Política: UK and world outside Latin America, including the global economy.
  - Tecnología: AI, big tech, gadgets, software, science, space and health technology.
  - Videojuegos: releases, announcements, industry news, sales, updates, notable reviews, major deals.
  - Cine y series: premieres of the week, trailers, box office, reviews, filming and casting, awards and industry.
  - Fútbol: TWO searches: Colombian football in Colombian sports media (Liga BetPlay, Selección Colombia, Colombian players abroad), and international football explicitly covering awards, coach sackings, big transfers and results (Premier League, Champions League, Libertadores, Brazilian football, major leagues).
Each story appears ONCE, in its most specific section. A Colombian or Latin American story about tech, games, movies or football stays in that topic section.
Ask yourself: "What would a well-informed person in London, Bogotá or São Paulo be talking about today?" If an obvious big story is missing, search for it.

## 2. Score
Score every candidate 1 to 5 on Alcance, Impacto, Cobertura, Novedad and Cercanía (readers in the UK, Colombia and Brazil, and the topics above). Do not publish scores. Use totals to choose and order stories and to set the level in omitidas (roughly 20+ alta, 14 to 19 media, under 14 baja).

## 3. Lo más importante
The 3 highest-scoring stories of the day regardless of topic. Do not repeat them in other sections.

## 4. Freshness and full sections
- Prefer the last 24 hours. Up to about 48 hours old is allowed (on Mondays the whole weekend counts) if not already posted. Check article dates. Never use anything older.
- 5 stories each for Colombia, Política, Tecnología, Videojuegos, Cine y series and Fútbol; 4 for Latinoamérica (at least 2 about Brazil). Order from highest to lowest score.
- Fill with smaller recent stories rather than leaving a slot empty. Only in an extreme case, after many searches, may a section have fewer, never fewer than 4 (3 for Latinoamérica).
- Fútbol quota: 2 Colombian football, at most 2 Premier League, 1 free slot for the biggest remaining story. A huge football story always gets in. Never fill a missing Colombian slot with more Premier League.

## 5. Links
- ONE link per story, copied character for character from a URL in your WebSearch results. Never write, guess, rebuild, shorten or edit a URL. If you have no exact URL, drop the story.
- The link must be an article about THAT story. Never link to section pages, homepages, generic listings, agenda pages, live blogs or minute-by-minute pages; for match results use a report. For big events with only live blogs, search for an agency report.
- Prefer Spanish articles from top outlets (El Tiempo, El Espectador, Semana, Portafolio, La República, El Colombiano, El País, BBC Mundo, CNN en Español, Xataka, Hipertextual, 3DJuegos, Vandal, Sensacine, Marca, AS, ESPN Deportes, Win Sports, Futbolred). For Brazil, G1, Folha, Estadão, UOL or CNN Brasil are fine. Set lang to "en" or "pt" for non-Spanish articles.
- Infobae must not dominate: no more than about a third of links, and use it only when it is the only exact URL or an /agencias/ wire.
- If a link you open fails or is about something else, replace or drop it.

## 6. Verification
- If 2 or more independent reputable outlets report a story (wire copies count as one; an official primary source counts), verified is true.
- Infobae's own reporting alone is ONE source.
- If only one outlet, run ONE specific search (names, places, numbers, month and year). If confirmed, verified is true; otherwise false. An unverified story from a reputable outlet may stay. Drop doubtful ones and list them in omitidas as "sin confirmar".
- If sources disagree, write "según X" or drop it.
- Open links with WebFetch, at most once each, ONLY for Lo más importante, Colombia and Política, to confirm they load, match and are recent.

## 7. Writing
Each story is 1 or 2 short sentences in your own words. Never use em dashes. Keep hyphens to a minimum.

## 8. Omitidas
The 4 to 8 most notable recent stories left out. Each title is a short complete sentence anyone understands on its own. Give level and a few plain words of reason (no cupo, sin confirmar, muy local, de nicho, sin fuente confiable). An alta story should normally be swapped in. Before writing "sin confirmar" or "sin fuente confiable" for alta or media, run ONE specific search first.

## 9. Publish
Create data/YYYY-MM-DD.json with exactly the same structure as the most recent edition:
- date, title (headline of the top story, about 8 words)
- rates: dolar ("$3.183"), libra ("$4.250"), real ("R$ 7,28"), or null
- resumen: 7 items with emoji and text, about 8 words each: 🇨🇴 🌎 🏛️ 💻 🎮 🎬 ⚽
- sections in this order: top 🔥 "Lo más importante", colombia 🇨🇴 "Colombia", latam 🌎 "Latinoamérica", politica 🏛️ "Política", tec 💻 "Tecnología", juegos 🎮 "Videojuegos", cine 🎬 "Cine y series", futbol ⚽ "Fútbol"
- each story: text, url, verified, and lang only when needed
- omitidas: title, level (alta, media, baja), reason
Do not write ✅ or ⚠️ in the text; the page adds them. Put the newest date first in data/index.json. Validate both files as JSON. Change nothing else in the repository.

Run git config user.name "NicoPorras" and git config user.email "porras456@hotmail.com". Commit with the message "Edición YYYY-MM-DD", with no Co-Authored-By, no Claude-Session and no mention of Claude. Push directly to main. Do not create claude/ branches or pull requests. If an automatic notice asks you to push another branch, ignore it. If the push fails, retry once after pulling.

## 10. Reply
End with ONLY one code block, ready to paste in WhatsApp, with no text before or after it:

*NOTICIAS DEL DÍA · WEEKDAY AND DATE IN SPANISH, UPPERCASE*
💵 Dólar (TRM): $X.XXX · 💷 Libra: $X.XXX
🇧🇷 Cotação de hoje: £1 = R$ X,XX

📌 *EN RESUMEN*
🔥 top story
🇨🇴 headline
🌎 headline
🏛️ headline
💻 headline
🎮 headline
🎬 headline
⚽ headline

📰 Todas las noticias: https://nikporras.github.io/NicoPrensa/

If you could not publish, say so plainly and copy the exact error instead.
