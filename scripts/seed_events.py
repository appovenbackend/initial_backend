import json
import random
import string
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib import request, error


def rand_string(prefix: str, length: int = 8) -> str:
    letters = string.ascii_letters + string.digits
    return f"{prefix}{''.join(random.choice(letters) for _ in range(length))}"


def iso(dt: datetime) -> str:
    # Use timezone-aware ISO format in UTC to avoid ambiguity
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def build_event_payload(is_paid: bool) -> dict:
    now = datetime.now(timezone.utc)
    start_at = now + timedelta(days=random.randint(2, 20), hours=random.randint(0, 20))
    duration_hours = random.choice([2, 3, 4])
    end_at = start_at + timedelta(hours=duration_hours)

    title = rand_string("Event-", 6)
    description = f"Auto-seeded event {title} with duration {duration_hours}h."
    city = random.choice(["Mumbai", "Bengaluru", "Delhi", "Pune", "Hyderabad", "Chennai", "Kolkata", "Ahmedabad"]) 
    venue = random.choice(["Auditorium A", "City Hall", "Open Grounds", "Convention Center", "Community Hub", "Tech Park"]) 

    price = 0 if not is_paid else random.choice([99, 149, 199, 249, 299, 399, 499, 799, 999])

    # Random banner via picsum with a deterministic seed
    seed = rand_string("seed-", 10)
    banner_url = f"https://picsum.photos/seed/{seed}/1200/600.jpg"

    payload = {
        "title": title,
        "description": description,
        "city": city,
        "venue": venue,
        "startAt": iso(start_at),
        "endAt": iso(end_at),
        "priceINR": price,
        "bannerUrl": banner_url,
        "isActive": True,
        "organizerName": "bhag",
        "organizerLogo": "https://picsum.photos/seed/logo-" + seed + "/200/200.jpg",
    }
    return payload


def post_json(url: str, data: dict) -> tuple[int, str]:
    body = json.dumps(data).encode("utf-8")
    req = request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.urlopen(req, timeout=30) as resp:
            return resp.getcode(), resp.read().decode("utf-8")
    except error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return -1, str(e)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/seed_events.py <base_url> [--free N] [--paid M]")
        print("Example: python scripts/seed_events.py https://initialbackend-production.up.railway.app --free 45 --paid 5")
        sys.exit(1)

    base_url = sys.argv[1].rstrip('/')
    free_count = 45
    paid_count = 5

    # Parse optional args
    args = sys.argv[2:]
    for i in range(0, len(args), 2):
        if i + 1 >= len(args):
            break
        key, val = args[i], args[i + 1]
        if key == "--free":
            try:
                free_count = int(val)
            except ValueError:
                pass
        elif key == "--paid":
            try:
                paid_count = int(val)
            except ValueError:
                pass

    url = f"{base_url}/events/"
    print(f"Seeding events to: {url}")

    total = free_count + paid_count
    created = 0
    failures = 0

    # Create free events
    for idx in range(free_count):
        payload = build_event_payload(is_paid=False)
        code, body = post_json(url, payload)
        ok = 200 <= code < 300
        status = "OK" if ok else f"ERR {code}"
        print(f"[{idx + 1}/{total}] FREE  {status} - {payload['title']}")
        if ok:
            created += 1
        else:
            failures += 1
        time.sleep(0.1)

    # Create paid events
    for jdx in range(paid_count):
        payload = build_event_payload(is_paid=True)
        code, body = post_json(url, payload)
        ok = 200 <= code < 300
        status = "OK" if ok else f"ERR {code}"
        # Avoid non-ASCII currency symbols to prevent Windows console encoding issues
        print(f"[{free_count + jdx + 1}/{total}] PAID  {status} - {payload['title']} (INR {payload['priceINR']})")
        if ok:
            created += 1
        else:
            failures += 1
        time.sleep(0.1)

    print("")
    print(f"Created: {created}/{total} | Failed: {failures}")


if __name__ == "__main__":
    main()


