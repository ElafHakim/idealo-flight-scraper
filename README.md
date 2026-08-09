# idealo-flight-scraper
Web scraping project for collecting flight data from Idealo using Scrapy and Playwright.

# Flight Scraper

Ein Python-Projekt zum automatisierten Crawlen und Speichern von Flugangeboten.

Der Scraper basiert auf **Scrapy** und **Playwright**. Flugrouten werden aus einer CSV-Datei eingelesen und die gefundenen Flugangebote anschließend verarbeitet und in einer **MongoDB-Datenbank** gespeichert.

Für die Verarbeitung einer größeren Anzahl von Flugrouten steht zusätzlich ein **Batch-Runner** zur Verfügung.

## Requirements

-Python 3.12
 -Docker
- Docker Compose

## Setup

Repository klonen:

```bash
git clone https://github.com/ElafHakim/idealo-flight-scraper
```

In das Scrapy-Projekt wechseln:

```bash
cd flight_scraper/flightscraper
```


Die benötigten Python-Pakete aus der `requirements.txt` installieren:

```bash
python -m pip install -r requirements.txt
```

Anschließend Chromium für Playwright installieren:

```bash
python -m playwright install chromium
```

## Hint to start MongoDB

MongoDB wird über Docker bereitgestellt.

```bash
docker compose up -d
```

Prüfen, ob der MongoDB-Container läuft:

```bash
docker ps
```

MongoDB ist anschließend über folgenden Port erreichbar:

```text
localhost:27017
```

Die MongoDB-Daten werden über ein Docker-Volume persistent gespeichert.

## Scraper starten

Um den Idealo-Spider direkt auszuführen:

```bash
python -m scrapy crawl idealo
```

Der Spider liest die konfigurierten Flugrouten ein, sendet die entsprechenden Anfragen und verarbeitet die gefundenen Flugangebote.

## Batch-Crawl starten

Für eine größere Anzahl an Flugrouten kann der Batch-Runner verwendet werden:

```bash
python scripts/batch_runner.py
```


Der Batch-Runner:

- teilt die Flugrouten in Batches auf,
- startet den Idealo-Spider für die jeweiligen Routen,
- überwacht den Crawl,
- erstellt Statusdateien,
- erstellt Logdateien,
- kann nicht abgeschlossene Batches erneut starten.

Die Status- und Logdateien landen in das Verzeichnis:

```text
batches/
```

## Laufende Python-Prozesse prüfen

Da der Batch-Runner Scrapy-Prozesse startet, können laufende Python-Prozesse unter Windows PowerShell mit folgendem Befehl geprüft werden:

```powershell
Get-Process python
```

Die Ausgabe enthält unter anderem die jeweilige Process-ID (`Id`).

## Python-Prozess beenden

Ein bestimmter Python-Prozess kann über seine Process-ID beendet werden:

```powershell
Stop-Process -Id <PROCESS_ID>
```

Beispiel:

```powershell
Stop-Process -Id 9932
```

Anschließend kann geprüft werden, ob noch Python-Prozesse laufen:

```powershell
Get-Process python
```

## MongoDB

MongoDB wird über Docker gestartet:

```powershell
docker compose up -d
```

Prüfen, ob der Container läuft:

```powershell
docker ps
```

Die MongoDB ist über Port `27017` erreichbar.

### Datenbank mit mongosh prüfen

Falls `mongosh` lokal installiert ist, kann eine Verbindung zur MongoDB hergestellt werden:

```powershell
mongosh "mongodb://localhost:27017"
```

Verfügbare Datenbanken anzeigen:

```javascript
show dbs
```

Die Datenbank des Scrapers auswählen:

```javascript
use web_mining
```

Collections anzeigen:

```javascript
show collections
```

Anzahl der gespeicherten Flugangebote prüfen:

```javascript
db.idealo_new.countDocuments()
```

Die MongoDB-Shell kann mit folgendem Befehl verlassen werden:

```javascript
exit
```

Alternativ kann `mongosh` direkt innerhalb des MongoDB-Containers gestartet werden:

```powershell
docker exec -it idealo-mongodb mongosh
```

### Collection leeren

Falls alle bereits gespeicherten Flugangebote im Collection `idealo_new` gelöscht werden sollen:

```javascript
use web_mining
db.idealo_new.deleteMany({})
```