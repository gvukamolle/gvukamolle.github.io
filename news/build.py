#!/usr/bin/env python3
"""Validate digest.json and render accessible, JavaScript-independent news HTML."""
import json, math, re
from pathlib import Path
from datetime import datetime, date, timezone
from html import escape as e
from urllib.parse import urlparse
ROOT = Path(__file__).resolve().parent
MONTHS = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря']

def render(data):
    day = date.fromisoformat(data['edition_date'])
    updated = datetime.fromisoformat(data['updated_at'].replace('Z','+00:00'))
    assert updated.tzinfo is not None, 'updated_at requires timezone'
    assert updated <= datetime.now(timezone.utc), 'Future publication timestamp'
    sections = data['sections']
    assert 1 <= len(sections) <= 3
    ids, words, cols, count = set(), 0, [], 0
    for section in sections:
        assert isinstance(section['title'], str) and section['title']
        assert isinstance(section['subtitle'], str)
        cards = []
        for item in section['items']:
            assert re.fullmatch(r'[a-z0-9-]+', item['id']) and item['id'] not in ids
            ids.add(item['id'])
            event_date = date.fromisoformat(item['date'])
            assert event_date <= day, 'Future news must be explicitly a planned event, not a past fact'
            assert 10 <= len(item['title']) <= 150
            assert 40 <= len(item['text']) <= 950
            assert 1 <= len(item['sources']) <= 4
            sources = []
            for source in item['sources']:
                url = urlparse(source['url'])
                assert url.scheme == 'https' and url.hostname and not url.username and not url.password
                sources.append(f'<a href="{e(source["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{e(source["name"])}</a>')
            words += len((item['title']+' '+item['text']).split())
            count += 1
            cards.append(f'''<article class="story" id="{e(item['id'])}">
<div class="story-meta"><span>{e(item['kind'])}</span><time datetime="{event_date.isoformat()}">{event_date.day:02}.{event_date.month:02}</time></div>
<h3>{e(item['title'])}</h3><p>{e(item['text'])}</p>
<div class="sources" aria-label="Источники">{''.join(sources)}</div></article>''')
        assert cards, 'Empty sections should be omitted'
        cols.append(f'''<section class="column" aria-labelledby="column-{len(cols)}"><div class="column-head"><div><h2 id="column-{len(cols)}">{e(section['title'])}</h2><p>{e(section['subtitle'])}</p></div><span class="count" aria-label="Количество заметок">{len(cards)}</span></div><div class="cards">{''.join(cards)}</div></section>''')
    assert 1 <= count <= 12
    duration = max(1, math.ceil(words / 160))
    date_label = f'{day.day} {MONTHS[day.month-1]}'
    return f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light dark"><meta name="theme-color" content="#f3f4f4" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#181d1c" media="(prefers-color-scheme: dark)"><title>Тише — сводка за {date_label} {day.year}</title><meta name="description" content="Короткая сводка важных событий России и мира. Факты, контекст и ссылки на источники. Без рекламы и кликбейта."><link rel="icon" href="./favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="./style.css"></head>
<body><a class="skip" href="#news">К новостям</a>
<header class="masthead"><div class="identity"><span class="brand">тише.</span><span class="tagline">Важное, без шума</span></div><span class="cadence"><span aria-hidden="true"></span>Раз в день</span></header>
<main class="page" id="news"><div class="edition"><div><p class="overline">Сводка за день · {day.year}</p><h1>{date_label}<span>.</span></h1></div><div class="edition-meta"><span class="reading">{count} событий · около {duration} мин</span><p>Россия и мир</p></div></div>
<p class="freshness" id="freshness" hidden>Это выпуск за {date_label} {day.year}. Новая сводка пока не опубликована.</p>
<div class="columns">{''.join(cols)}</div>
<section class="ending" aria-label="Конец выпуска"><span class="end-mark" aria-hidden="true">✓</span><h2>На сегодня всё.</h2><p>Следующая сводка — завтра.<br>А пока можно вернуться к своим делам.</p></section>
<footer class="footer"><p>Отбираем события, которые меняют жизнь людей, правила или картину мира. Краткие сводки подготовлены с помощью ИИ по указанным источникам. Заявления и прогнозы отделяем от установленных фактов.</p><div class="colophon"><strong>тише.</strong>Без рекламы и счётчиков</div></footer></main>
<script>const published = Date.parse({json.dumps(data['updated_at'])}); if (Date.now() - published > 36 * 60 * 60 * 1000) {{ document.getElementById('freshness').hidden = false; document.querySelector('.ending p').textContent = 'Дата этого выпуска указана вверху. Следующая сводка пока не опубликована.'; }}</script>
</body></html>'''

if __name__ == '__main__':
    data = json.loads((ROOT / 'digest.json').read_text())
    html = render(data)
    (ROOT / 'index.html').write_text(html, encoding='utf-8')
    print(f'Rendered {sum(len(s["items"]) for s in data["sections"])} stories; {len(html.encode())} bytes')
