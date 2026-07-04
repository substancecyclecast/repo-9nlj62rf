/**
 * k6 Smoke Test for SnabAgent API
 *
 * Run: k6 run load_tests/k6_smoke.js
 * Env: K6_BASE_URL (default: http://localhost:8000)
 */
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE = __ENV.K6_BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.SNABAGENT_API_KEY || 'dev-only-key-change-in-prod';

export const options = {
  stages: [
    { duration: '10s', target: 5 },   // ramp-up
    { duration: '30s', target: 10 },   // hold
    { duration: '10s', target: 0 },    // ramp-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],   // 95th < 500ms
    http_req_failed: ['rate<0.05'],     // <5% errors
  },
};

const headers = {
  'Content-Type': 'application/json',
  'X-API-Key': API_KEY,
};

export default function () {
  // Health check
  const health = http.get(`${BASE}/health`);
  check(health, {
    'health 200': (r) => r.status === 200,
    'health ok': (r) => r.json().status === 'ok',
  });

  // List lots
  const lots = http.get(`${BASE}/api/v1/lots/?page=1&page_size=10`, { headers });
  check(lots, {
    'lots 200': (r) => r.status === 200,
    'lots has items': (r) => r.json().items !== undefined,
  });

  // Create lot
  const payload = JSON.stringify({
    customer_name: `k6-test-${__VU}-${__ITER}`,
    raw_request: 'Тестовая заявка k6: болты М10 100 шт',
    phase: 'pre_nmck',
  });
  const create = http.post(`${BASE}/api/v1/lots`, payload, { headers });
  check(create, {
    'create 200': (r) => r.status === 200,
    'create has id': (r) => r.json().id !== undefined,
  });

  sleep(1);
}
