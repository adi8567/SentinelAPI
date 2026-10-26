#!/usr/bin/env python3
"""SentinelAPI Ingestion CLI Tool.

Enables batch ingestion of real API traffic log files, automated verification,
and pipeline metrics inspection.
"""

import argparse
import asyncio
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from backend.app.core.config import settings
from backend.app.schemas.events import LogSource
from backend.app.services.ingestion.pipeline import ingestion_pipeline
from backend.app.services.storage.factory import get_storage
from backend.app.services.streaming.kafka_client import stream_producer

console = Console()


async def ingest_file(file_path: Path, source_type: LogSource = LogSource.AUTO) -> bool:
    """Ingests a single file through the pipeline."""
    if not file_path.exists():
        console.print(f"[bold red]File not found:[/bold red] {file_path}")
        return False

    console.print(f"[cyan]Reading logs from:[/cyan] {file_path.name}")
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        console.print(f"[yellow]Skipping empty file:[/yellow] {file_path.name}")
        return True

    res = await ingestion_pipeline.ingest_raw_batch(
        raw_lines=lines,
        source_type=source_type,
        gateway_id=f"cli-{file_path.stem}",
        store_raw=True,
    )

    status_color = "green" if res.success and res.rejected_count == 0 else "yellow" if res.success else "red"
    console.print(
        f"[{status_color}]Result:[/{status_color}] Accepted: {res.accepted_count} | "
        f"Rejected: {res.rejected_count} | Source: {res.source_detected} | "
        f"Time: {res.processing_time_ms:.2f}ms"
    )

    if res.parse_errors:
        console.print(f"[red]Encountered {len(res.parse_errors)} parse error(s):[/red]")
        for err in res.parse_errors[:5]:
            console.print(f"  Line {err.index}: {err.error} (Snippet: {err.line_snippet})")

    return res.success


async def run_cli():
    parser = argparse.ArgumentParser(description="SentinelAPI Real Data Ingestion Runner")
    parser.add_argument("--file", "-f", type=str, help="Path to a log file to ingest")
    parser.add_argument("--all", "-a", action="store_true", help="Ingest all files in data/real_datasets/")
    parser.add_argument("--source", "-s", type=str, default="auto", help="Log format: auto, nginx, envoy, kong, aws_apigw, azure_apim, gcp_endpoints, opentelemetry")
    parser.add_argument("--verify", "-v", action="store_true", help="Verify database contents and print traffic metrics")

    args = parser.parse_args()

    # Initialize services
    storage = await get_storage()
    await storage.initialize()
    await stream_producer.start()

    console.print(Panel.fit(
        f"[bold green]SentinelAPI Traffic Ingestion Engine[/bold green]\n"
        f"Storage Engine: [bold cyan]{settings.STORAGE_BACKEND.value}[/bold cyan] | "
        f"Streaming: [bold cyan]{settings.STREAMING_BACKEND.value}[/bold cyan]",
        title="SentinelAPI v1.0"
    ))

    source_enum = LogSource(args.source) if args.source in [e.value for e in LogSource] else LogSource.AUTO

    if args.all:
        datasets_dir = BASE_DIR / "data" / "real_datasets"
        data_files = sorted(list(datasets_dir.glob("*.log")) + list(datasets_dir.glob("*.json")))
        console.print(f"[bold]Found {len(data_files)} dataset files to ingest.[/bold]\n")
        for df in data_files:
            await ingest_file(df, source_type=LogSource.AUTO)
            console.print("-" * 50)
    elif args.file:
        await ingest_file(Path(args.file), source_type=source_enum)
    elif not args.verify:
        # Default behavior: ingest all real datasets
        datasets_dir = BASE_DIR / "data" / "real_datasets"
        data_files = sorted(list(datasets_dir.glob("*.log")) + list(datasets_dir.glob("*.json")))
        console.print(f"[bold]Ingesting all {len(data_files)} real dataset files...[/bold]\n")
        for df in data_files:
            await ingest_file(df, source_type=LogSource.AUTO)
            console.print("-" * 50)

    # Verification Table
    total_events = await storage.get_total_events_count()
    metrics = await storage.get_traffic_metrics()

    stats_table = Table(title="Ingestion & Storage Verification")
    stats_table.add_column("Metric", style="cyan", no_wrap=True)
    stats_table.add_column("Value", style="magenta")

    stats_table.add_row("Total Normalized Events in DB", str(total_events))
    stats_table.add_row("Average Latency (ms)", f"{metrics.get('avg_latency_ms', 0):.2f} ms")
    stats_table.add_row("Median Latency (p50)", f"{metrics.get('p50_latency_ms', 0):.2f} ms")
    stats_table.add_row("95th Percentile Latency (p95)", f"{metrics.get('p95_latency_ms', 0):.2f} ms")
    stats_table.add_row("99th Percentile Latency (p99)", f"{metrics.get('p99_latency_ms', 0):.2f} ms")
    stats_table.add_row("Total Inbound Bytes", f"{metrics.get('total_bytes_in', 0):,} bytes")
    stats_table.add_row("Total Outbound Bytes", f"{metrics.get('total_bytes_out', 0):,} bytes")
    stats_table.add_row("Status Codes Observed", str(metrics.get("status_breakdown", {})))
    stats_table.add_row("HTTP Methods Observed", str(metrics.get("methods_breakdown", {})))

    console.print(stats_table)

    # Top endpoints table
    top_eps = metrics.get("top_endpoints", [])
    if top_eps:
        ep_table = Table(title="Top Ingested API Endpoints")
        ep_table.add_column("Method", style="green")
        ep_table.add_column("Endpoint Path", style="blue")
        ep_table.add_column("Requests", style="yellow")
        ep_table.add_column("Avg Latency (ms)", style="cyan")

        for ep in top_eps[:10]:
            ep_table.add_row(ep["method"], ep["path"], str(ep["count"]), f"{ep['avg_latency_ms']:.2f}")

        console.print(ep_table)

    await stream_producer.stop()
    await storage.close()
    console.print("\n[bold green]Ingestion pipeline run finished successfully![/bold green]")


if __name__ == "__main__":
    asyncio.run(run_cli())
