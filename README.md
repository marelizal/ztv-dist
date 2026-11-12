# ztv-dist

Distribucion publica de ZTV. Este repo **no tiene codigo**: solo datos que la
TV descarga por HTTP.

## Que hay aqui

| Ruta | Para que la usa la TV |
|---|---|
| `seeds.json` (rama `seeds`) | Pool de semillas de sesion, cifrado. |
| `version.json` (rama `main`) | Manifiesto de actualizacion OTA. |
| `releases/` | Paquetes `.ipk` publicados para instalar. |

## URLs que consume la TV

```
https://raw.githubusercontent.com/marelizal/ztv-dist/seeds/seeds.json
https://raw.githubusercontent.com/marelizal/ztv-dist/main/version.json
```

Las dos van horneadas en el paquete webOS, en
`platforms/webos/service/com.zafiro.tv.service/config.json`.

## Pool de semillas cifrado

El pool travels cifrado: son credenciales de sesion y no van en claro a un
repo publico.

- Formato: `{"v":1,"alg":"aes-256-gcm","data":"<base64>"}`.
- La clave la tiene solo el service, horneada en el paquete webOS.
- El service descifra el pool al descargarlo; si la clave no esta o el
  contenido no descifra, se descarta el pool y se sigue con la sesion propia.

Quien publica el pool cifrado es el repo privado del proyecto, con el
workflow `seeds.yml`: acuña semillas, las cifra y las sube a la rama `seeds`.

## Quien publica

El repo privado del proyecto genera y publica todo aca:

- `seeds.json`: el workflow `seeds.yml` acuña, cifra y sube el pool.
- `version.json` y los `.ipk`: el workflow `publish.yml` los sube al tag.

Este repo no tiene secrets ni workflows: es solo el destino de las
publicaciones.

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
