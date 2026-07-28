import csv
import subprocess
import time
import os
from pathlib import Path

env = os.environ.copy()

CSV_FILE = "flight_routes.csv"
BATCH_SIZE = 200
PAUSE_SECONDS = 5
ZERO_LIMIT = 5  #  wenn die Meldung  0 pages/min 5 mal hintereinander kommt
DAYS_PER_ROUTE = 7
BATCH_DIR = Path("batches")
BATCH_DIR.mkdir(exist_ok=True)

START_ROUTE_NUMBER = 0
START_INDEX = START_ROUTE_NUMBER - 1

def count_routes(csv_file):
    with Path(csv_file).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return sum(1 for _ in reader)

FINAL_STATUSES = {"completed", "blacklisted_iata", "same_iata"}

def batch_is_finished(statusfile, expected_count):
    path = Path(statusfile)

    if not path.exists():
        return False
    finished_count = 0

    with path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.strip().split(",")

                if len(parts) < 4:
                    continue

                last_status = parts[-1].strip()

                if last_status in FINAL_STATUSES:
                    finished_count += 1

    return finished_count >= expected_count

def count_consecutive_zero_pages(logfile):
    path = Path(logfile)

    if not path.exists():
        return 0

    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()

    count = 0

    for line in reversed(lines):
        if "[scrapy.extensions.logstats]" not in line:
            continue

        if "(at 0 pages/min)" in line:
            count += 1
        else:
            break
    return count

total_routes = count_routes(CSV_FILE)
MAX_RETRIES_PER_BATCH = 10



for start in range(START_INDEX, total_routes, BATCH_SIZE):
    batch_end = min(start + BATCH_SIZE, total_routes)

    attempt = 1

    while attempt <= MAX_RETRIES_PER_BATCH:

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        logfile = BATCH_DIR / f"batch_{start + 1}_{batch_end}_try_{attempt}_{timestamp}.log"
        statusfile = BATCH_DIR / f"batch_{start + 1}_{batch_end}.txt"
        
        expected_count = (batch_end - start) * DAYS_PER_ROUTE

        if batch_is_finished(statusfile,  expected_count):
            print(f"Batch {start + 1}-{batch_end} ist schon fertig. Next Batch.")
            break

        print("=" * 80)
        print(f"Starte Batch: Route {start + 1} bis {batch_end} | Versuch {attempt}")
        print("=" * 80)

        killed_by_zero = False

        process = subprocess.Popen(
            [
                "python", "-m", "scrapy", "crawl", "idealo",
                "-a", f"batch_start={start}",
                "-a", f"limit={BATCH_SIZE}",
                "-a", f"status_file={str(statusfile)}",
                #"-O", jsonfile,
                "--logfile", str(logfile),
            ],
            env=env,
        )

        while True:
            if process.poll() is not None:
                break
            time.sleep(10)

            zero_count = count_consecutive_zero_pages(logfile)

            if zero_count >= ZERO_LIMIT:
                killed_by_zero = True
                print(
                    f"Batch {start + 1}-{batch_end}: "
                    f"{ZERO_LIMIT}x 0 pages/min erkannt. Prozess wird beendet."
                )

                process.terminate()

                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

                break

        process.wait()

        if killed_by_zero:
            print(f"Batch {start + 1}-{batch_end} wird wiederholt.")
            attempt += 1
            continue

        if process.returncode != 0:
            print(f"Batch {start + 1}-{batch_end} wurde mit Fehler beendet.")
            attempt += 1
            continue

        print(f"Batch fertig: {start + 1} bis {batch_end}")
        break

    if attempt > MAX_RETRIES_PER_BATCH:
        print(f"Batch {start + 1}-{batch_end} nach {MAX_RETRIES_PER_BATCH} Versuchen nicht fertig.")
        break

    #if batch_end < total_routes:
        #print(f"Pause {PAUSE_SECONDS} Sekunden...")
        #time.sleep(PAUSE_SECONDS)

print("Alle Batches fertig.")