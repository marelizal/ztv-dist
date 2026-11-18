#!/usr/bin/env python3
"""
Prueba y "renueva" (resuelve en el momento) los enlaces HLS de los canales
de la18hd.su (deportes y TV), los mismos que usa la app (PelotaLibre).

Uso:
  python3 tools/renew_pelotalibre_links.py
  python3 tools/renew_pelotalibre_links.py --check          # también verifica el m3u8
  python3 tools/renew_pelotalibre_links.py --json           # salida JSON
  python3 tools/renew_pelotalibre_links.py --all            # incluye canales inactivos
  python3 tools/renew_pelotalibre_links.py --country ARGENTINA

Por defecto verifica solo canales marcados como Activo en status.json.
Nota: los enlaces son tokenizados/efímeros; este script obtiene URLs frescas
al ejecutarse, no las persiste en la app.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from typing import Optional

STATUS_URL = "https://la18hd.su/status.json"
PAGE_URL = "https://la18hd.su/vivo/canal.php?stream={stream}"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
PAGE_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-419,es;q=0.9,en;q=0.8",
    "Referer": "https://pelotalibre.mx/",
    "Sec-Fetch-Dest": "iframe",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "Upgrade-Insecure-Requests": "1",
}
PLAYBACK_HEADERS = {
    "User-Agent": UA,
    "Referer": "https://pelotalibre.mx/",
    "Origin": "https://la18hd.su",
}

SRC_RE = re.compile(r'"src"\s*:\s*"(https?://[^"]+\.m3u8[^"]*)"')

# Respaldo si status.json no está disponible
FALLBACK_CHANNELS = [
    {"stream": "dsports", "name": "DSports", "country": "LATINOAMERICA", "active": True},
    {"stream": "dsports2", "name": "DSports 2", "country": "LATINOAMERICA", "active": True},
    {"stream": "dsportsplus", "name": "DSports+", "country": "LATINOAMERICA", "active": True},
    {"stream": "espn", "name": "ESPN", "country": "LATINOAMERICA", "active": True},
    {"stream": "espn2", "name": "ESPN 2", "country": "LATINOAMERICA", "active": True},
    {"stream": "espn3", "name": "ESPN 3", "country": "LATINOAMERICA", "active": True},
    {"stream": "foxsports", "name": "Fox Sports", "country": "ARGENTINA", "active": True},
    {"stream": "foxsports2", "name": "Fox Sports 2", "country": "ARGENTINA", "active": True},
    {"stream": "foxsports3", "name": "Fox Sports 3", "country": "ARGENTINA", "active": True},
]


def fetch_status(timeout: float = 20.0):
    req = urllib.request.Request(STATUS_URL, headers={"User-Agent": UA, "Accept": "application/json,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        data = json.loads(res.read().decode("utf-8", errors="replace"))
    channels = []
    for country, arr in data.items():
        if not isinstance(arr, list):
            continue
        for c in arr:
            if not isinstance(c, dict):
                continue
            name = str(c.get("Canal", "")).strip()
            estado = str(c.get("Estado", "")).strip()
            link = str(c.get("Link", "")).strip()
            stream = ""
            if link:
                qs = urllib.parse.urlparse(link).query
                stream = urllib.parse.parse_qs(qs).get("stream", [""])[0]
            if not stream:
                stream = str(c.get("stream", "")).strip()
            if not stream or not name:
                continue
            channels.append({
                "stream": stream,
                "name": name,
                "country": str(country),
                "active": estado.lower() == "activo",
            })
    return channels


def extract_m3u8(body: str) -> Optional[str]:
    m = SRC_RE.search(body)
    if m:
        return m.group(1).strip()
    m = re.search(r"(https?://[^\"'\s>]+\.m3u8[^\"'\s>]*)", body)
    if m:
        return m.group(1).strip()
    return None


def resolve(stream: str, timeout: float = 20.0) -> str:
    url = PAGE_URL.format(stream=urllib.parse.quote(stream, safe=""))
    req = urllib.request.Request(url, headers=PAGE_HEADERS, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as res:
        if res.status != 200:
            raise RuntimeError(f"HTTP {res.status}")
        body = res.read().decode("utf-8", errors="replace")
    m3u8 = extract_m3u8(body)
    if not m3u8:
        raise RuntimeError("stream no encontrado (no se halló .m3u8 en la página)")
    return m3u8


def check_m3u8(url: str, timeout: float = 15.0) -> tuple[bool, str]:
    req = urllib.request.Request(url, headers=PLAYBACK_HEADERS, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            ct = res.headers.get("Content-Type", "")
            sample = res.read(512).decode("utf-8", errors="replace")
            ok = res.status == 200 and ("#EXTM3U" in sample or "mpegurl" in ct.lower() or ".m3u8" in url)
            detail = f"HTTP {res.status} ct={ct!r} m3u8={'sí' if '#EXTM3U' in sample else 'no'}"
            return ok, detail
    except Exception as e:
        return False, str(e)


def main() -> int:
    ap = argparse.ArgumentParser(description="Renueva/verifica enlaces de la18hd (deportes y TV)")
    ap.add_argument("--check", action="store_true", help="verificar que el m3u8 responda")
    ap.add_argument("--json", action="store_true", help="salida JSON")
    ap.add_argument("--all", action="store_true", help="incluir canales inactivos")
    ap.add_argument("--country", help="filtrar por país (ej. ARGENTINA, USA)")
    ap.add_argument("--timeout", type=float, default=20.0, help="timeout de red en segundos")
    args = ap.parse_args()

    try:
        channels = fetch_status(timeout=args.timeout)
    except Exception as e:
        if not args.json:
            print(f"Aviso: no se pudo leer status.json ({e}), usando lista de respaldo", file=sys.stderr)
        channels = list(FALLBACK_CHANNELS)

    if args.country:
        want = args.country.strip().upper()
        channels = [c for c in channels if c.get("country", "").upper() == want]
    if not args.all:
        channels = [c for c in channels if c.get("active")]

    # dedupe por stream conservando orden
    seen = set()
    unique = []
    for c in channels:
        s = c["stream"]
        if s in seen:
            continue
        seen.add(s)
        unique.append(c)
    channels = unique

    results = []
    ok_count = 0
    for ch in channels:
        stream = ch["stream"]
        name = ch["name"]
        row = {
            "stream": stream,
            "name": name,
            "country": ch.get("country"),
            "ok": False,
            "url": None,
            "error": None,
            "check": None,
        }
        try:
            url = resolve(stream, timeout=args.timeout)
            row["url"] = url
            row["ok"] = True
            if args.check:
                cok, detail = check_m3u8(url, timeout=min(15.0, args.timeout))
                row["check"] = {"ok": cok, "detail": detail}
                row["ok"] = row["ok"] and cok
        except Exception as e:
            row["error"] = str(e)
        if row["ok"]:
            ok_count += 1
        results.append(row)

        if not args.json:
            status = "OK" if row["ok"] else "FALLO"
            country = ch.get("country") or ""
            print(f"[{status}] {name} ({stream}) [{country}]")
            if row.get("url"):
                print(f"  url: {row['url']}")
            if row.get("check"):
                c = row["check"]
                print(f"  check: {'OK' if c['ok'] else 'FALLO'} - {c['detail']}")
            if row.get("error"):
                print(f"  error: {row['error']}")

    total = len(channels)
    if args.json:
        print(json.dumps({"ok": ok_count, "total": total, "channels": results}, ensure_ascii=False, indent=2))
    else:
        print(f"\nResumen: {ok_count}/{total} canales OK")

    return 0 if total > 0 and ok_count == total else 1


if __name__ == "__main__":
    sys.exit(main())
