"""
Prometheus-backed implementation of the leanMetrics catalog.

The vendor-neutral metric catalog lives in
lean_spec.subspecs.observability.metric_specs.
This module materializes it into prometheus_client objects and exposes them
through a typed registry singleton.

This module uses the null object pattern for zero-cost metrics before
initialization. Every metric attribute starts as a silent no-op stub.
After initialization, stubs are replaced with real Prometheus objects.

This design gives consumers a stable API at import time.
No "is metrics enabled?" checks are needed anywhere in the codebase.
Code that records metrics works identically whether the Prometheus
subsystem is active or not.
"""

from __future__ import annotations

import time

from prometheus_client import (
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from lean_spec.subspecs.observability.metric_specs import ALL_METRIC_SPECS, MetricSpec


class _NoOpMetric:
    """
    Null object that absorbs all metric operations without side effects.

    This stub mirrors the subset of the Prometheus metric interface that
    consumers actually use:

    - Gauge operations: set, inc
    - Histogram operations: observe
    - Label selection: labels (returns another no-op for chaining)

    A single shared instance serves all uninitialized metric attributes.
    This avoids allocating one stub per metric and keeps memory overhead
    near zero.
    """

    def set(self, value: float) -> None:  # noqa: ARG002
        """Accept and discard a gauge value."""

    def inc(self, amount: float = 1) -> None:  # noqa: ARG002
        """Accept and discard a counter increment."""

    def observe(self, amount: float) -> None:  # noqa: ARG002
        """Accept and discard a histogram observation."""

    def labels(self, **kwargs: str) -> _NoOpMetric:  # noqa: ARG002
        """
        Return self to support chained label selection.

        Prometheus metrics with labels require a selection step before
        recording. Returning self allows the full chain to complete
        silently.
        """
        return self


_NOOP = _NoOpMetric()
"""Shared no-op instance used by all uninitialized metric attributes."""


def _build(spec: MetricSpec, registry: CollectorRegistry) -> Counter | Gauge | Histogram:
    """Materialize a MetricSpec into the matching Prometheus client object."""
    labelnames = list(spec.labels)
    if spec.kind == "histogram":
        assert spec.buckets is not None, f"Histogram {spec.name} missing buckets"
        return Histogram(
            spec.name, spec.description, labelnames, buckets=spec.buckets, registry=registry
        )
    if spec.kind == "counter":
        return Counter(spec.name, spec.description, labelnames, registry=registry)
    return Gauge(spec.name, spec.description, labelnames, registry=registry)


class MetricsRegistry:
    """
    Central holder for all Prometheus metrics in a lean node.

    Attributes start as no-op stubs and become real Prometheus objects
    after initialization. This two-phase lifecycle means:

    - Importing the module is always safe and cheap.
    - Recording metrics works at any point in the node lifetime.
    - No conditional "is metrics ready?" logic pollutes call sites.

    A single module-level instance acts as the singleton.
    Consumers import that instance and use qualified attribute access.
    """

    _initialized: bool = False

    # Node info
    lean_node_info: Gauge | _NoOpMetric = _NOOP
    """Labeled gauge exposing node name and version. Always set to 1."""
    lean_node_start_time_seconds: Gauge | _NoOpMetric = _NOOP
    """Unix timestamp recorded once at node startup."""

    # Fork choice
    lean_head_slot: Gauge | _NoOpMetric = _NOOP
    """Slot of the current chain head selected by fork choice."""
    lean_current_slot: Gauge | _NoOpMetric = _NOOP
    """Wall-clock slot derived from genesis time and the slot interval."""
    lean_safe_target_slot: Gauge | _NoOpMetric = _NOOP
    """Slot of the highest target that has been deemed safe."""
    lean_fork_choice_block_processing_time_seconds: Histogram | _NoOpMetric = _NOOP
    """Latency of integrating a new block into the fork choice store."""
    lean_attestations_valid_total: Counter | _NoOpMetric = _NOOP
    """Running count of attestations that passed all validation checks."""
    lean_attestations_invalid_total: Counter | _NoOpMetric = _NOOP
    """Running count of attestations rejected during validation."""
    lean_attestation_validation_time_seconds: Histogram | _NoOpMetric = _NOOP
    """Latency of a single attestation validation pass."""
    lean_fork_choice_reorgs_total: Counter | _NoOpMetric = _NOOP
    """Running count of chain head reorganizations."""
    lean_fork_choice_reorg_depth: Histogram | _NoOpMetric = _NOOP
    """Number of blocks rolled back during each reorg event."""

    # State transition
    lean_latest_justified_slot: Gauge | _NoOpMetric = _NOOP
    """Slot of the most recently justified checkpoint."""
    lean_latest_finalized_slot: Gauge | _NoOpMetric = _NOOP
    """Slot of the most recently finalized checkpoint."""
    lean_state_transition_time_seconds: Histogram | _NoOpMetric = _NOOP
    """Latency of applying a full state transition for one slot."""

    # Validator
    lean_validators_count: Gauge | _NoOpMetric = _NOOP
    """Number of validator keys managed by this node."""

    # Network
    lean_connected_peers: Gauge | _NoOpMetric = _NOOP
    """Current number of active peer connections."""

    def init(
        self,
        name: str = "leanspec-node",
        version: str = "0.0.1",
        registry: CollectorRegistry | None = None,
    ) -> None:
        """
        Replace all no-op stubs with real Prometheus metric objects.

        Iterates the vendor-neutral catalog and constructs one Prometheus
        object per spec, then assigns each to the matching typed attribute.
        Two node-info metrics receive their initial values here:

        - lean_node_info is set to 1 with name and version labels.
        - lean_node_start_time_seconds records the wall-clock startup time.

        Call once at node startup. The method is idempotent.
        Repeated calls after the first are silently ignored.
        This prevents double-registration errors in Prometheus.

        Args:
            name: Human-readable node name exposed in the info gauge.
            version: Node version exposed in the info gauge.
            registry: Prometheus collector registry. Falls back to the
                global default registry when not provided.
        """
        # Guard against repeated initialization.
        if self._initialized:
            return
        reg = registry or REGISTRY

        # Materialize every catalog entry and assign it to its typed attribute.
        for spec in ALL_METRIC_SPECS:
            setattr(self, spec.name, _build(spec, reg))

        # Seed the node-info gauges with their startup values.
        #
        # lean_node_info uses a constant 1 with name/version labels.
        # lean_node_start_time_seconds records when the node booted.
        self.lean_node_info.labels(name=name, version=version).set(1)
        self.lean_node_start_time_seconds.set(time.time())

        self._initialized = True

    def reset(self) -> None:
        """
        Restore all metrics to their initial no-op state.

        Intended exclusively for test teardown.
        Production code should never call this.

        Clears all instance overrides so attributes fall back to
        the class-level no-op defaults.
        """
        self.__dict__.clear()


registry = MetricsRegistry()
"""
Module-level singleton shared by all consumers.

Import this instance and use qualified attribute access
throughout the codebase.
"""


def get_metrics_output(registry: CollectorRegistry | None = None) -> bytes:
    """
    Serialize all registered metrics into Prometheus text exposition format.

    Typically called by an HTTP handler to serve the ``/metrics`` endpoint.
    The output is ready to return as a response body.

    Args:
        registry: Prometheus collector registry to export. Falls back to
            the global default registry when not provided.

    Returns:
        UTF-8 encoded bytes in Prometheus text exposition format.
    """
    reg = registry or REGISTRY
    return generate_latest(reg)
