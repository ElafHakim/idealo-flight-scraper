from pathlib import Path


class StatusHandler:
    def __init__(self, status_file):
        self.status_file = status_file

    def mark_route_status(self, route, departure_date, status):

        path = Path(self.status_file)
        uid = route["uid"]
        key = f"{uid},{departure_date},{route['from']},{route['to']}"

        if not path.exists():
            with path.open("w", encoding="utf-8") as f:
                f.write(f"{key},{status}\n")
            return

        lines = path.read_text(encoding="utf-8").splitlines()
        updated = False

        for i, line in enumerate(lines):
            if line.startswith(f"{key},"):
                lines[i] = line + f",{status}"
                updated = True
                break

        # Route noch nicht vorhanden
        if not updated:
            lines.append(f"{key},{status}")

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def load_completed_routes(self):
        path = Path(self.status_file)

        if not path.exists():
            return set()

        completed_keys = set()

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")

                if len(parts) < 5:
                    continue

                uid = parts[0]
                departure_date = parts[1]
                last_status = parts[-1]

                if last_status == "completed":
                    completed_keys.add((uid, departure_date))

        return completed_keys

    def load_problematic_routes(self):
        path = Path(self.status_file)
        if not path.exists():
            return set()

        problematic_ids = set()

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")

                if len(parts) < 4:
                    continue

                uid = parts[0]
                last_status = parts[-1]

                if last_status == "problematic":
                    problematic_ids.add(uid)

        return problematic_ids


def load_no_searchid_fount_routes(self):
    path = Path(self.status_file)
    if not path.exists():
        return set()

    no_searchid_found_ids = set()

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")

            if len(parts) < 4:
                continue

            uid = parts[0]
            last_status = parts[-1]

            if last_status == "no_searchid_found":
                no_searchid_found_ids.add(uid)

    return no_searchid_found_ids


def load_service_unavailable_routes(self):
    path = Path(self.status_file)

    if not path.exists():
        return set()

    service_unavailable_ids = set()

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")

            if len(parts) < 4:
                continue

            uid = parts[0]
            last_status = parts[-1]

            if last_status == "503_service_unavailable":
                service_unavailable_ids.add(uid)

    return service_unavailable_ids


def load_first_queued_routes(self, limit=12):
    path = Path(self.status_file)

    if not path.exists():
        return set()

    queued_ids = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(",")

            if len(parts) < 4:
                continue

            uid = parts[0]
            last_status = parts[-1]

            if last_status == "queued":
                queued_ids.append(uid)

            if len(queued_ids) >= limit:
                break

    return set(queued_ids)
