"""SentinelAPI Real Dataset Ingestion Utility.

Ingests real production datasets into SentinelAPI, updating inventories,
baselines, and triggering anomaly detection and adaptive policies.
"""

import asyncio
from pathlib import Path
import sys
import httpx

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app.core.config import settings
from backend.app.schemas.events import LogSource


async def main():
    print("=" * 70)
    print(" SentinelAPI Real Dataset Ingestion Utility")
    print("=" * 70)

    data_dir = BASE_DIR / "data" / "real_datasets"
    if not data_dir.exists():
        print(f"[!] Dataset directory not found: {data_dir}")
        return

    datasets = [
        ("nginx_access.log", "nginx"),
        ("real_api_sec_attacks.log", "nginx"),
        ("envoy_access.json", "envoy"),
        ("aws_api_gateway.json", "aws_apigw"),
        ("azure_apim.json", "azure_apim"),
        ("gcp_endpoints.json", "gcp_endpoints"),
        ("kong_gateway.json", "kong"),
        ("otel_traces.json", "opentelemetry"),
    ]

    api_url = "http://127.0.0.1:8000/api/v1"
    headers = {"X-API-Key": settings.ADMIN_API_KEY}

    # Check if backend is active
    server_running = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{api_url}/health")
            if resp.status_code == 200:
                server_running = True
    except Exception:
        server_running = False

    if server_running:
        print("[*] Detected active SentinelAPI server on http://127.0.0.1:8000")
        print("[*] Ingesting datasets via HTTP Ingestion API (/api/v1/ingest/raw)...")

        total_accepted = 0
        async with httpx.AsyncClient(timeout=30.0) as client:
            for filename, source in datasets:
                file_path = data_dir / filename
                if not file_path.exists():
                    continue

                lines = [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()]
                print(f"[+] Streaming {len(lines)} records from {filename} ({source})...")

                payload = {
                    "source_type": source,
                    "logs": lines,
                    "gateway_id": f"ingest-{source}",
                }
                res = await client.post(f"{api_url}/ingest/raw", json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    accepted = data.get("accepted_count", 0)
                    total_accepted += accepted
                    print(f"    Accepted: {accepted}/{len(lines)} (Processing: {data.get('processing_time_ms', 0)}ms)")
                else:
                    print(f"    [!] Error {res.status_code}: {res.text}")

            # Trigger baseline recompute
            print("\n[*] Triggering historical baseline recomputation on running server...")
            await client.post(f"{api_url}/baseline/recompute", headers=headers)

        print("\n" + "=" * 70)
        print(f" Ingestion Complete! {total_accepted} events ingested into live server.")
        print("=" * 70)
        return

    # Fallback to direct repository access if server is offline
    print("[*] SentinelAPI server is offline. Ingesting directly into DuckDB storage...")
    from backend.app.services.baseline.batch_learner import batch_baseline_learner
    from backend.app.services.baseline.online_updater import online_baseline_updater
    from backend.app.services.detection.engine import anomaly_engine
    from backend.app.services.ingestion.auto_detector import parser_registry
    from backend.app.services.inventory.inventory_service import inventory_service
    from backend.app.services.policy.engine import policy_engine
    from backend.app.services.storage.factory import get_storage

    storage = await get_storage()
    await storage.initialize()

    total_ingested = 0
    total_anomalies = 0

    for filename, source_name in datasets:
        file_path = data_dir / filename
        if not file_path.exists():
            continue

        source = LogSource(source_name)
        lines = [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        print(f"\n[+] Ingesting {len(lines)} records from {filename} ({source.value})...")

        events, errors, detected = parser_registry.parse_with_detection(lines, forced_source=source)
        if events:
            await storage.store_events(events)
            total_ingested += len(events)

            for event in events:
                await inventory_service.process_event(event)
                online_baseline_updater.observe_event(event)
                anomaly = anomaly_engine.score_event(event)
                if anomaly:
                    total_anomalies += 1
                    await storage.store_anomaly(anomaly)
                    await policy_engine.evaluate(event, anomaly=anomaly)
                else:
                    await policy_engine.evaluate(event)

    print("\n[*] Recomputing historical statistical baselines from stored data...")
    res = await batch_baseline_learner.compute_all_baselines()
    print(f"    Baselines computed for {res.endpoints_computed} endpoints, {res.clients_computed} clients.")

    print("\n" + "=" * 70)
    print(f" Ingestion Summary: {total_ingested} events ingested, {total_anomalies} anomalies detected.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
