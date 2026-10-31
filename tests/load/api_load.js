import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: Number(__ENV.VUS),
  duration: __ENV.DURATION,
  thresholds: {
    http_req_failed: ["rate<0.01"],    // under 1% of requests fail
    http_req_duration: ["p(95)<500"],  // 95% of requests finish in 500 ms
    checks: ["rate>0.99"],             // over 99% of answers are correct
  },
};

const headers = {
  Authorization: `Bearer ${__ENV.API_TOKEN}`,
  "Content-Type": "application/json",
};

export default function () {
  const health = http.get(`${__ENV.TARGET_URL}/health`);
  check(health, { "health is 200": (r) => r.status === 200 });

  const reading = JSON.stringify({
    unit_id: `UPS-${__VU}`,
    state_of_charge: 80,
    voltage_v: 480,
    current_a: 100,
  });
  const saved = http.post(`${__ENV.TARGET_URL}/readings`, reading, { headers });
  check(saved, { "reading is saved": (r) => r.status === 201 });

  sleep(0.1);
}
