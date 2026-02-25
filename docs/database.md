# Database Connection Details

## Cloud SQL (PostgreSQL) — Google Cloud

| Field    | Value                  |
|----------|------------------------|
| Host     | 34.18.45.84            |
| Port     | 5432                   |
| Database | data_portal            |
| Username | dataportal             |
| Password | DataPortal2024         |

---

## Connection String

```
postgresql://dataportal:DataPortal2024@34.18.45.84:5432/data_portal
```

---

## Connect via psql

```bash
psql "postgresql://dataportal:DataPortal2024@34.18.45.84:5432/data_portal"
```

---

## Connect via DBeaver / TablePlus / DataGrip

| Field    | Value          |
|----------|----------------|
| Host     | 34.18.45.84    |
| Port     | 5432           |
| Database | data_portal    |
| User     | dataportal     |
| Password | DataPortal2024 |
| SSL      | disable        |

> **Note:** Your IP must be whitelisted in Cloud SQL authorized networks.
> Ask the project owner to add your IP at:
> GCP Console → SQL → data-portal-db → Connections → Authorized networks

To find your current IP:
```bash
curl ifconfig.me
```

---

## Cloud SQL Instance Info

| Field              | Value                                      |
|--------------------|--------------------------------------------|
| Instance           | data-portal-db                             |
| Project            | uniapply-486919                            |
| Region             | me-central1                                |
| Connection Name    | uniapply-486919:me-central1:data-portal-db |

---

## From Cloud Run (Unix Socket)

Services running on Cloud Run connect via the Cloud SQL Auth Proxy using a unix socket:

```
postgresql://dataportal:DataPortal2024@/data_portal?host=/cloudsql/uniapply-486919:me-central1:data-portal-db
```

---

## Other Secrets

| Secret         | Value                                        |
|----------------|----------------------------------------------|
| JWT SECRET_KEY | f53IBK0D0d8vZz0EyA_cxm-aMYxmnIanQYC984uau4M |
| GEMINI_API_KEY | AIzaSyAGO994FBa2zpKIOov_laUIHMKJ0cs4Gyw     |
