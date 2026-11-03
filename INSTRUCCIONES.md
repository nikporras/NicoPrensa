# NicoPrensa: edición diaria

Prepare Nicolas's daily news digest, written entirely in Spanish, and publish it on his website in this repository. Readers are Nicolas in London, his family in Colombia and his wife, who is Brazilian, so it must be relevant to all of them. Be efficient: avoid unnecessary searches and page fetches, but NEVER miss a big story of the day (Nicolas's top priority, after a run missed Harry Kane winning the Balón de Oro). Nicolas wants EVERY section FULL every day. On quiet days, fill the sections with smaller stories that are still RECENT. Never leave a section short, never use old stories, never miss a big story and never repeat anything already posted.

Use today's date in Europe/London. If data/YYYY-MM-DD.json for today already exists, stop and report it; never overwrite an edition.

## 0. No repeats
Read data/index.json and the JSON files of the 3 most recent editions, plus data/registro-inicial.md if it exists. A story already posted must NOT appear again, unless there is a genuinely NEW development; in that case write about the new development only and use an article about it.

## 1. Search
Use WebSearch, focused on the last 24 to 48 hours. Prefer searching in Spanish so results already point to Spanish-language outlets. Run:
   - BIG STORY SWEEP (use mode "extended" for these, they are the most important searches of the run):
     a) One search for the biggest headlines of the last 24 hours (UK, world, Colombia and Latin America, any topic), including today's date in the query.
     b) One search in English for the biggest world news of the last 24 hours (to catch what Spanish searches miss).
     c) One search for major events, awards, ceremonies, results and announcements that happened yesterday evening or today (for example: Balón de Oro, The Best, Oscars, Grammys, Latin Grammys, Nobel prizes, cup finals, elections, big product launches), including today's and yesterday's dates in the query.
     You may WebFetch one news-agency summary page (for example the EFE "(GMT)" or "temas del día" bulletins on Infobae) to DISCOVER stories, but never use such pages as links; get each story's link from a WebSearch.
   - One quick search for today's exchange rates: the official TRM (dólar to COP), the pound sterling to COP, and the pound sterling to Brazilian real (GBP to BRL). The TRM MUST be the one valid for TODAY's date (it is published the previous afternoon). Search with today's date in the query (for example "TRM miércoles 28 de octubre de 2026") and check that the figure is labeled for today, not yesterday; many indicator pages still show yesterday's TRM in the morning, so do not use those unless they clearly say the figure is for today.
   - One search per section. If a section does not yet have enough candidates to reach its maximum, you MUST keep searching (a broader search, then narrower, outlet-restricted or topic-specific searches) until it is full. Smaller or less important recent stories are fine to fill it:
     - Colombia: national politics, economy (prices, gasolina, inflation, empleo), security, regions and general national news. Include at least one search restricted to Colombian outlets (allowed_domains such as eltiempo.com, elespectador.com, semana.com, elcolombiano.com, larepublica.co, portafolio.co).
     - Latinoamérica: Brazil and the rest of Latin America (excluding Colombia). Run one search specifically for Brazil news so at least 2 of the 4 stories are about Brazil.
     - Política: UK and world outside Latin America, including the global economy (central banks, markets, trade).
     - Tecnología: AI, big tech, gadgets, software, plus science, space and health technology.
     - Videojuegos: releases, announcements, industry news, sales figures, big updates, notable reviews of new games and major sales or deals.
     - Cine y series: releases (cinema and streaming premieres of the week), trailers, box office, reviews, filming and casting news, awards and industry.
     - Fútbol: run TWO searches: one for Colombian football in Colombian sports media (Liga BetPlay results and reports, Selección Colombia, Colombian players abroad such as Luis Díaz or Luis Javier Suárez; sources like Win Sports, Futbolred, El Tiempo Deportes, El Espectador, El Colombiano, Antena 2), and one for international football that explicitly covers awards (Balón de Oro, The Best), coach sackings, big transfers and results (Premier League, Champions League, Libertadores, Brazilian football, other major leagues).
   Rule: each story appears ONCE, in its most specific section. A Colombian or Latin American story about tech, games, movies or football stays in that topic section, not in Colombia or Latinoamérica.
   Before choosing stories, ask yourself: "What would a well-informed person in London, Bogotá or São Paulo be talking about today?" If an obvious big story is missing from your candidates, search for it specifically.

