#!/usr/bin/env python3
"""
Obtiene la agenda de eventos deportivos de tvlibre.st y la exporta como JSON.

Uso:
  python3 tools/fetch_tvlibre_agenda.py
  python3 tools/fetch_tvlibre_agenda.py --out agenda.json
  python3 tools/fetch_tvlibre_agenda.py --pretty

La salida incluye, por evento, título, hora, categoría (clase CSS) y las
opciones de canal/enlace disponibles. Para enlaces /eventos/?r=..., se decodifica
el parámetro r (base64) como URL de destino.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Optional

AGENDA_URL = "https://tvlibre.st/agenda/"
BASE_URL = "https://tvlibre.st"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def fetch_html(url: str = AGENDA_URL, timeout: float = 20.0) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-419,es;q=0.9,en;q=0.8",
            "Referer": BASE_URL + "/",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as res:
        raw = res.read()
    return raw.decode("utf-8", errors="replace")


def absolutize(href: str) -> str:
    href = (href or "").strip()
    if not href:
        return ""
    return urllib.parse.urljoin(BASE_URL + "/", href)


def decode_r_param(href: str) -> Optional[str]:
    """Decodifica el parámetro r (base64/base64url) de /eventos/?r=... si existe."""
    try:
        parsed = urllib.parse.urlparse(href)
        qs = urllib.parse.parse_qs(parsed.query)
        vals = qs.get("r") or qs.get("url") or []
        if not vals:
            return None
        token = vals[0].strip()
        if not token:
            return None
        # base64url y base64 estándar (con o sin padding)
        padded = token + "=" * (-len(token) % 4)
        try:
            raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        except Exception:
            raw = base64.b64decode(padded.encode("ascii"))
        decoded = raw.decode("utf-8", errors="replace").strip()
        return decoded or None
    except Exception:
        return None


def norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()


class AgendaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.header_date: str = ""
        self.events: list[dict[str, Any]] = []

        self._in_header = False
        self._header_buf: list[str] = []

        self._in_menu = False
        self._menu_depth = 0

        self._event_li_depth = 0  # depth of current top-level event <li> within .menu
        self._sub_li_depth = 0
        self._in_event_a = False
        self._in_event_t = False
        self._in_event_tt = False
        self._event_text_buf: list[str] = []
        self._event_time_buf: list[str] = []

        self._in_sub_a = False
        self._in_sub_span = False
        self._sub_text_buf: list[str] = []
        self._sub_quality_buf: list[str] = []
        self._sub_href: str = ""

        self._cur: Optional[dict[str, Any]] = None
        self._cur_opt: Optional[dict[str, Any]] = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        attr = {k: (v or "") for k, v in attrs}
        classes = set((attr.get("class") or "").split())

        if tag == "div" and "agenda-header" in classes:
            self._in_header = True
            self._header_buf = []

        if tag == "ul" and "menu" in classes and not self._in_menu:
            self._in_menu = True
            self._menu_depth = 1
            return
        if self._in_menu and tag == "ul":
            self._menu_depth += 1

        if self._in_menu and tag == "li":
            if self._event_li_depth == 0 and "subitem1" not in classes and "subitem" not in classes:
                # top-level event item
                self._event_li_depth = 1
                self._cur = {
                    "category": next((c for c in classes if c not in {"open", "has-sub"}), ""),
                    "title": "",
                    "time": "",
                    "options": [],
                }
                self._event_text_buf = []
                self._event_time_buf = []
                return
            elif self._event_li_depth >= 1:
                self._event_li_depth += 1
                if "subitem1" in classes or "subitem" in classes or (self._sub_li_depth == 0 and self._cur is not None):
                    # option inside event's sublist
                    # Heuristic: li directly inside the nested ul of event (depth becomes 2 at first nested li)
                    if self._sub_li_depth == 0:
                        self._sub_li_depth = 1
                        self._cur_opt = {"name": "", "quality": "", "href": "", "url": None}
                        self._sub_text_buf = []
                        self._sub_quality_buf = []
                        self._sub_href = ""
                    else:
                        self._sub_li_depth += 1
                return

        if self._cur is not None and tag == "a":
            if self._event_li_depth == 1 and self._sub_li_depth == 0:
                self._in_event_a = True
                self._in_event_t = False
            elif self._sub_li_depth >= 1 and self._cur_opt is not None:
                self._in_sub_a = True
                self._sub_href = attr.get("href", "")
                self._in_sub_span = False

        if self._in_event_a and tag == "span" and "t" in classes:
            self._in_event_t = True
        if self._in_sub_a and tag == "span":
            self._in_sub_span = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "div" and self._in_header:
            self._in_header = False
            self.header_date = norm_text("".join(self._header_buf))

        if not self._in_menu:
            return

        if tag == "span":
            if self._in_event_t:
                self._in_event_t = False
            if self._in_sub_span:
                self._in_sub_span = False

        if tag == "a":
            if self._in_sub_a and self._cur_opt is not None:
                self._in_sub_a = False
                name = norm_text("".join(self._sub_text_buf))
                quality = norm_text("".join(self._sub_quality_buf))
                href_abs = absolutize(self._sub_href)
                self._cur_opt["name"] = name
                self._cur_opt["quality"] = quality
                self._cur_opt["href"] = href_abs
                self._cur_opt["url"] = decode_r_param(href_abs)
            elif self._in_event_a and self._sub_li_depth == 0:
                self._in_event_a = False

        if tag == "li":
            if self._sub_li_depth > 0:
                if self._sub_li_depth == 1 and self._cur is not None and self._cur_opt is not None:
                    # finalize option
                    if self._cur_opt.get("name") or self._cur_opt.get("href"):
                        self._cur["options"].append(self._cur_opt)
                    self._cur_opt = None
                self._sub_li_depth -= 1
                self._event_li_depth = max(0, self._event_li_depth - 1)
                return
            if self._event_li_depth > 0:
                if self._event_li_depth == 1 and self._cur is not None:
                    # finalize event
                    title = norm_text("".join(self._event_text_buf))
                    time = norm_text("".join(self._event_time_buf))
                    self._cur["title"] = title
                    self._cur["time"] = time
                    if title or self._cur["options"]:
                        self.events.append(self._cur)
                    self._cur = None
                self._event_li_depth -= 1
                return

        if tag == "ul":
            self._menu_depth -= 1
            if self._menu_depth <= 0:
                self._in_menu = False
                self._menu_depth = 0

    def handle_data(self, data: str) -> None:
        if self._in_header:
            self._header_buf.append(data)
            return
        if not self._in_menu:
            return
        if self._in_sub_a and self._cur_opt is not None:
            if self._in_sub_span:
                self._sub_quality_buf.append(data)
            else:
                self._sub_text_buf.append(data)
            return
        if self._in_event_a and self._cur is not None:
            if self._in_event_t:
                self._event_time_buf.append(data)
            else:
                self._event_text_buf.append(data)


def parse_agenda(html: str) -> dict[str, Any]:
    parser = AgendaParser()
    parser.feed(html)
    parser.close()
    return {
        "source": AGENDA_URL,
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "date": parser.header_date,
        "count": len(parser.events),
        "events": parser.events,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Exporta la agenda de tvlibre.st como JSON")
    ap.add_argument("--out", help="ruta de salida (por defecto: stdout)")
    ap.add_argument("--pretty", action="store_true", help="JSON con indentación")
    ap.add_argument("--timeout", type=float, default=20.0, help="timeout HTTP en segundos")
    args = ap.parse_args()

    try:
        html = fetch_html(timeout=args.timeout)
        data = parse_agenda(html)
    except Exception as e:
        print(f"Error obteniendo agenda: {e}", file=sys.stderr)
        return 1

    indent = 2 if args.pretty else None
    payload = json.dumps(data, ensure_ascii=False, indent=indent)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload)
            if indent is not None:
                f.write("\n")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
