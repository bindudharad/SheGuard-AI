# SheGuard API Test Report

**Generated:** 2026-08-07 · Tested against live backend at `http://127.0.0.1:8000` with a valid QA JWT.

---

## 1. Authentication

| Test | Result | Notes |
|---|---|---|
| `/register` (short password) | 422 | Validation works |
| `/register` duplicate phone | 409 | Correct |
| `/login` wrong password | 401 | Correct |
| `/login` correct creds (`9876543201`/`Test@12345`) | 200 | token issued |
| `/profile/55` with own token | 200 | OK |
| `/profile/1` (foreign user) | 403 | **Authorization enforced** ✅ |
| No token / empty token / garbage token | 401 | Correct |

> ⚠️ **Blocking config bug:** with the stock `.env` value `SHEGUARD_JWT_SECRET=replace-with-a-long-random-secret`,
> `app/services/security.py` rejects it and **register/login return 500**. The backend was verified using an
> environment override: `SHEGUARD_JWT_SECRET=qa-verification-only-secret-9f8e7d6c5b4a`.
> **Root cause:** placeholder secret in `.env` + validation in `security.py`.

## 2. Endpoint results (32-check suite)

All against authenticated session unless noted.

| Endpoint | Method | Expected | Actual | Status |
|---|---|---|---|---|
| `/` | GET | 200 | 200 | ✅ |
| `/health/gpu` | GET | 200 | 200 | ✅ |
| `/system/local-network` | GET | 200 | 200 | ✅ |
| `/incidents` | GET | 200 | 200 | ✅ |
| `/incidents/latest` | GET | 200 | 200 | ✅ |
| `/incident/history/55` | GET | 200 | 200 | ✅ |
| `/incident/live` | GET | 200 | 200 | ✅ |
| `/incident/search?q=fall` | GET | 200 | 200 | ✅ |
| `/incidents/{id}` | GET | 200 | 200 | ✅ |
| `/profile/{id}` | GET | 200 / 403 | 200 / 403 | ✅ |
| `/evidence/{id}` | GET | 200 / 403 | 403 (foreign) | ✅ |
| `/secure/evidence/{id}` | GET | 200 | 200 | ✅ |
| `/contacts/55`, `/contacts/add` | GET/POST | 200 | 200 | ✅ |
| `/camera/list`, `/camera/register`, `/camera/health` | GET/POST | 200 | 200 | ✅ |
| `/location/update`, `/location/live/55` | POST/GET | 200 | 200 | ✅ |
| `/tracking/start`, `/tracking/update`, `/tracking/history` | POST/POST/GET | 200 | 200 | ✅ |
| `/track/{id}` page | GET | 200 | 200 | ✅ |
| `/emergency/start` | POST | 200 | 200 | ✅ |
| `/incidents/create` (JSON) | POST | 200 | 200 | ✅ |
| `/incident/create` (multipart) | POST | 200 | **500** | ❌ python-multipart missing |
| `/evidence/upload` (base64) | POST | 200 | 200 | ✅ (schema matches Flutter) |
| `/notifications/send` | POST | 200 | 200 | ✅ |
| `/health` | GET | 200 | **404** | ⚠️ no such route; health is at `/` |
| WebSockets `/ws/live`, `/ws/emergency`, `/ws/tracking` | WS | upgrade | **404** | ❌ libs missing |

## 3. Schema compatibility

- **Flutter → backend:** `/incidents/create` JSON payload (`user_id`, `incident_type`, `confidence`,
  `threat_score`, `ai_summary`, `latitude`, `longitude`, `send_alert`) matches `IncidentCreate`. ✅
- **Flutter → backend:** `/evidence/upload` (`session_id`, `evidence_type`, `filename`, `content_base64`,
  `encrypted`, `created_at`) matches `EvidenceUpload`. ✅
- **Dashboard → backend:** response mapping mismatch — see DASHBOARD_TEST_REPORT.md. ⚠️

## 4. Summary

- REST surface: **30/32 checks passed** (2 failures: multipart 500, WS 404).
- One documentation mismatch: `/health` does not exist (health is served at `/`).
- Route-registration bug: `/evidence/file` is shadowed by `/evidence/{incident_id}` and is unreachable.

**API health score: 8 / 10**
