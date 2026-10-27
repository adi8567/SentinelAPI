#!/usr/bin/env python3
"""SentinelAPI Ingestion, Inventory & Baseline Learning CLI Tool.

Enables batch ingestion of real API traffic log files, automated asset discovery,
statistical baseline training, and metrics verification.
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
from backend.app.services.baseline.batch_learner import batch_baseline_learner
from backend.app.services.detection.engine import anomaly_engine
from backend.app.services.ingestion.pipeline import ingestion_pipeline
from backend.app.services.inventory.inventory_service import inventory_service
from backend.app.services.policy.actions.ban_manager import ip_ban_manager
from backend.app.services.policy.actions.quarantine_manager import quarantine_manager
from backend.app.services.policy.actions.siem_forwarder import siem_forwarder
from backend.app.services.policy.actions.webhook_dispatcher import webhook_dispatcher
from backend.app.services.policy.engine import policy_engine
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
    parser = argparse.ArgumentParser(description="SentinelAPI Real Data Ingestion & Learning Runner")
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
        f"[bold green]SentinelAPI Traffic Ingestion & Learning Engine[/bold green]\n"
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

    # 1. Verification Table
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

    # 2. Discovered API Inventory Table
    discovered_endpoints = inventory_service.list_endpoints()
    inv_table = Table(title=f"Discovered API Inventory ({len(discovered_endpoints)} Unique Endpoints)")
    inv_table.add_column("Method", style="green")
    inv_table.add_column("Path Template", style="blue")
    inv_table.add_column("Risk", style="bold")
    inv_table.add_column("Calls", style="yellow")
    inv_table.add_column("Auth?", style="cyan")
    inv_table.add_column("Parameters", style="magenta")

    risk_colors = {
        "low": "green",
        "medium": "yellow",
        "high": "red",
        "critical": "bold red on white",
    }

    for ep in discovered_endpoints[:15]:
        r_color = risk_colors.get(ep.risk_level.value, "white")
        params_str = ", ".join(ep.parameters.keys()) if ep.parameters else "-"
        auth_str = "Yes (" + ", ".join(ep.auth_types_observed) + ")" if ep.is_authenticated else "No"
        inv_table.add_row(
            ep.http_method,
            ep.path_template,
            f"[{r_color}]{ep.risk_level.value.upper()}[/{r_color}]",
            str(ep.call_count),
            auth_str,
            params_str,
        )

    console.print(inv_table)

    # 3. Train and Display Statistical Baselines
    console.print("[cyan]Recomputing batch statistical baselines over all historical traffic...[/cyan]")
    base_res = await batch_baseline_learner.compute_all_baselines()
    console.print(f"[green]Learned baselines for {base_res.endpoints_computed} endpoints across {base_res.total_events_analyzed} real events in {base_res.execution_time_ms:.2f}ms.[/green]\n")

    base_table = Table(title="Learned Endpoint Statistical Baselines")
    base_table.add_column("Endpoint ID", style="cyan")
    base_table.add_column("Sample Size", style="yellow")
    base_table.add_column("p50 Lat (ms)", style="green")
    base_table.add_column("p90 Lat (ms)", style="blue")
    base_table.add_column("p95 Lat (ms)", style="magenta")
    base_table.add_column("Mean ± Std (ms)", style="cyan")
    base_table.add_column("Status Distribution", style="white")

    for b in batch_baseline_learner.get_all_endpoint_baselines()[:12]:
        status_str = ", ".join(f"{k}:{int(v*100)}%" for k, v in b.status_code_distribution.items())
        base_table.add_row(
            b.endpoint_id[:10] + "...",
            str(b.sample_size),
            f"{b.latency_p50:.1f}",
            f"{b.latency_p90:.1f}",
            f"{b.latency_p95:.1f}",
            f"{b.latency_mean:.1f} ± {b.latency_std:.1f}",
            status_str,
        )

    console.print(base_table)

    # 4. Train ML Models (Isolation Forest & Markov Chains)
    console.print("\n[cyan]Retraining ML Outlier & Markov Sequence models on real ingested traffic...[/cyan]")
    ml_res = await anomaly_engine.retrain_models()
    console.print(
        f"[green]Models ({', '.join(ml_res.models_retrained)}) retrained successfully "
        f"across {ml_res.training_sample_size} events in {ml_res.training_duration_ms:.2f}ms "
        f"[{ml_res.new_version}].[/green]\n"
    )

    # 5. Display Detected Real-Time Anomalies & Threats
    detected_anomalies = anomaly_engine.list_anomalies()
    anom_table = Table(title=f"Detected Anomalies & Threats ({len(detected_anomalies)} Flagged Events)")
    anom_table.add_column("Severity", style="bold")
    anom_table.add_column("Risk", style="yellow")
    anom_table.add_column("Method", style="green")
    anom_table.add_column("Path", style="blue")
    anom_table.add_column("Client IP", style="cyan")
    anom_table.add_column("Primary Detector", style="magenta")
    anom_table.add_column("Explainable Diagnostics", style="white")

    sev_colors = {
        "critical": "bold red on white",
        "high": "red",
        "medium": "yellow",
        "low": "cyan",
        "info": "white",
    }

    for a in detected_anomalies[:15]:
        s_color = sev_colors.get(a.severity.value, "white")
        diag_str = " | ".join(a.contributing_factors) if a.contributing_factors else "Multivariate anomaly"
        anom_table.add_row(
            f"[{s_color}]{a.severity.value.upper()}[/{s_color}]",
            f"{a.risk_score:.1f}",
            a.http_method,
            a.path,
            a.client_ip,
            a.primary_detector,
            diag_str[:110] + ("..." if len(diag_str) > 110 else ""),
        )

    console.print(anom_table)

    # Anomaly Stats breakdown
    anom_stats = anomaly_engine.get_stats()
    stats_panel = Panel.fit(
        f"[bold]Total Anomalies:[/bold] {anom_stats['total_anomalies']} | "
        f"[bold red]Critical:[/bold red] {anom_stats['severity_breakdown'].get('critical', 0)} | "
        f"[red]High:[/red] {anom_stats['severity_breakdown'].get('high', 0)} | "
        f"[yellow]Medium:[/yellow] {anom_stats['severity_breakdown'].get('medium', 0)} | "
        f"[green]Low/Info:[/green] {anom_stats['severity_breakdown'].get('low', 0) + anom_stats['severity_breakdown'].get('info', 0)}\n"
        f"[cyan]Risk Score Distribution:[/cyan] {anom_stats['risk_score_distribution']}",
        title="Real-Time Threat Detection Summary"
    )
    console.print(stats_panel)

    # 6. Adaptive Response & Closed-Loop Policy Enforcement
    policy_rules = await policy_engine.get_rules()
    pol_table = Table(title=f"Active Security Policies ({len(policy_rules)} Declarative Rules)")
    pol_table.add_column("Priority", style="yellow")
    pol_table.add_column("Policy ID", style="cyan")
    pol_table.add_column("Name", style="bold")
    pol_table.add_column("Action", style="magenta")
    pol_table.add_column("Conditions Summary", style="white")

    action_colors = {
        "block": "bold red on white",
        "throttle": "bold yellow",
        "challenge": "bold cyan",
        "quarantine": "bold magenta",
        "allow": "green",
    }

    for r in policy_rules:
        a_color = action_colors.get(r.action.value, "white")
        conds = []
        if r.conditions.endpoint_pattern:
            conds.append(f"Path: {r.conditions.endpoint_pattern}")
        if r.conditions.attack_types:
            conds.append(f"Attacks: {','.join(r.conditions.attack_types)}")
        if r.conditions.min_risk_score is not None:
            conds.append(f"MinScore: {r.conditions.min_risk_score}")
        if r.conditions.severities:
            conds.append(f"Sevs: {','.join(s.value for s in r.conditions.severities)}")
        if r.conditions.max_client_reputation is not None:
            conds.append(f"MaxRep: {r.conditions.max_client_reputation}")
        cond_str = " | ".join(conds) if conds else "Match All"

        pol_table.add_row(
            str(r.priority),
            r.policy_id,
            r.name,
            f"[{a_color}]{r.action.value.upper()}[/{a_color}]",
            cond_str,
        )

    console.print(pol_table)

    # Decisions Audit Table
    decisions = await policy_engine.get_decisions(limit=15)
    dec_table = Table(title=f"Automated Policy Enforcement Decisions ({len(decisions)} Recent Actions)")
    dec_table.add_column("Action", style="bold")
    dec_table.add_column("Client IP", style="cyan")
    dec_table.add_column("Endpoint", style="blue")
    dec_table.add_column("Matched Policy", style="yellow")
    dec_table.add_column("Reason / Action Details", style="white")

    for d in decisions:
        a_color = action_colors.get(d.action_taken.value, "white")
        details = ", ".join(f"{k}={v}" for k, v in d.action_details.items() if k not in ["action"])
        dec_table.add_row(
            f"[{a_color}]{d.action_taken.value.upper()}[/{a_color}]",
            d.client_ip,
            d.endpoint,
            d.matched_policy_name or d.matched_policy_id or "default",
            f"{d.reason} [{details}]" if details else d.reason,
        )

    console.print(dec_table)

    # Policy Stats & Action Summary
    pol_stats = await policy_engine.get_stats()
    bans = await ip_ban_manager.list_active_bans()
    quarantined = await quarantine_manager.list_active()
    siem_stats = siem_forwarder.get_stats()

    pol_summary = Panel.fit(
        f"[bold]Total Decisions Evaluated:[/bold] {pol_stats.total_decisions_evaluated} | "
        f"[bold red]Blocks:[/bold red] {pol_stats.actions_breakdown.get('block', 0)} | "
        f"[bold yellow]Throttles:[/bold yellow] {pol_stats.actions_breakdown.get('throttle', 0)} | "
        f"[bold cyan]Challenges:[/bold cyan] {pol_stats.actions_breakdown.get('challenge', 0)} | "
        f"[bold magenta]Quarantines:[/bold magenta] {pol_stats.actions_breakdown.get('quarantine', 0)} | "
        f"[green]Allows:[/green] {pol_stats.actions_breakdown.get('allow', 0)}\n"
        f"[bold red]Active IP Bans:[/bold red] {len(bans)} ({', '.join(b.ip for b in bans) if bans else 'None'})\n"
        f"[bold magenta]Active Quarantines:[/bold magenta] {len(quarantined)} ({', '.join(q.client_ip for q in quarantined) if quarantined else 'None'})\n"
        f"[cyan]SIEM CEF Records Emitted:[/cyan] {siem_stats['total_siem_events_forwarded']} | "
        f"[blue]Webhooks Dispatched:[/blue] {pol_stats.total_webhooks_dispatched}",
        title="Adaptive Protection & Action Summary"
    )
    console.print(pol_summary)

    await stream_producer.stop()
    await storage.close()
    console.print("\n[bold green]SentinelAPI Phase 4 verification completed successfully![/bold green]")


if __name__ == "__main__":
    asyncio.run(run_cli())
