#!/usr/bin/env python3
"""
Genera un único archivo `sports.json` para la18hd (canales) + tvlibre (agenda).

- Obtiene el catálogo de canales desde la18hd.su/status.json.
- Resuelve y verifica cada canal activo (check en vivo) y marca `enabled`
  según si funciona o no (el "renew"/verificación habilita o inhabilita).
- Obtiene la agenda de eventos desde tvlibre.st/agenda/.
- Publica todo en un solo JSON independiente del consumidor.

Uso:
  python3 tools/build_sports.py --out sports.json
  python3 tools/build_sports.py --out sports.json --timeout 15
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

# Permitir importar scripts hermanos (tools/)
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import fetch_tvlibre_agenda as tvlibre  # noqa: E402
import renew_pelotalibre_links as la18  # noqa: E402


def build_la18(timeout: float = 20.0) -> dict[str, Any]:
    """Obtiene, resuelve y verifica canales la18hd; devuelve estructura por país."""
    try:
        channels = la18.fetch_status(timeout=timeout)
    except Exception:
        channels = list(la18.FALLBACK_CHANNELS)

    # solo activos de origen, dedupe por stream
    channels = [c for c in channels if c.get("active")]
    seen: set[str] = set()
    unique = []
    for c in channels:
        s = c.get("stream")
        if not s or s in seen:
            continue
        seen.add(s)
        unique.append(c)
    channels = unique

    countries: dict[str, list[dict[str, Any]]] = {}
    ok_count = 0

    for ch in channels:
        stream = ch["stream"]
        name = ch.get("name") or stream
        country = ch.get("country") or "OTROS"

        entry: dict[str, Any] = {
            "stream": stream,
            "name": name,
            "enabled": False,
            "sourceActive": bool(ch.get("active")),
            "resolvedUrl": None,
            "check": None,
            "error": None,
        }

        try:
            url = la18.resolve(stream, timeout=timeout)
            entry["resolvedUrl"] = url
            cok, detail = la18.check_m3u8(url, timeout=min(15.0, timeout))
            entry["check"] = {"ok": cok, "detail": detail}
            entry["enabled"] = bool(cok)
            if not cok:
                entry["error"] = detail
        except Exception as e:
            entry["error"] = str(e)
            entry["check"] = {"ok": False, "detail": str(e)}
            entry["enabled"] = False

        if entry["enabled"]:
            ok_count += 1

        countries.setdefault(country, []).append(entry)

    return {
        "source": la18.STATUS_URL,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "ok": ok_count,
        "total": len(channels),
        "countries": countries,
    }


def build_tvlibre(timeout: float = 20.0) -> dict[str, Any]:
    """Obtiene la agenda/eventos de tvlibre.st."""
    try:
        html = tvlibre.fetch_html(timeout=timeout)
        data = tvlibre.parse_agenda(html)
        # mantener campos relevantes y consistentes
        return {
            "source": tvlibre.AGENDA_URL,
            "fetchedAt": data.get("fetchedAt"),
            "date": data.get("date"),
            "count": data.get("count", 0),
            "events": data.get("events", []),
        }
    except Exception as e:
        return {
            "source": tvlibre.AGENDA_URL,
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
            "date": None,
            "count": 0,
            "events": [],
            "error": str(e),
        }


def main() -> int:
    ap = argparse.ArgumentParser(description="Genera sports.json (la18hd verificado + agenda tvlibre)")
    ap.add_argument("--out", required=True, help="ruta de salida para sports.json")
    ap.add_argument("--timeout", type=float, default=20.0, help="timeout de red en segundos")
    ap.add_argument("--pretty", action="store_true", help="JSON con indentación (por defecto: compacto)")
    args = ap.parse_args()

    la18_data = build_la18(timeout=args.timeout)
    tvlibre_data = build_tvlibre(timeout=args.timeout)

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "timezone": "UTC",
        "sources": {
            "la18": la18.STATUS_URL,
            "tvlibre": tvlibre.AGENDA_URL,
        },
        "la18": la18_data,
        "tvlibre": tvlibre_data,
    }

    indent = 2 if args.pretty else None
    text = json.dumps(payload, ensure_ascii=False, indent=indent)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(text)
        if indent is not None:
            f.write("\n")

    ok = int(la18_data.get("ok", 0))
    total = int(la18_data.get("total", 0))
    all_ok = total > 0 and ok == total
    print(f"sports.json generado: la18 {ok}/{total} habilitados, tvlibre {tvlibre_data.get('count', 0)} eventos")
    # Generación exitosa siempre que se haya escrito el archivo; el estado de canales
    # queda reflejado en enabled/disabled dentro del JSON.
    return 0 if all_ok else 2



if __name__ == "__main__":
    sys.exit(main())
