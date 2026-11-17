"""A sajtószemle automatizmusának parancssori indítója."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from datetime import datetime,timedelta
from .core import (BUDAPEST,read_sources,load_state,save_state,collect,
                   preflight,now_iso,parse_date,in_window,time_window)
from .ai import draft
from .pdf import build_pdf
from . import drive


def edition_date():
    here=datetime.now(BUDAPEST)
    return (here.date()+timedelta(days=1)).isoformat() if here.hour>=7 else here.date().isoformat()


def main(argv=None):
    ap=argparse.ArgumentParser(description='Napi sajtószemle B, minőségbiztosított kutató- és PDF-folyamat')
    ap.add_argument('--phase',choices=('collect','publish','smoke'),default='collect')
    ap.add_argument('--issue-date',default=None)
    ap.add_argument('--state',default='data/state.json')
    ap.add_argument('--sources',default='config/sources.json')
    ap.add_argument('--out',default='output')
    ap.add_argument('--per-source',type=int,default=10)
    ap.add_argument('--ai-limit',type=int,default=20)
    args=ap.parse_args(argv)
    issue=args.issue_date or edition_date()
    path=Path(args.state)
    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    log={'edition':issue,'phase':args.phase,'started':now_iso(),'events':[]}
    try:
        if args.phase=='smoke':
            report={'ready':False,'issues':['Próbafutás: nincs ellenőrzött forrás és EPG.'],
                    'groups_checked':[],'approved_stories':0,'verified_epg':0,'verified_channels':0}
            result=build_pdf(out/'PRÓBA_NEM_PUBLIKÁLHATÓ.pdf',issue,
                             [{'title':'Próbahír, nem valódi esemény','source':'Teszt','url':'https://example.com',
                               'summary':'Ez kizárólag a PDF-tördelés és az ékezetek ellenőrzésére szolgáló fiktív tesztszöveg.'}],
                             report,diagnostic=True)
            log['events'].append(result)
        else:
            try:
                log['events'].append(drive.pull(path))
            except Exception as exc:
                log['events'].append(f'Drive állapotletöltés hiba: {type(exc).__name__}: {str(exc)[:120]}')
            state=load_state(path)
            sources=read_sources(Path(args.sources))
            collection=collect(sources,state,issue,per_source=args.per_source)
            log['collection']=collection
            log['events'].append('A lekérdezés csak hírjelölteket állít elő, nem teljes forráslefedettségi igazolás.')
            if args.phase=='publish':
                log['ai']=draft(state,limit=args.ai_limit)
            report=preflight(state,issue)
            log['preflight']=report
            if args.phase=='publish':
                start,end=time_window(issue)
                stories=[v for v in state['stories'].values() if in_window(v.get('published'),start,end)]
                stories.sort(key=lambda x:x.get('published') or '',reverse=True)
                if report['ready']:
                    stories=[x for x in stories if x.get('approved') is True and x.get('summary')]
                    pdf=out/f'Teljes_berlini_es_kozlekedesi_sajtoszemle_{issue}_GitHub.pdf'
                    res=build_pdf(pdf,issue,stories,report,diagnostic=False)
                    log['pdf']=res
                    try:
                        log['drive_pdf']=drive.upload_pdf(pdf)
                    except Exception as exc:
                        log['events'].append(f'Végleges PDF elkészült, de Drive nem sikerült: {type(exc).__name__}: {exc}')
                else:
                    # Csak diagnosztika: ezt a fájlt tilos véglegesként feltölteni.
                    pdf=out/f'DIAGNOSZTIKA_{issue}_NEM_PUBLIKALHATO.pdf'
                    log['pdf']=build_pdf(pdf,issue,stories[:60],report,diagnostic=True)
            state['runs'].append({'time':now_iso(),'issue':issue,'phase':args.phase,'preflight':report})
            state['runs']=state['runs'][-500:]
            save_state(path,state)
            try:
                log['events'].append(drive.push_state(path))
            except Exception as exc:
                log['events'].append(f'Drive állapotmentés hiba: {type(exc).__name__}: {str(exc)[:120]}')
        log['finished']=now_iso()
        (out/'run-report.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'edition':issue,'phase':args.phase,'report':log.get('preflight'),
                          'pdf':log.get('pdf'),'events':log['events'][-5:]},ensure_ascii=False,indent=2))
    except Exception as exc:
        log['fatal_error']=f'{type(exc).__name__}: {str(exc)[:500]}'
        (out/'run-report.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
        raise

if __name__=='__main__':main()