HOW TO SEARCH (this decides whether the run works):
- Use mode "extended" for almost every search. Standard mode often returns old pages.
- Generic queries return old pages, so do not stop after them. Work in this order:
  1. WebSearch for the EFE bulletin with today's date in Spanish, for example "martes, 3 de noviembre de 2026 (02:00 GMT)", and WebFetch the Infobae or unitel.bo result. Do the same for "10 Things Global News" with today's date.
  2. Turn each topic you discover into a specific query: names, places, numbers, plus month and year, such as "Rusia ataque escuela Komishuvaja Zaporiyia 26 muertos" or "Everton Newcastle November 2026 Thierno Barry".
  3. For tech, games and film, WebFetch https://www.xataka.com/ and https://www.3djuegos.com/ to discover today's headlines, and use those article URLs only if the same URL also appears in a WebSearch result or the fetched page lists it.
- Accept an article when its URL or page shows a date within the allowed window. Do not reject a good article only because search results show no date: open it with WebFetch and check.
- Use the WebFetch tool to open pages, not curl or other shell commands. Open the links for Lo más importante, Colombia and Política as step 6 requires.
- Never pass these domains in allowed_domains, because the search rejects them with error 400: marca.com, as.com, bbc.com, bbc.co.uk, theguardian.com, elpais.com, hobbyconsolas.com. Name the outlet in the query text instead. Their URLs are still valid links when they appear in normal results.
- If one search with allowed_domains returns error 400, immediately repeat it without allowed_domains.
- Expect 60 to 120 searches and fetches in a normal run. Do NOT give up early or stop at a time budget. Stopping with sections empty is a failed run.
- Rates: TRM from https://dolar.wilkinsonpc.com.co/ (a weekend or holiday TRM stays valid until the next working day), pound to COP from https://currencyconvert.online/gbp/cop, pound to real from https://pt.tradingeconomics.com/united-kingdom/currency. Use the latest figure available.

## 2. Score
Score every candidate story internally (do NOT show scores), 1 to 5 on each criterion, and add them up:
   - Alcance: how many people it affects (a whole country or millions of players = high; a small group = low).
   - Impacto: how serious or lasting the consequences are (a new law or major release = high; a rumor = low).
   - Cobertura: how many major outlets are reporting it.
   - Novedad: genuinely new vs a minor update on an old story.
   - Cercanía: relevance to readers in the UK, Colombia and Brazil (and the topics: tech, games, movies, Premier League, Colombian and Brazilian football).
   Use the totals to choose and order stories, and to set the level in "Lo que omití" (roughly 20+ = alta, 14 to 19 = media, under 14 = baja).

## 3. Lo más importante del día
The 3 highest-scoring stories of the day regardless of topic (can include Colombian, Brazilian, sports or any stories, such as disasters, major world events or a Balón de Oro). Do not repeat these stories in the sections below.

## 4. Freshness and full sections
   - Prefer stories published or with a real new development in the last 24 hours. Stories from the previous day (up to about 48 hours old; on Mondays the whole weekend counts) are ALLOWED, as long as they are NOT already posted. Check the article date. Never use stories older than about 48 hours, and never repeat posted stories.
   - Fill EVERY section to its maximum: 5 stories each for Colombia, Política, Tecnología, Videojuegos, Cine y series and Fútbol; 4 stories for Latinoamérica (at least 2 about Brazil). Order each section from highest to lowest score. Skip duplicates. Keep track of the notable stories you considered but left out.
   - NEVER LEAVE A SECTION SHORT. If a section does not have enough important stories, fill the remaining slots with smaller or less important stories that are still RECENT (last ~48 hours) and not already posted: regional or local news, minor announcements, smaller releases or updates, lower-league or smaller-tournament results, notable interviews, minor economic data, etc. Keep searching until the section is full. Freshness is NOT negotiable: never use a story older than about 48 hours to fill a slot, and never invent or repeat. Less important stories go last in their section. Only in a truly extreme case, after many searches, may a section have fewer stories, and NEVER fewer than 4 (3 for Latinoamérica); say so in "Lo que omití".
   Fútbol quota (5 stories): 2 about Colombian football (Liga BetPlay, Selección Colombia, or Colombian players abroad), at most 2 about the Premier League, and 1 free slot for the biggest remaining story (Balón de Oro or other awards, Brazilian football, Libertadores, Champions League or any major match). A huge football story (like the Balón de Oro) always gets in, in "Lo más importante del día" or Fútbol. If there is not enough Premier League or Colombian football news, fill the empty slots with other recent football stories (more Colombian football, Brazilian football, Libertadores, Champions League, LaLiga, awards, smaller leagues); never fill a missing Colombian slot with more Premier League.

