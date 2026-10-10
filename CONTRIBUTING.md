# Mitwirken

Beiträge sind willkommen!

1. Repo forken und einen Branch anlegen (`feature/mein-feature`).
2. Lokal testen:
   ```bash
   docker build -t ts-clock-banner .
   docker run --rm -p 8080:8080 ts-clock-banner
   ```
   Danach `http://localhost:8080/banner.png` im Browser öffnen.
3. Pull Request gegen `main` erstellen und die Vorlage ausfüllen.

Bei Design-Änderungen bitte ein Vorher/Nachher-Bild anhängen.
