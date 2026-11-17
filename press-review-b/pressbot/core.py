"""Forrásgyűjtés és ellenőrizhető állapotkezelés. Nincs automatikus tényállítás."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode
from zoneinfo import ZoneInfo
import html
import json
import os
import re

BUDAPEST = ZoneInfo('Europe/Budapest')
GROUPS = tuple('ABCDEFGHIJKLM')
USER_AGENT = 'NapiSajtoszemleResearchBot/0.1 (news research; contact repository owner)'


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def normalize_url(url: str) -> str:
    """Tracking parameters removed; only public http(s) URLs accepted."""
    u = urlparse(url.strip())
    if u.scheme not in ('https', 'http') or not u.hostname:
        raise ValueError('Nem HTTP(S) URL')
    if u.username or u.password or u.port and u.port not in (80, 443):
        raise ValueError('Tiltott URL összetevő')
    if u.hostname.lower() in ('localhost', '127.0.0.1', '0.0.0.0') or u.hostname.endswith('.local'):
        raise ValueError('Nem nyilvános cím')
    params = [(k, v) for k, v in parse_qsl(u.query) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid','gclid')]
    return urlunparse((u.scheme.lower(), u.netloc.lower(), u.path.rstrip('/') or '/', '', urlencode(params), ''))


def time_window(issue_date: str) -> tuple[datetime, datetime]:
    day = datetime.fromisoformat(issue_date).date()
    return (datetime.combine(day-timedelta(days=1), time(7), BUDAPEST),
            datetime.combine(day, time(6, 40), BUDAPEST))


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    from dateutil import parser
    try:
        dt = parser.parse(value)
        if not dt.tzinfo:
            return None  # nincs bizonyított időzóna
        return dt.astimezone(BUDAPEST)
    except (ValueError, OverflowError, TypeError):
        return None


def in_window(published: str | None, start: datetime, end: datetime) -> bool:
    dt = parse_date(published)
    return bool(dt and start <= dt <= end)


def new_state() -> dict:
    return {'schema': 1, 'stories': {}, 'visits': [], 'epg': [], 'runs': [], 'approvals': []}


def load_state(path: Path) -> dict:
    if not path.is_file():
        return new_state()
    doc = json.loads(path.read_text(encoding='utf-8'))
    if doc.get('schema') != 1:
        raise RuntimeError('Ismeretlen adatbázis-verzió')
    for key, default in new_state().items():
        doc.setdefault(key, default)
    return doc


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True), encoding='utf-8')
    temp.replace(path)


def read_sources(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding='utf-8'))
    entries = data.get('sources', [])
    keys=set()
    for e in entries:
        if e['group'] not in GROUPS:
            raise ValueError(f"Ismeretlen csoport: {e['group']}")
        e['url'] = normalize_url(e['url'])
        if e['id'] in keys:
            raise ValueError(f"Duplikált forrásazonosító: {e['id']}")
        keys.add(e['id'])
    return entries


def _published_of(tag, feed_published=None):
    if feed_published:
        dt = parse_date(feed_published)
        return dt.isoformat() if dt else None
    for selector in ('meta[property="article:published_time"]', 'meta[name="date"]',
                     'meta[name="pubdate"]', 'meta[itemprop="datePublished"]',
                     'time[datetime]'):
        el=tag.select_one(selector)
        if el:
            dt=parse_date(el.get('content') or el.get('datetime'))
            if dt:
                return dt.isoformat()
    return None


def _read_article(session, url: str, group: str, source: str) -> dict:
    from bs4 import BeautifulSoup
    response=session.get(url,timeout=18,headers={'User-Agent':USER_AGENT})
    response.raise_for_status()
    if 'text/html' not in response.headers.get('content-type','text/html'):
        raise ValueError('Nem HTML cikk')
    soup=BeautifulSoup(response.text[:1_500_000], 'html.parser')
    published=_published_of(soup)
    title=soup.select_one('h1') or soup.select_one('meta[property="og:title"]') or soup.title
    title=(title.get('content') or title.get_text(' ',strip=True)) if title else ''
    for node in soup.select('script,style,nav,footer,aside,form,header'):
        node.decompose()
    main=soup.select_one('article') or soup.select_one('main') or soup.body
    content=main.get_text(' ',strip=True) if main else ''
    content=re.sub(r'\s+', ' ', content)
    return {'url':normalize_url(response.url),'group':group,'source':source,'title':html.unescape(title[:350]),
            'published':published,'body':content[:14000], 'body_length':len(content),
            'checked_at':now_iso(),'stage':'candidate','approved':False}


def collect_one(source: dict, start: datetime, end: datetime, per_source=15) -> tuple[list[dict], dict]:
    import xml.etree.ElementTree as ET
    import requests
    from bs4 import BeautifulSoup
    url=source['url']
    name=source['name']
    result=[]
    visit={'source_id':source['id'],'group':source['group'],'url':url,'time':now_iso(),
           'status':'error','count':0,'note':''}
    session=requests.Session()
    try:
        resp=session.get(url,headers={'User-Agent':USER_AGENT,'Accept':'text/html, application/rss+xml, application/atom+xml'},timeout=20)
        resp.raise_for_status()
        ct=resp.headers.get('content-type','').lower()
        is_feed=('xml' in ct or 'rss' in ct or source.get('type')=='rss')
        proposals=[]
        if is_feed:
            root=ET.fromstring(resp.content)
            for node in list(root.findall('.//item'))+list(root.findall('.//{http://www.w3.org/2005/Atom}entry')):
                href=(node.findtext('link') or '').strip()
                if not href:
                    atom=node.find('{http://www.w3.org/2005/Atom}link')
                    href=(atom.get('href') or '').strip() if atom is not None else ''
                d=(node.findtext('pubDate') or node.findtext('{http://www.w3.org/2005/Atom}published')
                   or node.findtext('{http://www.w3.org/2005/Atom}updated'))
                parsed=parse_date(d)
                if href and parsed and in_window(parsed.isoformat(),start,end):
                    proposals.append(href)
        else:
            soup=BeautifulSoup(resp.text[:1_500_000], 'html.parser')
            targets=soup.select('article a[href], main a[href], h2 a[href], h3 a[href]')
            origin=urlparse(url).hostname
            for a in targets:
                candidate=urljoin(resp.url,a.get('href',''))
                try:
                    clean=normalize_url(candidate)
                    host=urlparse(clean).hostname
                    if not (host == origin or host.endswith('.'+origin)):
                        continue
                    if clean==url or clean in proposals or len(a.get_text(' ',strip=True))<12:
                        continue
                    proposals.append(clean)
                except (ValueError, AttributeError):
                    continue
        for href in proposals[:per_source]:
            try:
                item=_read_article(session,href,source['group'],name)
                if (in_window(item.get('published'),start,end)
                        and item['body_length']>=180):
                    result.append(item)
            except (ValueError,requests.RequestException):
                continue
        visit.update(status='visited',count=len(result),note=(
            'A forrásoldalt lekérdeztük; a teljes rovat-lefedettség nincs igazolva. '
            'Ismeretlen publikálási idejű tételek kizárva.'))
    except Exception as exc:
        visit['note']=f'{type(exc).__name__}: {str(exc)[:180]}'
    return result,visit


def collect(sources: list[dict], state: dict, issue_date: str, per_source=10) -> dict:
    start,end=time_window(issue_date)
    summary={'date':issue_date,'sources_attempted':0,'sources_visited':0,'new_candidates':0,'errors':[]}
    for source in sources:
        items,visit=collect_one(source,start,end,per_source)
        state['visits'].append(visit)
        summary['sources_attempted']+=1
        if visit['status']=='visited': summary['sources_visited']+=1
        else: summary['errors'].append(f"{source['name']}: {visit['note']}")
        for item in items:
            url=item['url']
            old=state['stories'].get(url)
            if old:
                old['checked_at']=item['checked_at']
                continue
            state['stories'][url]=item
            summary['new_candidates']+=1
    state['visits']=state['visits'][-10000:]
    return summary


def preflight(state: dict, issue_date: str, min_stories=60, min_epg=250) -> dict:
    start,end=time_window(issue_date)
    visits={v.get('group') for v in state['visits'] if v.get('status')=='visited' and
            in_window(v.get('time'),start,end)}
    ready=[s for s in state['stories'].values() if s.get('approved') is True and
           s.get('summary') and in_window(s.get('published'),start,end)]
    epg=[e for e in state.get('epg',[]) if e.get('day')==issue_date and e.get('verified') is True]
    chans={e.get('channel') for e in epg}
    issues=[]
    if visits!=set(GROUPS):issues.append('Nem ellenőrzött csoportok: '+', '.join(sorted(set(GROUPS)-visits)))
    if len(ready)<min_stories:issues.append(f'Ellenőrzött hírek: {len(ready)}/{min_stories}')
    if len(epg)<min_epg:issues.append(f'Igazolt EPG-tételek: {len(epg)}/{min_epg}')
    if len(chans)<14:issues.append(f'Igazolt tévécsatornák: {len(chans)}/14')
    if any(not s.get('source_evidence') for s in ready):
        issues.append('Legalább egy késznek jelölt cikkből hiányzik a forrásbizonyíték')
    return {'issue_date':issue_date,'ready':not issues,'issues':issues,
            'groups_checked':sorted(visits),'approved_stories':len(ready),
            'verified_epg':len(epg),'verified_channels':len(chans)}


def approve_evidence(story: dict, evidence: str, summary: str, *, rule='evidence') -> bool:
    """Bizonyíték-szövegnek ténylegesen szerepelnie kell a letöltött forrásban.
    Ez nem helyettesíti az emberi ellenőrzést: önmagában nem állít approved=True-t.
    """
    normalized=lambda s: re.sub(r'\s+',' ',s).strip().casefold()
    if len(evidence)<20 or normalized(evidence) not in normalized(story.get('body','')):
        return False
    if len(summary)<25 or len(summary)>2000:
        return False
    story['source_evidence']=evidence
    story['summary']=summary
    story['stage']='draft_with_evidence'
    return True