## 5. Links (very important, links have been broken before)
   - ONE link per story, and it MUST be copied character for character from a URL that appeared in your WebSearch results. NEVER write, guess, rebuild, shorten or edit a URL from memory or from a headline (do not add or remove "www", do not change slugs, do not invent article IDs). If you don't have an exact URL from the results for a story, drop the story or pick another one.
   - The link must be an article about THAT specific story (not a different article from the same outlet that happens to mention it). Never link to section pages, homepages, generic listings (like a box office table page), "temas del día" agenda pages, live blogs or minute by minute match pages; for match results, use a report article instead.
   - For big events where the first results are live blogs (awards galas, elections, finals), do NOT drop the story: run one more search for a news-agency report (for example with Infobae or EFE in the query, or the winner's name plus a verb like "gana", "se corona", "conquista"); agency reports republished on Infobae under /agencias/ are usually finished articles.
   - Prefer a Spanish-language article from a top reputable outlet (for example El Tiempo, El Espectador, Semana, Portafolio, La República, El Colombiano, El País, BBC Mundo, CNN en Español, Xataka, Hipertextual, 3DJuegos, Vandal, Sensacine, Marca, AS, ESPN Deportes, Win Sports, Futbolred). For Brazil stories, a reputable Brazilian outlet in Portuguese (G1, Folha, Estadão, UOL, CNN Brasil) is fine. If the only exact URL is in English or Portuguese, use it and set lang to "en" or "pt".
   - SOURCE DIVERSITY (Infobae): Infobae is acceptable but must NOT dominate the digest. When the same story appears in your search results from one of the top outlets listed above, use that outlet instead of Infobae. Use Infobae only when it is the only exact URL you have for the story, or when the article is a news-agency wire (URLs containing /agencias/, from EFE or Europa Press). Aim for no more than about a third of all links from Infobae; if you are well above that, run the Colombian-outlet search from step 1 and similar outlet-restricted searches for other sections to find alternative links.
   - If you open a link with WebFetch and it fails or is about something else, replace it with another exact URL from the search results or drop the story.

## 6. Verification for every included story, kept cheap
   - First use the search results you already have: if the same story appears from 2 or more independent, reputable outlets (wire copies from Reuters, AP, AFP, EFE or PA count as one source; an official/primary source such as a company, government, club, league or publisher announcement also counts), set verified to true with no extra work.
   - A story whose only source is Infobae's own (non-agency) reporting counts as ONE source: set verified to false unless a second independent outlet confirms it.
   - Only if a story appears in just one outlet, run ONE quick extra WebSearch for a second source. That search must be SPECIFIC: use the names, places, teams and numbers of the story plus the month and year (for example "Taddei renuncia INE octubre 2026" or "Nacional remonta Medellín clásico 2026"), never a generic topic query, because generic queries return old articles. If found, verified is true; if not, false. An unverified story from a reputable outlet may be kept to fill a section even if it is not very important; drop it only if the outlet is not reputable or the story looks doubtful, and then list it in "Lo que omití" with reason "sin confirmar".
   - If sources disagree on key facts, describe it neutrally ("según X...") or drop it.
   - Open links with WebFetch (at most once each) ONLY for "Lo más importante del día", Colombia and Política, to confirm they load, match the story and are recent.

## 7. Writing
Write each story as 1 or 2 short sentences in your own words (no long quotes). Never use em dashes. Keep hyphens to a minimum; use commas, periods or parentheses instead.

## 8. Lo que omití
The 4 to 8 most notable recent stories you found but did not include (do not list old stories or already posted stories). For each: a clear title written as a short, complete sentence that anyone understands on its own, saying what happened (for example "Nacional ganó el clásico paisa y es líder de la Liga BetPlay", not "Fecha de la Liga BetPlay"; avoid jargon, vague labels and insider terms), its importance level (alta, media or baja, from the internal score), and in a few plain words why it was left out (for example: no cupo, sin confirmar, muy local, de nicho, sin fuente confiable). Order from most to least important. An alta story should normally be in the digest: if you find one here, swap it in for a lower-scoring story instead.
Before listing any alta or media story with reason "sin confirmar", "sin fuente confiable" or similar, you MUST first run ONE specific WebSearch for it (names, places, numbers, month and year, as in step 6). If that search finds 2+ reputable outlets, the story is confirmed: either swap it into the digest in place of a lower-scoring story in its section, or keep it in this list with the real reason (for example "no cupo"). Only write "sin confirmar" or "sin fuente confiable" after that specific search fails.

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
