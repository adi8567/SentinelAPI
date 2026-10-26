# SentinelAPI Machine Learning & Behavioral Analytics

This directory houses the statistical baseline learning models (Phase 2) and real-time anomaly detection engines (Phase 3).

## Planned Modules
- `baselines/`: Request rates, latency quantile distributions, status code distributions, time-of-day seasonality models.
- `detectors/`:
  - Statistical (z-score, MAD, percentile-based)
  - Isolation Forest & Local Outlier Factor (LOF)
  - Sequence anomaly detection (Markov chains / transitions)
  - Contextual risk scoring (identity + endpoint + time + volume)
- `pipeline/`: Real-time streaming scoring pipeline consuming normalized Kafka events.
