# Cloud Run Deployment Setup

## One-Time GCP Setup

Run these commands once before the first deploy.

### 1. Enable Required APIs
```bash
gcloud config set project uniapply-486919

gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```

### 2. Create Artifact Registry Repository
```bash
gcloud artifacts repositories create data-portal \
  --repository-format=docker \
  --location=me-central1 \
  --description="Data Portal Docker images"
```

### 3. Create Service Account for GitHub Actions
```bash
# Create the service account
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions Deploy"

SA=github-actions@uniapply-486919.iam.gserviceaccount.com

# Grant required roles
gcloud projects add-iam-policy-binding uniapply-486919 \
  --member="serviceAccount:$SA" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding uniapply-486919 \
  --member="serviceAccount:$SA" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding uniapply-486919 \
  --member="serviceAccount:$SA" \
  --role="roles/iam.serviceAccountUser"

# Generate and download the JSON key
gcloud iam service-accounts keys create gha-key.json \
  --iam-account=$SA
```

## GitHub Secrets Setup

Go to **GitHub repo → Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|--------|-------|
| `GCP_SA_KEY` | Contents of `gha-key.json` (the full JSON) |
| `DATABASE_URL` | `postgresql://dataportal:PASSWORD@34.18.45.84:5432/data_portal` |
| `SECRET_KEY` | Your JWT secret (long random string) |
| `ALLOWED_ORIGINS` | `https://data-portal-frontend-HASH-ew.a.run.app` (update after first deploy) |
| `ANTHROPIC_API_KEY` | Your Anthropic key |
| `GEMINI_API_KEY` | Your Gemini key |
| `OPENAI_API_KEY` | Your OpenAI key (optional) |
| `FIRECRAWL_VM_IP` | External IP of Firecrawl VM |
| `BACKEND_URL` | `https://data-portal-backend-HASH-ew.a.run.app` (update after first deploy) |

> **Note:** After the first deploy, Cloud Run will give you the service URLs.
> Update `BACKEND_URL` and `ALLOWED_ORIGINS` with the real URLs, then push again.

## First Deploy (Manual Trigger)

To trigger the first deploy for both services, make a small change to both
`backend/` and `frontend/` in one commit, or manually deploy once via CLI:

```bash
# Backend
gcloud run deploy data-portal-backend \
  --image me-central1-docker.pkg.dev/uniapply-486919/data-portal/backend:latest \
  --region me-central1 \
  --allow-unauthenticated

# Frontend
gcloud run deploy data-portal-frontend \
  --image me-central1-docker.pkg.dev/uniapply-486919/data-portal/frontend:latest \
  --region me-central1 \
  --allow-unauthenticated
```

## How CI/CD Works

```
Push to main
    │
    ├─ backend/** changed?  → Build & deploy data-portal-backend
    │
    └─ frontend/** changed? → Build & deploy data-portal-frontend
```

Both jobs run in parallel if both parts changed. If only one changed, only
that service is rebuilt and redeployed — saving time and cost.

## Delete the key file
```bash
rm gha-key.json
```
