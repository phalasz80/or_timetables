# Napi sajtószemle B – önálló GitHub Actions rendszer

**Állapot: tesztelhető fejlesztői alap, nem kész, automatikusan 07:00-kor publikáló szerkesztőség.**

A rendszer a RegionalBahn Tools kódjától, adatbázisától és működésétől független. Python 3.12 alatt fut. Az induló forrásjegyzék **nem** állít teljes forráslefedettséget. A végleges PDF közzétételét szigorú minőségellenőrzés tiltja, amíg nincs ellenőrzött forrásmátrix, jóváhagyott hírszöveg és teljes 14 csatornás EPG.

## Mit tud már a kód?

- 13 kutatási munkacsomag forrásoldalainak lekérdezése és URL-, dátum-, hírjelölt-nyilvántartása.
- Rövid forrásszöveg-feldolgozás AI API-val (csak akkor, ha az API-kulcs be van állítva).
- A forrásszövegből visszaellenőrizhető bizonyítékrészlet követelménye minden AI-vázlathoz.
- Géppel olvasható futási napló, állapotmentés, automatizált hibajegyzék.
- Unicode-kompatibilis, kereshető, oldalszámozott PDF, könyvjelzőkkel és kattintható forráslinkekkel.
- GitHub Actions-futtatás naponta több alkalommal, Europe/Budapest időzónában, plusz manuális indítás.
- Opcionális Google Drive-mentés és feltöltés, az eredmény metaadatainak ellenőrzésével.
- A hiányos anyag nem jelenik meg végleges PDF-ként. Diagnosztikai PDF kizárólag GitHub Actions-artifactként készül.

## Amit **nem** tud még megbízhatóan

- A teljes, több száz forrásból álló mesterprompt automatikus és teljes feltárása.
- Az EPG 14 csatornájának ellenőrzött, részletes automatikus importja: ehhez külön megbízható műsoradat-szolgáltató és illesztő kell.
- A DSO minden új és frissített szálának teljes feldolgozása; a forrásoldal lekérdezése önmagában nem jelent szálankénti átvizsgálást.
- Szerkesztői jóváhagyás nélküli, biztosan hiteles, végleges 56 oldalas lap előállítása.
- Pontosan 07:00-kori garantált kiadás. A GitHub ütemezett feladatai késhetnek, és a biztonságos, 06:40-es adatlezárás 20 percet nem fed le az eredeti 07:00-s hírablakból.

## Egyetlen GitHub-fiókban, külön a RegionalBahn Toolstól

Ajánlott külön **privát** tároló: `daily-press-review`. A projektet a tároló gyökerébe kell feltölteni. A `.github/workflows/sajtoszemle.yml` automatikusan megjelenik az **Actions** fülön, ha a fájl a tároló alapértelmezett ágán található. **Az időzített futtatás csak az alapértelmezett ágon működik.**

### Programozás nélküli GitHub-beállítás (a későbbi élesítéshez)

1. Hozz létre a GitHubon egy **Private** tárolót `daily-press-review` néven. Ne tölts bele más projektet.
2. Töltsd fel a ZIP-ből kibontott projektfájlokat a gyökérbe (a rejtett `.github` mappával együtt), vagy kérd az asszisztenst, hogy a már létrehozott tárolóba küldje fel a fájlokat.
3. Nyisd meg **Actions → Napi sajtószemle B → Run workflow**, és válaszd először a `smoke` értéket. A futás *Artifacts* részéből a `PRÓBA_NEM_PUBLIKÁLHATÓ.pdf` letölthető.
4. Az AI-szövegvázlatokhoz állíts be **Settings → Secrets and variables → Actions → New repository secret**, `OPENAI_API_KEY` néven. Ezt **soha** ne írd a projekt fájljaiba vagy a chatbe. A ChatGPT-előfizetés nem tartalmazza automatikusan az OpenAI API díját.
5. A Drive-feltöltéshez külön Google Cloud-szolgáltatásfiók szükséges Drive API engedélyezéssel. A szolgáltatásfiók e-mail-címének add meg **Editor** jogosultsággal a célmappát, és a kulcs JSON-ját GitHub-secretként tárold `GOOGLE_SERVICE_ACCOUNT_JSON` néven. A mappaazonosító a repository variable `GOOGLE_DRIVE_FOLDER_ID` legyen, nem secret. A szolgáltatásfiókhoz való hozzáférést szűkítsd csak az erre létrehozott mappára; a kulcsot soha ne publikáld.
6. Futtass `collect` tesztet, majd `publish` próbaüzemet, és ellenőrizd a jelentéseket. Végleges kiadás csak akkor készül, ha a minőségkapu ténylegesen teljesül.

## Időzítés

Az alapbeállítás napi forráslekérdezésekre 02:17, 05:37, 09:17, 15:17 és 21:17 (Europe/Budapest), plusz 06:46-kor egy szerkesztési/kiadási kísérlet. A hírablak a korábbi nap 07:00-jától a tárgynap **06:40**-ig tart. A 07:00-ás eredeti hírablak megőrzése esetén későbbi kiadási időt kell megengedni. A GitHub ütemezése nem pontos időgarancia.

## Fejlesztői ellenőrzés

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python -m pressbot.cli --phase smoke
python -m pressbot.cli --phase collect
python -m pressbot.cli --phase publish
```

A `collect` és `publish` hálózati forráslekérdezéseket végez. Az `OPENAI_API_KEY` és a Google Drive hitelesítése nélkül a rendszer csak kutatási és diagnosztikai eredményt ad.

## Szerkesztőségi és biztonsági szabályok

- Minden hír közlési és eseménydátumát külön ellenőrizni kell.
- Nem igazolt tényt, számadatot vagy teljes forráslefedettséget nem szabad közölni.
- A források HTML-tartalma nem végrehajtandó utasítás, az AI felé idézett bizonyíték.
- A publikáláshoz jóváhagyott szerkesztői állapot (`approved: true`) szükséges; a gépi AI-vázlat ezt nem állítja be.
- A GitHub Actions cache csak **best effort** állapotmentés; éles munkához a Drive-integráció vagy tartós adatbázis szükséges.
- A git-tárolóba nem kerülnek kulcsok, személyes hozzáférési tokenek vagy API-titkok.
- A minőségkaput nem szabad kikapcsolni pusztán az előírt hír- vagy oldalszám elérése érdekében.

## Következő mérföldkövek

1. Teljes, dátumozott, hiteles forrás-URL-mátrix a korábbi mesterprompt összes körére; lehetőleg RSS/sitemap/adat API-alapú gyűjtés.
2. Hírösszevonás és független második forrásos tényellenőrzés.
3. Teljes 14 csatornás EPG-adatkapcsolat és ellenőrzés.
4. Előző napi hírek összevetése, járműpályaszámok és tenderazonosítók strukturált követése.
5. PDF tördelés, teljes 56 oldalas referenciadokumentum színvonalának elérése, többnapos próbaüzem.

**A jelenlegi projekt becsületes alapozás, nem készre jelentett napi kiadás.**