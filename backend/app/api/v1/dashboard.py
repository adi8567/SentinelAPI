"""SentinelAPI Rich Dashboard REST Endpoints.

Provides aggregated real-data visualizations for frontend charts and dashboards.
"""

from typing import List
from fastapi import APIRouter, Query
from backend.app.api.deps import CurrentPrincipal
from backend.app.schemas.dashboard import (
    ActionsBreakdownData,
    AnomalyTimeseriesPoint,
    DashboardOverview,
    EndpointHealthMetric,
    GeoDistributionPoint,
    RiskDistributionData,
    TopEndpointAnomalies,
    TrafficTimeseriesPoint,
)
from backend.app.services.dashboard.dashboard_service import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Visualizations"])


@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
    principal: CurrentPrincipal,
) -> DashboardOverview:
    """Retrieves executive summary cards: total requests, anomaly rate, blocked attacks, latencies."""
    return await dashboard_service.get_overview()


@router.get("/traffic-timeseries", response_model=List[TrafficTimeseriesPoint])
async def get_traffic_timeseries(
    principal: CurrentPrincipal,
    limit: int = Query(60, ge=1, le=500, description="Number of time buckets"),
) -> List[TrafficTimeseriesPoint]:
    """Retrieves real-time traffic volume time-series (total, error, and anomalous requests)."""
    return await dashboard_service.get_traffic_timeseries(limit=limit)


@router.get("/anomalies-timeseries", response_model=List[AnomalyTimeseriesPoint])
async def get_anomalies_timeseries(
    principal: CurrentPrincipal,
    limit: int = Query(60, ge=1, le=500),
) -> List[AnomalyTimeseriesPoint]:
    """Retrieves anomaly count time-series grouped by severity level."""
    return await dashboard_service.get_anomalies_timeseries(limit=limit)


@router.get("/risk-distribution", response_model=RiskDistributionData)
async def get_risk_distribution(
    principal: CurrentPrincipal,
) -> RiskDistributionData:
    """Retrieves composite risk score histogram (0-20 to 80-100) and box-plot quartiles."""
    return await dashboard_service.get_risk_distribution()


@router.get("/top-endpoints", response_model=List[TopEndpointAnomalies])
async def get_top_anomalous_endpoints(
    principal: CurrentPrincipal,
    limit: int = Query(10, ge=1, le=50),
) -> List[TopEndpointAnomalies]:
    """Retrieves endpoints exhibiting the highest number of anomalies and risk ratings."""
    return await dashboard_service.get_top_anomalous_endpoints(limit=limit)


@router.get("/endpoint-health", response_model=List[EndpointHealthMetric])
async def get_endpoint_health(
    principal: CurrentPrincipal,
) -> List[EndpointHealthMetric]:
    """Retrieves endpoint health matrix with error percentages and latency metrics."""
    return await dashboard_service.get_endpoint_health_matrix()


@router.get("/geo-distribution", response_model=List[GeoDistributionPoint])
async def get_geo_distribution(
    principal: CurrentPrincipal,
) -> List[GeoDistributionPoint]:
    """Retrieves geographic client traffic distribution."""
    return await dashboard_service.get_geo_distribution()


@router.get("/actions-breakdown", response_model=ActionsBreakdownData)
async def get_actions_breakdown(
    principal: CurrentPrincipal,
) -> ActionsBreakdownData:
    """Retrieves adaptive protection enforcement distribution and active bans count."""
    return await dashboard_service.get_actions_breakdown()
