"""Újságszerű, Unicode-biztos diagnosztikai PDF, és jóváhagyott anyag PDF-je.
ReportLab Bookmarks, kattintható tartalomjegyzék, oldalszámok, kattintható források.
"""
from __future__ import annotations
import html
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.platypus.tableofcontents import TableOfContents

FONT_CANDIDATES=[
  ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
  ('/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf'),
]

def prepare_fonts():
    for regular,bold in FONT_CANDIDATES:
        if Path(regular).is_file() and Path(bold).is_file():
            pdfmetrics.registerFont(TTFont('Szemle',regular))
            pdfmetrics.registerFont(TTFont('Szemle-Bold',bold))
            pdfmetrics.registerFontFamily('Szemle',normal='Szemle',bold='Szemle-Bold')
            return
    raise RuntimeError('Hiányzó magyar ékezetes TTF betűtípus')

class SzemleDoc(BaseDocTemplate):
    def __init__(self,filename,issue_date,**kwargs):
        self.issue_date=issue_date
        self.counter=0
        super().__init__(filename,pagesize=A4,leftMargin=21*mm,rightMargin=19*mm,
                         topMargin=22*mm,bottomMargin=21*mm,**kwargs)
        frame=Frame(self.leftMargin,self.bottomMargin,self.width,self.height,id='main',showBoundary=0)
        self.addPageTemplates(PageTemplate(id='standard',frames=[frame],onPage=self._footer))
    def beforeDocument(self):
        self.counter=0  # stabil bookmark-azonosítók minden TOC-generálási körben

    def _footer(self,canv,doc):
        canv.saveState()
        canv.setStrokeColor(colors.HexColor('#C8CFDA'))
        canv.line(21*mm,18*mm,190*mm,18*mm)
        canv.setFont('Szemle',7)
        canv.drawString(21*mm,14*mm,f'TELJES BERLINI ÉS KÖZLEKEDÉSI SAJTÓSZEMLE  |  {self.issue_date}')
        canv.drawRightString(190*mm,14*mm,f'{doc.page}. oldal')
        canv.restoreState()
    def afterFlowable(self,flowable):
        if getattr(flowable,'_heading_level',None) is not None:
            self.counter+=1
            key='section-%d' % self.counter
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(flowable.getPlainText(),key,flowable._heading_level,False)
            self.notify('TOCEntry',(flowable._heading_level,flowable.getPlainText(),self.page,key))


def esc(s):return html.escape(str(s),quote=True)

def build_pdf(path:Path,issue_date:str,stories:list[dict],report:dict,*,diagnostic:bool):
    prepare_fonts()
    path.parent.mkdir(parents=True,exist_ok=True)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='MainTitleU',fontName='Szemle-Bold',fontSize=22,leading=29,spaceAfter=16,textColor=colors.HexColor('#162B44')))
    styles.add(ParagraphStyle(name='SubU',fontName='Szemle',fontSize=11,leading=16,spaceAfter=15))
    styles.add(ParagraphStyle(name='SectionU',fontName='Szemle-Bold',fontSize=14,leading=19,spaceBefore=16,spaceAfter=9,keepWithNext=True))
    styles.add(ParagraphStyle(name='NewsU',fontName='Szemle-Bold',fontSize=11,leading=15,spaceBefore=13,spaceAfter=5,keepWithNext=True))
    styles.add(ParagraphStyle(name='BodyU',fontName='Szemle',fontSize=9,leading=14,spaceAfter=9,alignment=TA_LEFT))
    styles.add(ParagraphStyle(name='LinkU',fontName='Szemle',fontSize=8,leading=11,textColor=colors.HexColor('#265F9B'),spaceAfter=11,wordWrap='CJK'))
    doc=SzemleDoc(str(path),issue_date)
    flow=[Spacer(1,25*mm),Paragraph('TELJES BERLINI ÉS<br/>KÖZLEKEDÉSI SAJTÓSZEMLE',styles['MainTitleU']),
          Paragraph(esc(issue_date),styles['SubU'])]
    if diagnostic:
        flow.append(Paragraph('<b>DIAGNOSZTIKAI PÉLDÁNY - NEM PUBLIKÁLHATÓ VÉGLEGES KIADÁSKÉNT</b>',styles['BodyU']))
    else:
        flow.append(Paragraph('<b>FORRÁSOKKAL ELLENŐRZÖTT ÉS ÁTVETT KIADÁS</b>',styles['BodyU']))
    flow.append(Paragraph('Hírablak: előző nap 07:00-tól a tárgynap 06:40-ig (Europe/Budapest). A 06:40–07:00 között megjelent közlemények a következő frissítési körbe kerülnek.',styles['BodyU']))
    for story in stories[:4]:
        flow.append(Paragraph(esc(story['title']),styles['NewsU']))
        flow.append(Paragraph(esc((story.get('summary') or story.get('body',''))[:390]),styles['BodyU']))
    flow+=[PageBreak(),Paragraph('Tartalomjegyzék',styles['SectionU'])]
    toc=TableOfContents()
    toc.levelStyles=[ParagraphStyle(name='toc0',fontName='Szemle',fontSize=9,leading=15,leftIndent=8,firstLineIndent=-8)]
    flow.extend([toc,PageBreak()])
    p=Paragraph('Forrásellenőrzés és szerkesztői átvétel',styles['SectionU']);p._heading_level=0;flow.append(p)
    flow.append(Paragraph('Automatikus kiadási kapu: <b>'+('TELJESÜLT' if report['ready'] else 'NEM TELJESÜLT')+'</b>.',styles['BodyU']))
    for err in report['issues']:
        flow.append(Paragraph('• '+esc(err),styles['BodyU']))
    flow.append(Paragraph(f"Ellenőrzött csoportok: {', '.join(report['groups_checked']) or 'nincs'}. Jóváhagyott hírek: {report['approved_stories']}. Igazolt EPG: {report['verified_epg']} tétel / {report['verified_channels']} csatorna.",styles['BodyU']))
    p=Paragraph('Hírek és hírjelöltek',styles['SectionU']);p._heading_level=0;flow.append(p)
    for story in stories:
        flow.append(Paragraph(esc(story['title'] or '(Cím nélkül)'),styles['NewsU']))
        flow.append(Paragraph(esc(story.get('summary') or 'Az ellenőrzött, szerkesztett hír még hiányzik.'),styles['BodyU']))
        flow.append(Paragraph(esc(story.get('published') or 'Közlési dátum nem igazolt')+' | '+esc(story.get('source','')),styles['BodyU']))
        src=story.get('url','')
        if src.startswith('https://') or src.startswith('http://'):
            flow.append(Paragraph(f'<link href="{esc(src)}">FORRÁS: {esc(src[:110])}</link>',styles['LinkU']))
    doc.multiBuild(flow,maxPasses=4)
    from pypdf import PdfReader
    reader=PdfReader(str(path))
    assert len(reader.pages)>=2 and len(reader.outline)>0
    return {'path':str(path),'pages':len(reader.pages),'bytes':path.stat().st_size}