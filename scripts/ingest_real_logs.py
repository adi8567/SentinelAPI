"""SentinelAPI Real Dataset Ingestion Utility.

Ingests real production datasets into SentinelAPI, updating inventories,
baselines, and triggering anomaly detection and adaptive policies.
"""

import asyncio
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app.schemas.events import LogSource
from backend.app.services.baseline.batch_learner import batch_baseline_learner
from backend.app.services.baseline.online_updater import online_baseline_updater
from backend.app.services.detection.engine import anomaly_engine
from backend.app.services.ingestion.auto_detector import parser_registry
from backend.app.services.inventory.inventory_service import inventory_service
from backend.app.services.policy.engine import policy_engine
from backend.app.services.storage.factory import get_storage


async def main():
    print("=" * 70)
    print(" SentinelAPI Real Dataset Ingestion Utility")
    print("=" * 70)

    data_dir = BASE_DIR / "data" / "real_datasets"
    if not data_dir.exists():
        print(f"[!] Dataset directory not found: {data_dir}")
        return

    storage = await get_storage()
    await storage.initialize()

    datasets = [
        ("nginx_access.log", LogSource.NGINX),
        ("real_api_sec_attacks.log", LogSource.NGINX),
        ("envoy_access.json", LogSource.ENVOY),
        ("aws_api_gateway.json", LogSource.AWS_APIGW),
        ("azure_apim.json", LogSource.AZURE_APIM),
        ("gcp_endpoints.json", LogSource.GCP_ENDPOINTS),
        ("kong_gateway.json", LogSource.KONG),
        ("otel_traces.json", LogSource.OPENTELEMETRY),
    ]

    total_ingested = 0
    total_anomalies = 0

    for filename, source in datasets:
        file_path = data_dir / filename
        if not file_path.exists():
            continue

        lines = [line.strip() for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        print(f"\n[+] Ingesting {len(lines)} records from {filename} ({source.value})...")

        events, errors, detected = parser_registry.parse_with_detection(lines, forced_source=source)
        if events:
            # 1. Store events in batch
            await storage.store_events(events)
            total_ingested += len(events)

            for event in events:
                # 2. Update inventory & session
                await inventory_service.process_event(event)

                # 3. Update online streaming baseline
                online_baseline_updater.observe_event(event)

                # 4. Score event
                anomaly = anomaly_engine.score_event(event)
                if anomaly:
                    total_anomalies += 1
                    await storage.store_anomaly(anomaly)
                    # 5. Evaluate policy
                    await policy_engine.evaluate(event, anomaly=anomaly)
                else:
                    await policy_engine.evaluate(event)

    # 6. Historical batch baseline recomputation
    print("\n[*] Recomputing historical statistical baselines from stored data...")
    res = await batch_baseline_learner.compute_all_baselines()
    print(f"    Baselines computed for {res.endpoints_computed} endpoints, {res.clients_computed} clients.")

    print("\n" + "=" * 70)
    print(f" Ingestion Summary: {total_ingested} events ingested, {total_anomalies} anomalies detected.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
