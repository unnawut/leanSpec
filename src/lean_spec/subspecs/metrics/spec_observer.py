"""
Prometheus-backed implementation of SpecObserver.

Couples vendor-neutral spec events to the Prometheus client library.
Lives in the metrics subpackage because the coupling belongs on the
Prometheus side of the seam.

The spec itself never imports this module.
"""

from __future__ import annotations

from lean_spec.subspecs.metrics.registry import registry as metrics


class PrometheusObserver:
    """Forward SpecObserver callbacks to Prometheus metrics."""

    # Duration events
    def state_transition_timed(self, seconds: float) -> None:
        """Record state transition latency into its histogram."""
        metrics.lean_state_transition_time_seconds.observe(seconds)

    def on_block_timed(self, seconds: float) -> None:
        """Record fork-choice block processing latency into its histogram."""
        metrics.lean_fork_choice_block_processing_time_seconds.observe(seconds)

    def on_attestation_timed(self, seconds: float) -> None:
        """Record gossip-attestation validation latency into its histogram."""
        metrics.lean_attestation_validation_time_seconds.observe(seconds)

    # Store-state snapshots
    def head_slot_observed(self, slot: int) -> None:
        """Update the head-slot gauge."""
        metrics.lean_head_slot.set(slot)

    def safe_target_observed(self, slot: int) -> None:
        """Update the safe-target-slot gauge."""
        metrics.lean_safe_target_slot.set(slot)

    def justified_slot_observed(self, slot: int) -> None:
        """Update the latest-justified-slot gauge."""
        metrics.lean_latest_justified_slot.set(slot)

    def finalized_slot_observed(self, slot: int) -> None:
        """Update the latest-finalized-slot gauge."""
        metrics.lean_latest_finalized_slot.set(slot)

    # Node-state snapshots
    def current_slot_observed(self, slot: int) -> None:
        """Update the wall-clock slot gauge."""
        metrics.lean_current_slot.set(slot)

    def peer_count_observed(self, count: int) -> None:
        """Update the connected-peers gauge."""
        metrics.lean_connected_peers.set(count)

    def validator_count_observed(self, count: int) -> None:
        """Update the validator-count gauge."""
        metrics.lean_validators_count.set(count)

    # Discrete events
    def reorg_detected(self, depth: int) -> None:
        """Increment the reorg counter and record the depth."""
        metrics.lean_fork_choice_reorgs_total.inc()
        metrics.lean_fork_choice_reorg_depth.observe(depth)

    def attestation_validated(self, source: str) -> None:
        """Increment the valid-attestation counter labeled by source."""
        metrics.lean_attestations_valid_total.labels(source=source).inc()

    def attestation_rejected(self, source: str) -> None:
        """Increment the invalid-attestation counter labeled by source."""
        metrics.lean_attestations_invalid_total.labels(source=source).inc()
