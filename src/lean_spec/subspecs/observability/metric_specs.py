"""
Vendor-neutral catalog of consensus-node metrics.

Names, descriptions, types, units, labels, and recommended bucket boundaries
follow the leanMetrics spec:
https://github.com/leanEthereum/leanMetrics/blob/main/metrics.md

These specs describe what a Lean consensus client should expose. They do not
depend on any particular telemetry backend. Prometheus, OpenTelemetry, or any
other adapter consumes this catalog and renders concrete metric objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MetricKind = Literal["counter", "gauge", "histogram"]
"""The three metric primitives every backend supports."""


# Categories grouping related metrics. Match the leanMetrics spec sections.
NODE_INFO = "node_info"
FORK_CHOICE = "fork_choice"
STATE_TRANSITION = "state_transition"
VALIDATOR = "validator"
NETWORK = "network"


@dataclass(frozen=True, slots=True)
class MetricSpec:
    """
    Backend-agnostic description of a single metric.

    Attributes:
    - name: Metric identifier as it appears in the exposition format.
    - kind: Metric primitive — counter, gauge, or histogram.
    - description: Human-readable purpose statement.
    - category: Section of the leanMetrics spec this metric belongs to.
    - unit: Measurement unit (for example "seconds", "blocks"). None for
      counts and dimensionless gauges.
    - labels: Label names attached at observation time. Empty for
      label-less metrics.
    - buckets: Recommended histogram bucket upper bounds in spec units.
      Required for histograms, must be None for counters and gauges.
    """

    name: str
    kind: MetricKind
    description: str
    category: str
    unit: str | None = None
    labels: tuple[str, ...] = ()
    buckets: tuple[float, ...] | None = None


# Node info
LEAN_NODE_INFO = MetricSpec(
    name="lean_node_info",
    kind="gauge",
    description="Node information (always 1).",
    category=NODE_INFO,
    labels=("name", "version"),
)
LEAN_NODE_START_TIME_SECONDS = MetricSpec(
    name="lean_node_start_time_seconds",
    kind="gauge",
    description="Start timestamp.",
    category=NODE_INFO,
    unit="seconds",
)


# Fork choice
LEAN_HEAD_SLOT = MetricSpec(
    name="lean_head_slot",
    kind="gauge",
    description="Latest slot of the lean chain.",
    category=FORK_CHOICE,
)
LEAN_CURRENT_SLOT = MetricSpec(
    name="lean_current_slot",
    kind="gauge",
    description="Current slot of the lean chain.",
    category=FORK_CHOICE,
)
LEAN_SAFE_TARGET_SLOT = MetricSpec(
    name="lean_safe_target_slot",
    kind="gauge",
    description="Safe target slot.",
    category=FORK_CHOICE,
)
LEAN_FORK_CHOICE_BLOCK_PROCESSING_TIME_SECONDS = MetricSpec(
    name="lean_fork_choice_block_processing_time_seconds",
    kind="histogram",
    description="Time taken to process block in fork choice.",
    category=FORK_CHOICE,
    unit="seconds",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 1, 1.25, 1.5, 2, 4),
)
LEAN_ATTESTATIONS_VALID_TOTAL = MetricSpec(
    name="lean_attestations_valid_total",
    kind="counter",
    description="Total number of valid attestations.",
    category=FORK_CHOICE,
    labels=("source",),
)
LEAN_ATTESTATIONS_INVALID_TOTAL = MetricSpec(
    name="lean_attestations_invalid_total",
    kind="counter",
    description="Total number of invalid attestations.",
    category=FORK_CHOICE,
    labels=("source",),
)
LEAN_ATTESTATION_VALIDATION_TIME_SECONDS = MetricSpec(
    name="lean_attestation_validation_time_seconds",
    kind="histogram",
    description="Time taken to validate attestation.",
    category=FORK_CHOICE,
    unit="seconds",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 1),
)
LEAN_FORK_CHOICE_REORGS_TOTAL = MetricSpec(
    name="lean_fork_choice_reorgs_total",
    kind="counter",
    description="Total number of fork choice reorgs.",
    category=FORK_CHOICE,
)
LEAN_FORK_CHOICE_REORG_DEPTH = MetricSpec(
    name="lean_fork_choice_reorg_depth",
    kind="histogram",
    description="Depth of fork choice reorgs (in blocks).",
    category=FORK_CHOICE,
    unit="blocks",
    buckets=(1, 2, 3, 5, 7, 10, 20, 30, 50, 100),
)


# State transition
LEAN_LATEST_JUSTIFIED_SLOT = MetricSpec(
    name="lean_latest_justified_slot",
    kind="gauge",
    description="Latest justified slot.",
    category=STATE_TRANSITION,
)
LEAN_LATEST_FINALIZED_SLOT = MetricSpec(
    name="lean_latest_finalized_slot",
    kind="gauge",
    description="Latest finalized slot.",
    category=STATE_TRANSITION,
)
LEAN_STATE_TRANSITION_TIME_SECONDS = MetricSpec(
    name="lean_state_transition_time_seconds",
    kind="histogram",
    description="Time to process state transition.",
    category=STATE_TRANSITION,
    unit="seconds",
    buckets=(0.25, 0.5, 0.75, 1, 1.25, 1.5, 2, 2.5, 3, 4),
)


# Validator
LEAN_VALIDATORS_COUNT = MetricSpec(
    name="lean_validators_count",
    kind="gauge",
    description="Number of validators managed by a node.",
    category=VALIDATOR,
)


# Network
LEAN_CONNECTED_PEERS = MetricSpec(
    name="lean_connected_peers",
    kind="gauge",
    description="Number of connected peers.",
    category=NETWORK,
)


ALL_METRIC_SPECS: tuple[MetricSpec, ...] = (
    LEAN_NODE_INFO,
    LEAN_NODE_START_TIME_SECONDS,
    LEAN_HEAD_SLOT,
    LEAN_CURRENT_SLOT,
    LEAN_SAFE_TARGET_SLOT,
    LEAN_FORK_CHOICE_BLOCK_PROCESSING_TIME_SECONDS,
    LEAN_ATTESTATIONS_VALID_TOTAL,
    LEAN_ATTESTATIONS_INVALID_TOTAL,
    LEAN_ATTESTATION_VALIDATION_TIME_SECONDS,
    LEAN_FORK_CHOICE_REORGS_TOTAL,
    LEAN_FORK_CHOICE_REORG_DEPTH,
    LEAN_LATEST_JUSTIFIED_SLOT,
    LEAN_LATEST_FINALIZED_SLOT,
    LEAN_STATE_TRANSITION_TIME_SECONDS,
    LEAN_VALIDATORS_COUNT,
    LEAN_CONNECTED_PEERS,
)
"""All metrics a Lean consensus node exposes. Iteration order matches the
leanMetrics spec section order."""
