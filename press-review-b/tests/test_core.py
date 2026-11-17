from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import pytest
from pressbot.core import (time_window,normalize_url,new_state,preflight,
                           approve_evidence,save_state,load_state,read_sources)
from pressbot.pdf import build_pdf
from pypdf import PdfReader


def test_time_window_uses_budapest():
    start,end=time_window('2026-11-18')
    assert (start.isoformat(),end.isoformat())==('2026-11-17T07:00:00+01:00','2026-11-18T06:40:00+01:00')


def test_url_dedup_and_security():
    assert normalize_url('https://EXAMPLE.com/news/?utm_source=x&x=y')=='https://example.com/news?x=y'
    with pytest.raises(ValueError):normalize_url('file:///etc/passwd')
    with pytest.raises(ValueError):normalize_url('https://localhost/admin')


def test_quality_gate_is_closed_by_default():
    s=new_state()
    r=preflight(s,'2026-11-18')
    assert r['ready'] is False
    assert 'A' not in r['groups_checked']
    assert r['verified_channels']==0


def test_unverified_quote_is_rejected():
    s={'body':'Közlemény: A vonat egyértelműen menetrend szerint közlekedett.'}
    assert not approve_evidence(s,'Nem szereplő következtetés, amit nem lehet bizonyítani.', 'Hosszabb hamis mondat, amely nem áll a forrásban.')
    assert approve_evidence(s,'A vonat egyértelműen menetrend szerint közlekedett.',
                            'A közlemény menetrend szerinti vonatközlekedést ír le.')
    assert s['stage']=='draft_with_evidence'
    assert not s.get('approved')


def test_state_roundtrip(tmp_path):
    p=tmp_path/'state.json'
    s=new_state();s['stories']['https://example.com']={'title':'Árvíztűrő tükörfúrógép'}
    save_state(p,s)
    assert load_state(p)==s


def test_sources_have_all_groups():
    sources=read_sources(Path('config/sources.json'))
    assert set('ABCDEFGHIJKLM')=={s['group'] for s in sources}
    assert len(sources)>=40


def test_pdf_smoke_unicode_and_outline(tmp_path):
    path=tmp_path/'test.pdf'
    report=preflight(new_state(),'2026-11-18')
    build_pdf(path,'2026-11-18',[{'title':'Berlini próbahír','summary':'Árvíztűrő tükörfúrógép, ő és ű, Ő és Ű.','url':'https://example.com/news',
              'published':'2026-11-17T12:00:00+01:00','source':'Teszt'}],report,diagnostic=True)
    r=PdfReader(str(path))
    assert len(r.pages)>=3
    text='\n'.join(p.extract_text() or '' for p in r.pages)
    assert 'Árvíztűrő tükörfúrógép' in text
    assert len(r.outline)>=2
    assert any('/URI' in a.get_object().get('/A',{}) for p in r.pages for a in (p.get('/Annots') or []))