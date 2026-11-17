"""Csak konfigurációt állít elő; forráslátogatást vagy ellenőrzést nem állít."""
import json
from pathlib import Path
S={
'A':[
 ('rbb24','https://www.rbb24.de/'),('Berlin Szenátus','https://www.berlin.de/sen/'),
 ('Brandenburg kormánya','https://www.brandenburg.de/'),('Tagesspiegel Berlin','https://www.tagesspiegel.de/berlin/'),
 ('Berliner Morgenpost','https://www.morgenpost.de/berlin/'),('Berliner Zeitung','https://www.berliner-zeitung.de/berlin')],
'B':[
 ('BVG','https://www.bvg.de/'),('S-Bahn Berlin','https://sbahn.berlin/'),('VBB','https://www.vbb.de/'),
 ('NEB','https://www.neb.de/'),('ODEG','https://www.odeg.de/'),('Barnimer Busgesellschaft','https://www.bbg-eberswalde.de/'),
 ('Strausberger Eisenbahn','https://www.strausberger-eisenbahn.de/'),('IGEB','https://www.igeb.org/'),
 ('Schöneiche–Rüdersdorf','https://www.srs-tram.de/'),('Woltersdorfer Straßenbahn','https://www.woltersdorfer-strassenbahn.com/')],
'C':[
 ('Bundesregierung','https://www.bundesregierung.de/'),('Bundestag','https://www.bundestag.de/'),
 ('Bundesrat','https://www.bundesrat.de/'),('tagesschau','https://www.tagesschau.de/'),
 ('Deutschlandfunk','https://www.deutschlandfunk.de/')],
'D':[
 ('Deutsche Bahn Presse','https://www.deutschebahn.com/de/presse/'),('DB InfraGO','https://www.dbinfrago.com/'),
 ('Hamburger Hochbahn','https://www.hochbahn.de/'),('MVG München','https://www.mvg.de/'),
 ('SSB Stuttgart','https://www.ssb-ag.de/'),('KVB Köln','https://www.kvb.koeln/'),
 ('Rheinbahn Düsseldorf','https://www.rheinbahn.de/'),('VGF Frankfurt','https://www.vgf-ffm.de/'),
 ('DVB Dresden','https://www.dvb.de/'),('LVB Leipzig','https://www.l.de/verkehrsbetriebe/'),
 ('WSW Wuppertal','https://www.wsw-online.de/')],
'E':[
 ('MÁV csoport','https://www.mavcsoport.hu/'),('BKK','https://bkk.hu/'),('BKV','https://www.bkv.hu/'),
 ('Főváros','https://budapest.hu/'),('Zugló','https://www.zuglo.hu/'),('Rákosmente','https://www.rakosmente.hu/'),
 ('Országgyűlés','https://www.parlament.hu/'),('Magyar Közlöny','https://magyarkozlony.hu/')],
'F':[
 ('TfL','https://tfl.gov.uk/'),('London City Hall','https://www.london.gov.uk/'),
 ('Network Rail','https://www.networkrail.co.uk/'),('National Rail','https://www.nationalrail.co.uk/'),
 ('Manchester Metrolink','https://tfgm.com/'),('West Midlands Metro','https://westmidlandsmetro.com/'),
 ('Edinburgh Trams','https://edinburghtrams.com/'),('Nexus Tyne and Wear','https://www.nexus.org.uk/')],
'G':[
 ('ORF','https://orf.at/'),('Österreich Bundesregierung','https://www.bundeskanzleramt.gv.at/'),
 ('Österreich Parlament','https://www.parlament.gv.at/'),('Schweizer Bundesrat','https://www.admin.ch/gov/de/start.html'),
 ('SRF','https://www.srf.ch/news'),('SWI swissinfo','https://www.swissinfo.ch/ger/')],
'H':[
 ('ÖBB','https://www.oebb.at/'),('ÖBB Presse','https://presse.oebb.at/'),
 ('Wiener Linien','https://www.wienerlinien.at/'),('SBB','https://www.sbb.ch/'),
 ('BLS','https://www.bls.ch/'),('RhB','https://www.rhb.ch/')],
'I':[
 ('ČD','https://www.cd.cz/'),('Správa železnic','https://www.spravazeleznic.cz/'),
 ('ZSSK','https://www.zssk.sk/'),('ŽSR','https://www.zsr.sk/'),
 ('HŽPP','https://www.hzpp.hr/'),('Slovenske železnice','https://potniski.sz.si/'),
 ('Srbija Voz','https://srbijavoz.rs/')],
'J':[
 ('Stadler','https://www.stadlerrail.com/'),('Siemens Mobility','https://www.mobility.siemens.com/'),
 ('Alstom','https://www.alstom.com/'),('Škoda Group','https://www.skodagroup.com/'),
 ('CAF','https://www.cafmobility.com/'),('PESA','https://pesa.pl/'),('Newag','https://www.newag.pl/'),
 ('Hitachi Rail','https://www.hitachirail.com/'),('Talgo','https://www.talgo.com/'),
 ('DB Gebrauchtzug','https://www.db-gebrauchtzug.de/')],
'K':[
 ('Drehscheibe Online','https://www.drehscheibe-online.de/'),('IGEB SIGNAL','https://signalarchiv.de/'),
 ('Eisenbahn-Kurier','https://www.eisenbahn-kurier.de/'),('Eisenbahn-Romantik','https://www.swrfernsehen.de/eisenbahn-romantik/')],
'L':[
 ('EU TED tenders','https://ted.europa.eu/'),('Magyar EKR','https://ekr.gov.hu/'),
 ('VBB menetrend','https://www.vbb.de/'),('ÖBB menetrend','https://www.oebb.at/'),
 ('SBB menetrend','https://www.sbb.ch/')],
'M':[
 ('ARD műsorrend','https://www.daserste.de/programm/'),('ZDF műsorrend','https://www.zdf.de/programm'),
 ('ARD műsor áttekintés','https://programm.ard.de/')]
}
result=[]
for group,values in S.items():
 for i,(name,url) in enumerate(values,1):
  result.append({'id':f'{group}-{i:03d}','group':group,'name':name,'url':url,'type':'html'})
obj={'about':'KIINDULÓ HONLAPLISTA. Nem teljes forrásmátrix, és nem minden cím automatikusan feldolgozható. A sikertelen oldalak naplózandók.',
     'sources':result}
Path(__file__).with_name('sources.json').write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(len(result))