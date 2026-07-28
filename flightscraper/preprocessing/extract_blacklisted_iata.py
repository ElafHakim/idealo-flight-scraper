from pathlib import Path

INPUT_FILE = "iata_validation_status.txt"
OUTPUT_FILE = "blacklisted_iata_for_idealo.txt"

BAD_STATUSES = {
    "no_searchid_found",
    "503_service_unavailable",
}

blacklisted_iata = set()

with Path(INPUT_FILE).open("r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        parts = line.strip().split(",")

        if len(parts) != 5:
            continue

        iata = parts[0].strip().upper()
        status = parts[4].strip()

        if status in BAD_STATUSES:
            blacklisted_iata.add(iata)

Path(OUTPUT_FILE).write_text(
    "\n".join(sorted(blacklisted_iata)) + "\n",
    encoding="utf-8"
)

print(f"Gefundene IATA: {len(blacklisted_iata)}")
print(f"Gespeichert in: {OUTPUT_FILE}")