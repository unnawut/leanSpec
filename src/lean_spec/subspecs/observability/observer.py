"""
SpecObserver Protocol and its module-level singleton.

Hook Points

The observer is called from spec code at a small set of well-defined points.
Each hook corresponds to a phenomenon whose measurement is intrinsic to the
function being observed, not to any particular caller.

Contract

Observers must not raise.
A hook fires during a consensus-critical code path.
Exceptions propagate and abort the operation.
Clients are expected to swallow internal errors in their observer
implementations (for example, a Prometheus backend outage).
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Protocol


class SpecObserver(Protocol):
    """
    Telemetry hooks invoked at spec-level event points.

    Return values are ignored.
    Every method is side-effect-only.

    Categories

    - Durations: state_transition_timed, on_block_timed, on_attestation_timed.
      Emitted by the spec functions that execute them.
    - Store-state snapshots: head_slot_observed, safe_target_observed,
      justified_slot_observed, finalized_slot_observed.
      Emitted by callers after a store-mutating operation and periodically
      by the node loop.
    - Node-state snapshots: current_slot_observed, peer_count_observed,
      validator_count_observed. Emitted by the node loop.
    - Discrete events: reorg_detected, attestation_validated,
      attestation_rejected. Emitted by callers when classifying outcomes.
    """

    # Duration events (histograms)
    def state_transition_timed(self, seconds: float) -> None:
        """Report the wall time of a state transition."""

    def on_block_timed(self, seconds: float) -> None:
        """Report the wall time of processing a block into the fork-choice store."""

    def on_attestation_timed(self, seconds: float) -> None:
        """Report the wall time of validating and integrating a gossip attestation."""

    # Store-state snapshots (gauges)
    def head_slot_observed(self, slot: int) -> None:
        """Report the slot of the current canonical head."""

    def safe_target_observed(self, slot: int) -> None:
        """Report the slot of the current safe target."""

    def justified_slot_observed(self, slot: int) -> None:
        """Report the slot of the latest justified checkpoint."""

    def finalized_slot_observed(self, slot: int) -> None:
        """Report the slot of the latest finalized checkpoint."""

    # Node-state snapshots (gauges)
    def current_slot_observed(self, slot: int) -> None:
        """Report the wall-clock slot."""

    def peer_count_observed(self, count: int) -> None:
        """Report the number of active peer connections."""

    def validator_count_observed(self, count: int) -> None:
        """Report the number of validators managed by this node."""

    # Discrete events (counters / event-driven histograms)
    def reorg_detected(self, depth: int) -> None:
        """Report a fork-choice head change with its depth in blocks."""

    def attestation_validated(self, source: str) -> None:
        """Report a successful attestation validation, labeled by source."""

    def attestation_rejected(self, source: str) -> None:
        """Report a rejected attestation, labeled by source."""


class NullObserver:
    """
    Default observer that discards every event.

    A single instance serves every unregistered consumer.
    No allocations per call.
    """

    def state_transition_timed(self, seconds: float) -> None:  # noqa: ARG002
        """Accept and discard."""

    def on_block_timed(self, seconds: float) -> None:  # noqa: ARG002
        """Accept and discard."""

    def on_attestation_timed(self, seconds: float) -> None:  # noqa: ARG002
        """Accept and discard."""

    def head_slot_observed(self, slot: int) -> None:  # noqa: ARG002
        """Accept and discard."""

    def safe_target_observed(self, slot: int) -> None:  # noqa: ARG002
        """Accept and discard."""

    def justified_slot_observed(self, slot: int) -> None:  # noqa: ARG002
        """Accept and discard."""

    def finalized_slot_observed(self, slot: int) -> None:  # noqa: ARG002
        """Accept and discard."""

    def current_slot_observed(self, slot: int) -> None:  # noqa: ARG002
        """Accept and discard."""

    def peer_count_observed(self, count: int) -> None:  # noqa: ARG002
        """Accept and discard."""

    def validator_count_observed(self, count: int) -> None:  # noqa: ARG002
        """Accept and discard."""

    def reorg_detected(self, depth: int) -> None:  # noqa: ARG002
        """Accept and discard."""

    def attestation_validated(self, source: str) -> None:  # noqa: ARG002
        """Accept and discard."""

    def attestation_rejected(self, source: str) -> None:  # noqa: ARG002
        """Accept and discard."""


_observer: SpecObserver = NullObserver()
"""
Process-wide observer singleton.

Starts as a NullObserver so spec imports are side-effect-free.
Replaced by the client at startup via set_observer.
"""


def set_observer(observer: SpecObserver) -> None:
    """
    Register the global observer.

    Call once at client startup after any backend initialization
    (for example, after metrics.init in the Prometheus case).
    Repeat calls replace the previous observer.
    """
    global _observer
    _observer = observer


def get_observer() -> SpecObserver:
    """
    Return the currently registered observer.

    Spec code calls this to publish events.
    When no observer has been registered the returned value is a NullObserver.
    """
    return _observer


@contextmanager
def observe_state_transition() -> Iterator[None]:
    """
    Time the wrapped state transition and publish the elapsed duration.

    Spec code wraps the body of a state transition in this block instead
    of calling a stopwatch primitive directly. On clean exit the elapsed
    wall time is published through the observer singleton.

    Semantics

    - Publishes state_transition_timed only when the body returns normally.
    - If the body raises, no event is emitted and the exception propagates.

    Other-language ports

    This helper is Python sugar.
    The portable contract is the state_transition_timed hook on SpecObserver.
    Clients in other languages produce the same event through whatever
    scoped-timer idiom is natural in their language (RAII, defer, etc.).
    """
    start = time.perf_counter()
    yield
    _observer.state_transition_timed(time.perf_counter() - start)


@contextmanager
def observe_on_block() -> Iterator[None]:
    """
    Time the wrapped fork-choice block integration and publish the duration.

    Semantics mirror observe_state_transition: publishes only on clean exit,
    propagates exceptions without emitting an event.
    """
    start = time.perf_counter()
    yield
    _observer.on_block_timed(time.perf_counter() - start)


@contextmanager
def observe_on_attestation() -> Iterator[None]:
    """
    Time the wrapped gossip-attestation validation and publish the duration.

    Semantics mirror observe_state_transition: publishes only on clean exit,
    propagates exceptions without emitting an event. The caller remains
    responsible for classifying the outcome (valid vs invalid counters),
    because that classification is a caller-side concern.
    """
    start = time.perf_counter()
    yield
    _observer.on_attestation_timed(time.perf_counter() - start)
