# BVMW SendHub

Interne Web-App zur Planung & Freigabe von Email-Aussendungen für einen Verband.

## Stack

| Schicht     | Technologie                                 |
|-------------|---------------------------------------------|
| Backend     | FastAPI 0.111, Python 3.11+, SQLAlchemy 2.0 |
| Datenbank   | PostgreSQL 15+                              |
| Migrationen | Alembic                                     |
| Storage     | LocalFS (S3-ready)                          |
| Frontend    | Next.js 14 (App Router), TypeScript         |
| UI          | Tailwind CSS, FullCalendar 6 (Drag & Drop)  |
| Auth        | Dev-Modus via `X-User`-Header, OIDC-ready   |

---

## Verzeichnisstruktur

```
BVMW-SendHub/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI App
│   │   ├── auth.py              # Auth-Dependency (X-User / OIDC)
│   │   ├── config.py            # Settings via Pydantic
│   │   ├── database.py          # SQLAlchemy Engine & Session
│   │   ├── models/              # ORM-Modelle
│   │   ├── schemas/             # Pydantic-Schemas
│   │   ├── routers/             # FastAPI-Router
│   │   ├── services/            # Business-Logik
│   │   └── storage/             # Storage-Abstraktion (Local / S3)
│   ├── alembic/                 # Datenbankmigrationen
│   ├── tests/                   # Pytest-Tests
│   ├── seed.py                  # Demo-Daten
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── app/                 # Next.js App Router
    │   │   ├── calendar/        # Kalender mit Drag & Drop
    │   │   ├── requests/        # Anfragenliste & neues Formular
    │   │   ├── campaigns/[id]/  # Kampagnen-Detail
    │   │   └── settings/        # Einstellungen
    │   ├── components/          # Shared Components
    │   ├── lib/api.ts           # API-Client
    │   └── types/               # TypeScript-Typen
    └── package.json
```

---

## Lokales Setup

### Voraussetzungen

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+

### 1. Datenbank anlegen

```bash
psql -U postgres
CREATE USER sendhub WITH PASSWORD 'sendhub';
CREATE DATABASE sendhub OWNER sendhub;
\q
```

### 2. Backend einrichten

```bash
cd backend

# Virtuelle Umgebung anlegen
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Umgebungsvariablen konfigurieren
cp .env.example .env
# .env anpassen (DATABASE_URL, etc.)
```

### 3. Datenbankmigrationen ausführen

```bash
cd backend
alembic upgrade head
```

### 4. Demo-Daten einspielen (Seed)

```bash
cd backend
python seed.py
```

Das Seed-Script legt an:
- 5 Demo-Abteilungen (Vorstand, Kommunikation, etc.)
- User `requester@bvmw.example` (Rolle: requester, Abteilung: Kommunikation)
- User `marketing@bvmw.example` (Rolle: marketing)
- Beispielkampagne "Demo Newsletter April 2025" mit PDF + 2 Bild-Assets

### 5. Backend starten

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

API läuft unter: http://localhost:8000
Swagger UI: http://localhost:8000/docs

### 6. Frontend einrichten & starten

```bash
cd frontend
npm install
npm run dev
```

Frontend läuft unter: http://localhost:3000

---

## Benutzer wechseln (Dev-Modus)

Die App läuft im Dev-Modus mit `X-User`-Header-Auth.
Im Browser oben rechts auf den Benutzernamen klicken, um zwischen Requester und Marketing zu wechseln.

| E-Mail                       | Rolle       |
|------------------------------|-------------|
| `requester@bvmw.example`     | Requester   |
| `marketing@bvmw.example`     | Marketing   |

API direkt testen:
```bash
# Als Requester
curl -H "X-User: requester@bvmw.example" http://localhost:8000/me

# Als Marketing
curl -H "X-User: marketing@bvmw.example" http://localhost:8000/settings
```

---

## Tests ausführen

```bash
cd backend
source .venv/bin/activate
pytest -v
```

Die Tests nutzen eine In-Memory SQLite-Datenbank (kein Postgres nötig).

Abgedeckt:
- `validate_email_slot`: Mindestabstand-Validierung, Konflikte, Selbst-Ausschluss, Custom-Gap
- `next_available`: Kein Konflikt, Mit Blocking-Kampagne, Custom-Gap, Neueste gewinnt
- Status-Transitions: Erlaubte und verbotene Übergänge für beide Rollen

---

## Konfiguration

### Umgebungsvariablen (`.env`)

| Variable               | Default                                             | Beschreibung                     |
|------------------------|-----------------------------------------------------|----------------------------------|
| `DATABASE_URL`         | `postgresql://sendhub:sendhub@localhost:5432/sendhub` | PostgreSQL-URL                 |
| `STORAGE_BACKEND`      | `local`                                             | `local` oder `s3`               |
| `STORAGE_LOCAL_BASE`   | `./storage`                                         | Basis-Pfad für lokale Dateien   |
| `AWS_ACCESS_KEY_ID`    | –                                                   | Für S3-Storage                  |
| `AWS_SECRET_ACCESS_KEY`| –                                                   | Für S3-Storage                  |
| `AWS_REGION`           | `eu-central-1`                                      | Für S3-Storage                  |
| `S3_BUCKET`            | `sendhub-files`                                     | S3-Bucket-Name                  |
| `SECRET_KEY`           | `dev-secret-key`                                    | Für spätere JWT-Signierung       |
| `ENVIRONMENT`          | `development`                                       | `development` oder `production` |

---

## Termin-Regel (Email-Kanal)

- Zwischen zwei Aussendungen mit blockierendem Status (`scheduled`, `approved`, `sent`) müssen mindestens `min_gap_days` **Kalendertage** liegen.
- Default: **2 Tage** (Mo → Mi OK, Mo → Di NICHT OK)
- Marketing kann den Mindestabstand unter `/settings` anpassen.
- Serverseitig validiert via `validate_email_slot()`.

---

## Statusmodell

```
submitted → in_review → scheduled → approved → sent
                   ↓         ↓           ↓
             changes_needed → submitted  rejected
```

Blockierend für Mindestabstand: `scheduled`, `approved`, `sent`

---

## S3-Migration

Um von LocalFS auf S3 zu wechseln:

```env
STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=eu-central-1
S3_BUCKET=mein-bucket
```

Die Storage-Abstraktion (`app/storage/`) ist so konzipiert, dass kein Anwendungscode geändert werden muss.

---

## OIDC-Integration

Die Datei `app/auth.py` enthält einen Placeholder für OIDC-Token-Validierung.
Aktuell wird im `ENVIRONMENT=development`-Modus der `X-User`-Header genutzt.
Für Produktion: `ENVIRONMENT=production` setzen und OIDC-Logik in `get_current_user()` implementieren.