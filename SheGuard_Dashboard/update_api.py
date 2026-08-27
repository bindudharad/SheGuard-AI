import
sys
with open('C:/Programs/codex/SheGuard/SheGuard_Dashboard/src/services/api.js', 'r') as f:
    content = f.read()

content = content.replace(
    'import { API_BASE_URL, MEDIA_BASE_URL, API_TIMEOUT_MS } from \
../config\;',
    'import { API_BASE_URL, MEDIA_BASE_URL, API_TIMEOUT_MS, BACKEND_HEALTH_CHECK_INTERVAL_MS } from \
../config\;'
)

