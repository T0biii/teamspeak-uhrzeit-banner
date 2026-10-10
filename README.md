# TeamSpeak Uhrzeit-Banner

Kleiner Docker-Container, der ein PNG-Banner mit aktueller Uhrzeit, Datum und Tagesfortschritt ausliefert.
Gedacht für das Feld **Banner Gfx URL** eines TeamSpeak-3-Servers (Intervall: 60 Sekunden).

## Schnellstart

1. [docker-compose.example.yml](docker-compose.example.yml) als `docker-compose.yml` kopieren und
   Image-Name, Domain, Cert-Resolver und Netzwerk anpassen.
2. `docker compose pull && docker compose up -d`
3. In TeamSpeak unter *Banner Gfx URL* `https://banner.example.com/banner.png` eintragen.

## Konfiguration

| Variable       | Standard        | Beschreibung                          |
|----------------|-----------------|---------------------------------------|
| `TZ`           | `Europe/Berlin` | Zeitzone                              |
| `WIDTH`        | `468`           | Bildbreite in Pixel                   |
| `HEIGHT`       | `120`           | Bildhöhe in Pixel                     |
| `SHOW_SECONDS` | `false`         | Sekunden anzeigen                     |
| `PORT`         | `8080`          | Port im Container                     |

Endpunkte: `/banner.png` (auch `/` und `/clock.png`), `/health`.

## Image

Wird per GitHub Actions gebaut und liegt in der GitHub Container Registry:
`ghcr.io/<github-name>/teamspeak-uhrzeit-banner:latest` (`amd64` und `arm64`).

## Lokal bauen

```bash
docker build -t ts-clock-banner .
docker run --rm -p 8080:8080 ts-clock-banner
```

## Lizenz

[MIT](LICENSE)
