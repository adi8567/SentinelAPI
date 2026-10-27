"""SentinelAPI Production Load & Stress Testing Suite (Locust).

Simulates concurrent real-world API traffic ingestion, high-throughput metric aggregation,
and adversarial attack bursts to benchmark platform throughput (req/sec) and latency SLOs.
"""

import json
import random
from locust import HttpUser, between, task


class SentinelApiUser(HttpUser):
    wait_time = between(0.05, 0.2)  # High throughput simulation

    def on_start(self):
        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": "sentinel_adm_secret_key_prod_99",
        }

    @task(6)
    def ingest_real_benign_traffic(self):
        """Simulates rapid continuous API traffic ingestion."""
        client_ip = f"198.51.100.{random.randint(1, 254)}"
        endpoints = [
            f"/api/v1/users/{random.randint(100, 999)}",
            f"/api/v1/catalog/items/{random.randint(10, 50)}",
            "/api/v1/orders",
            "/api/v1/search?q=electronics",
            "/healthz",
        ]
        chosen_ep = random.choice(endpoints)
        log_line = f'{client_ip} - - [27/Oct/2026:10:00:00 +0000] "GET {chosen_ep} HTTP/1.1" 200 450 "-" "Mozilla/5.0"'

        payload = {
            "source_type": "auto",
            "logs": [log_line],
        }
        self.client.post("/api/v1/ingest/raw", json=payload, headers=self.headers)

    @task(1)
    def ingest_security_attack_burst(self):
        """Simulates adversarial attacks (SQL injection, path traversal) to test engine scoring."""
        attacker_ip = f"203.0.113.{random.randint(100, 250)}"
        attacks = [
            f'{attacker_ip} - - [27/Oct/2026:10:00:01 +0000] "GET /api/v1/users?id=1%27%20OR%201=1-- HTTP/1.1" 403 80 "-" "sqlmap/1.6"',
            f'{attacker_ip} - - [27/Oct/2026:10:00:02 +0000] "GET /api/v1/download?file=../../../../etc/passwd HTTP/1.1" 403 75 "-" "Nikto/2.1"',
        ]
        payload = {
            "source_type": "auto",
            "logs": [random.choice(attacks)],
        }
        self.client.post("/api/v1/ingest/raw", json=payload, headers=self.headers)

    @task(3)
    def query_dashboard_overview(self):
        """Simulates SOC analyst dashboard querying."""
        self.client.get("/api/v1/dashboard/overview", headers=self.headers)

    @task(2)
    def query_prometheus_metrics(self):
        """Simulates Prometheus scraper collecting metrics."""
        self.client.get("/metrics")
