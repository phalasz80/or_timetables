"""Forrásalapú magyar hírvázlat; bizonyíték nélküli állítás nem kerül kiadásba."""
from __future__ import annotations
import json
import os
from .core import approve_evidence

GUIDANCE = """Magyar nyelvű vasúti és közéleti szerkesztőségi segéd vagy.
A kapott forrásszövegből készíts megfontolt, tárgyszerű, 80–180 szavas hírvázlatot.
Kizárólag a kapott szövegben bizonyított állításokat írd le. Ne tételezz fel dátumot,
árat, járműtípust, utashatást vagy szervezeti státuszt. Különítsd el a tervezetet,
a közleményt és a megvalósult állapotot. A kapott cikk egyetlen forrás, ezért a
feldolgozás maradjon tervezet. Válaszolj CSAK JSON-ként, pontosan e két kulccsal:
{"summary": "magyar nyelvű szöveg", "source_evidence": "a forrásból szó szerint 20–180 karakteres, valódi ellenőrző részlet"}
"""


def draft(state:dict, limit:int=12) -> dict:
    if not os.environ.get('OPENAI_API_KEY'):
        return {'drafted':0,'error':'OPENAI_API_KEY hiányzik'}
    from openai import OpenAI
    client=OpenAI(api_key=os.environ['OPENAI_API_KEY'], timeout=50.0, max_retries=2)
    count=0
    errors=[]
    for item in state['stories'].values():
        if item.get('summary') or item.get('body_length',0)<180:
            continue
        prompt=json.dumps({'title':item['title'],'source_url':item['url'],
                           'published':item.get('published'),'source_text':item['body'][:9500]},ensure_ascii=False)
        try:
            r=client.responses.create(model=os.getenv('OPENAI_MODEL','gpt-4.1-mini'),instructions=GUIDANCE,
                                      input=prompt, max_output_tokens=650)
            raw=r.output_text.strip()
            if raw.startswith('```'):
                raw=raw.strip('`').removeprefix('json').strip()
            data=json.loads(raw)
            if approve_evidence(item,data.get('source_evidence',''),data.get('summary','')):
                count+=1
            else:
                errors.append(f"Nem igazolható idézet: {item['url']}")
        except Exception as exc:
            errors.append(f"{item['url']}: {type(exc).__name__}: {str(exc)[:100]}")
        if count>=limit: break
    return {'drafted':count,'errors':errors[:30],
            'note':'Az AI-vázlatokat még nem hagyta jóvá szerkesztő; nem publikálhatóak véglegesként.'}