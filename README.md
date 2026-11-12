# ztv-dist

Distribucion publica de ZTV. Este repo **no tiene codigo**: solo datos que la
TV descarga por HTTP.

## Que hay aqui

| Ruta | Para que la usa la TV |
|---|---|
| `seeds.json` (rama `seeds`) | Pool de semillas de sesion del portal. |
| `version.json` (rama `main`) | Manifiesto de actualizacion OTA. |
| `releases/` | Paquetes `.ipk` publicados para instalar. |

## URLs que consume la TV

```
https://raw.githubusercontent.com/marelizal/ztv-dist/seeds/seeds.json
https://raw.githubusercontent.com/marelizal/ztv-dist/main/version.json
```

Las dos van horneadas en el paquete webOS, en
`platforms/webos/service/com.zafiro.tv.service/config.json`.

## Quien publica

El repo privado `marelizal/z-tvsm` genera y publica todo aca:

- `seeds.json`: el workflow `seeds.yml` acuña semillas nuevas y las sube.
- `version.json` y los `.ipk`: el workflow `publish.yml` los sube al tag.

Este repo no tiene secrets ni workflows: es solo el destino de las
publicaciones.

## Sobre las semillas

Cada semilla es una sesion del portal (`userId`, `userToken`, `sn`) con vida
corta. El pool se renueva cada pocas horas y las semillas viejas se descartan
solas. Publicarlas es lo mismo que hace el proyecto XUPER: son credenciales de
vida corta, no la llave del portal.

## version.json

```json
{
  "version": "0.1.3",
  "name": "z-tvsm",
  "minWebos": "1.0.0",
  "ipkUrl": "https://github.com/marelizal/ztv-dist/releases/download/v0.1.3/com.zafiro.tv_0.1.3_all.ipk",
  "sha256": "…",
  "changelog": "…",
  "releaseDate": "2026-11-12"
}
```
