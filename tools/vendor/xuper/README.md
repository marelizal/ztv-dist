# Vendor: runtime del servicio de XUPER-HYDRA-PORT-WEBOS

Los módulos de este directorio son el runtime del servicio Luna, vendidos del
proyecto upstream:

- Fuente: <https://github.com/cristianco7/XUPER-HYDRA-PORT-WEBOS>
  (`webos/services/com.webosflux.xuptertv.fidelity.service/`)
- Licencia: MIT — ver [`LICENSE`](./LICENSE). El binario FFmpeg embebido es
  GPLv3 (ver `ffmpeg-GPLv3.txt` generado por el build); su fuente y el tarball
  original están en `apps/service/vendor/ffmpeg-7.0.2-armhf-static.tar.xz`
  (upstream `tools/vendor/`).

| Archivo | Rol |
|---|---|
| `magis.js` | Protocolo del portal (cifrado 3DES, sesión anónima, catálogo, VOD, TV en vivo, semillas) |
| `proxy.js` | Proxy HLS/TS en loopback (puerto aleatorio) + subtítulos |
| `ffmpeg-relay.js` | Modo Fluido: TS/HEVC → fMP4 (`hvc1`) vía FFmpeg local en 127.0.0.1:8787 |
| `ts-indexer.js` | Indexador MPEG-TS para seek sobre el stream |
| `dnsx.js` | Resolución DNS-over-HTTPS multi-proveedor con caché |
| `upstream.js` | Proxy HTTP(S) saliente opcional (`setProxy`) |
| `netdiag.js` | Diagnóstico de red (TCP/TLS, DoH, IP pública, capas portal/sesión/live/VOD) |
| `updater.js` | OTA: `checkUpdate`/`applyUpdate` contra `ZTV_UPDATE_MANIFEST_URLS` |
| `seeds-fallback.json` | Semillas que viajan en el paquete (lo genera el build desde `platforms/webos/seed.json`) |

## Parches aplicados respecto del upstream

Mínimos, para identidad de z-tvsm y configurabilidad (el código y el protocolo
quedan intactos):

1. Rutas temporales: `/tmp/xuper-*` → `/tmp/ztvsm-*`.
2. `User-Agent` de diagnóstico: `XuperTV/webOS` → `ZTV/webOS`.
3. `magis.js`: `SEED_URL` sobre-escribible con `ZTV_SEEDS_URL` y export de
   `refreshSeeds` para el comando Luna del mismo nombre.
4. `ffmpeg-relay.js`: ruta del binario sobre-escribible con `ZTV_FFMPEG`.
5. `updater.js`: canales OTA vía `ZTV_UPDATE_MANIFEST_URLS` (sin canal
   configurado el método responde error claro); `APP_ID`/nombres → z-tvsm.

El entry del servicio (`apps/service/src/service-entry.ts`) es un port de su
`index.js` a TypeScript con los mismos comandos más los extras de z-tvsm
(`session`, `refreshSeeds`, `ensureStarted`).
