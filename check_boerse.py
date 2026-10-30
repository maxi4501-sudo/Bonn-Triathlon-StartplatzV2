#!/usr/bin/env python3
"""Überwacht die datasport-Startplatzbörse und schickt bei neuen Einträgen
eine Push-Nachricht (ntfy.sh) mit Link aufs Handy."""
import json
import os
import re
import sys

import requests
from bs4 import BeautifulSoup

URL = "https://www.datasport.de/anmeldeservice/492/3316/boerse/12154/"
STATE_FILE = "state.json"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9",
}


def fetch_lines() -> list[str]:
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "input", "meta", "link"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln]


def notify(topic: str, title: str, message: str) -> None:
    # Header müssen ASCII sein, der Body darf Umlaute enthalten.
    requests.post(
        f"https://ntfy.sh/{topic}",
        data=message.encode("utf-8"),
        headers={
            "Title": title,
            "Click": URL,
            "Priority": "urgent",
            "Tags": "bell,triathlon",
        },
        timeout=30,
    ).raise_for_status()


def main() -> int:
    try:
        lines = fetch_lines()
    except Exception as e:  # noqa: BLE001
        print(f"Fehler beim Abrufen: {e}", file=sys.stderr)
        return 1

    if "--debug" in sys.argv:
        print("\n".join(lines))
        return 0

    topic = os.environ["NTFY_TOPIC"]

    if not os.path.exists(STATE_FILE):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"lines": lines}, f, ensure_ascii=False, indent=1)
        notify(topic, "Ueberwachung gestartet",
               "Die Startplatzboerse wird jetzt ueberwacht.")
        print("Erster Lauf, Zustand gespeichert.")
        return 0

    with open(STATE_FILE, encoding="utf-8") as f:
        old = json.load(f)["lines"]

    new_lines = [ln for ln in lines if ln not in set(old)]
    if new_lines:
        snippet = "\n".join(new_lines)[:400]
        notify(topic, "Startplatz Bonn Triathlon!", f"Neu in der Boerse:\n{snippet}")
        print("Benachrichtigung gesendet:", new_lines)

    if lines != old:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"lines": lines}, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
