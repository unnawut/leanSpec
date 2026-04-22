"""Tests for the spec observer singleton and its Prometheus adapter."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from typing import Any

import pytest
from prometheus_client import CollectorRegistry, Histogram

from lean_spec.subspecs.metrics import PrometheusObserver
from lean_spec.subspecs.metrics import registry as metrics
from lean_spec.subspecs.observability import (
    NullObserver,
    get_observer,
    observe_on_attestation,
    observe_on_block,
    observe_state_transition,
    set_observer,
)


@pytest.fixture
def fresh_registry() -> CollectorRegistry:
    """Create an isolated Prometheus registry for each test."""
    return CollectorRegistry()


@pytest.fixture(autouse=True)
def _reset_metrics() -> Iterator[None]:
    """Ensure metrics are uninitialized before and after each test."""
    metrics.reset()
    yield
    metrics.reset()


@pytest.fixture(autouse=True)
def _reset_observer() -> Iterator[None]:
    """Restore the default NullObserver between tests."""
    yield
    set_observer(NullObserver())


def _init_metrics(registry: CollectorRegistry) -> None:
    """Initialize metrics with the given isolated registry."""
    metrics.init(registry=registry)


def _get_histogram_sum(histogram: Any) -> float:
    """Read the cumulative observed sum of a Prometheus Histogram."""
    assert isinstance(histogram, Histogram)
    return histogram._sum.get()


# Each row pairs an observer hook with the Prometheus histogram it records into
# and the context manager that publishes it.
SPEC_EVENTS = [
    pytest.param(
        "state_transition_timed",
        "lean_state_transition_time_seconds",
        observe_state_transition,
        id="state_transition",
    ),
    pytest.param(
        "on_block_timed",
        "lean_fork_choice_block_processing_time_seconds",
        observe_on_block,
        id="on_block",
    ),
    pytest.param(
        "on_attestation_timed",
        "lean_attestation_validation_time_seconds",
        observe_on_attestation,
        id="on_attestation",
    ),
]


# Gauge-style hooks: observer method + Prometheus gauge name.
GAUGE_EMISSIONS = [
    pytest.param("head_slot_observed", "lean_head_slot", id="head_slot"),
    pytest.param("safe_target_observed", "lean_safe_target_slot", id="safe_target"),
    pytest.param("justified_slot_observed", "lean_latest_justified_slot", id="justified"),
    pytest.param("finalized_slot_observed", "lean_latest_finalized_slot", id="finalized"),
    pytest.param("current_slot_observed", "lean_current_slot", id="current_slot"),
    pytest.param("peer_count_observed", "lean_connected_peers", id="peers"),
    pytest.param("validator_count_observed", "lean_validators_count", id="validators"),
]


class TestNullObserverDefault:
    """NullObserver is the registered singleton until set_observer is called."""

    def test_get_observer_returns_null_by_default(self) -> None:
        assert isinstance(get_observer(), NullObserver)

    @pytest.mark.parametrize(("method_name", "_metric_attr", "_cm"), SPEC_EVENTS)
    def test_null_observer_discards_events(
        self,
        method_name: str,
        _metric_attr: str,
        _cm: Callable[[], AbstractContextManager[None]],
    ) -> None:
        getattr(NullObserver(), method_name)(0.5)


class TestSetObserver:
    """set_observer replaces the module singleton."""

    def test_replaces_singleton(self) -> None:
        observer = PrometheusObserver()
        set_observer(observer)
        assert get_observer() is observer


class TestPrometheusObserverUninitialized:
    """PrometheusObserver is a no-op when metrics have not been initialized."""

    @pytest.mark.parametrize(("method_name", "_metric_attr", "_cm"), SPEC_EVENTS)
    def test_no_error_when_metrics_not_initialized(
        self,
        method_name: str,
        _metric_attr: str,
        _cm: Callable[[], AbstractContextManager[None]],
    ) -> None:
        getattr(PrometheusObserver(), method_name)(0.1)


class TestPrometheusObserverWithRegistry:
    """Each hook forwards into its paired Prometheus histogram."""

    @pytest.mark.parametrize(("method_name", "metric_attr", "_cm"), SPEC_EVENTS)
    def test_observes_single_value(
        self,
        fresh_registry: CollectorRegistry,
        method_name: str,
        metric_attr: str,
        _cm: Callable[[], AbstractContextManager[None]],
    ) -> None:
        _init_metrics(fresh_registry)

        getattr(PrometheusObserver(), method_name)(0.5)

        assert _get_histogram_sum(getattr(metrics, metric_attr)) == 0.5

    @pytest.mark.parametrize(("method_name", "metric_attr", "_cm"), SPEC_EVENTS)
    def test_accumulates_multiple_values(
        self,
        fresh_registry: CollectorRegistry,
        method_name: str,
        metric_attr: str,
        _cm: Callable[[], AbstractContextManager[None]],
    ) -> None:
        _init_metrics(fresh_registry)

        observer = PrometheusObserver()
        getattr(observer, method_name)(0.5)
        getattr(observer, method_name)(0.75)

        assert _get_histogram_sum(getattr(metrics, metric_attr)) == 1.25


class _RecordingObserver:
    """Captures every hook call keyed by method name."""

    def __init__(self) -> None:
        self.samples: dict[str, list[float | int | str]] = {
            "state_transition_timed": [],
            "on_block_timed": [],
            "on_attestation_timed": [],
            "head_slot_observed": [],
            "safe_target_observed": [],
            "justified_slot_observed": [],
            "finalized_slot_observed": [],
            "current_slot_observed": [],
            "peer_count_observed": [],
            "validator_count_observed": [],
            "reorg_detected": [],
            "attestation_validated": [],
            "attestation_rejected": [],
        }

    def state_transition_timed(self, seconds: float) -> None:
        self.samples["state_transition_timed"].append(seconds)

    def on_block_timed(self, seconds: float) -> None:
        self.samples["on_block_timed"].append(seconds)

    def on_attestation_timed(self, seconds: float) -> None:
        self.samples["on_attestation_timed"].append(seconds)

    def head_slot_observed(self, slot: int) -> None:
        self.samples["head_slot_observed"].append(slot)

    def safe_target_observed(self, slot: int) -> None:
        self.samples["safe_target_observed"].append(slot)

    def justified_slot_observed(self, slot: int) -> None:
        self.samples["justified_slot_observed"].append(slot)

    def finalized_slot_observed(self, slot: int) -> None:
        self.samples["finalized_slot_observed"].append(slot)

    def current_slot_observed(self, slot: int) -> None:
        self.samples["current_slot_observed"].append(slot)

    def peer_count_observed(self, count: int) -> None:
        self.samples["peer_count_observed"].append(count)

    def validator_count_observed(self, count: int) -> None:
        self.samples["validator_count_observed"].append(count)

    def reorg_detected(self, depth: int) -> None:
        self.samples["reorg_detected"].append(depth)

    def attestation_validated(self, source: str) -> None:
        self.samples["attestation_validated"].append(source)

    def attestation_rejected(self, source: str) -> None:
        self.samples["attestation_rejected"].append(source)


class TestObserveContextManagers:
    """Each observe_* context manager publishes on clean exit, not on raise."""

    @pytest.mark.parametrize(("method_name", "_metric_attr", "cm"), SPEC_EVENTS)
    def test_publishes_on_clean_exit(
        self,
        method_name: str,
        _metric_attr: str,
        cm: Callable[[], AbstractContextManager[None]],
    ) -> None:
        observer = _RecordingObserver()
        set_observer(observer)

        with cm():
            pass

        recorded = observer.samples[method_name]
        assert len(recorded) == 1
        sample = recorded[0]
        assert isinstance(sample, float) and sample >= 0.0

    @pytest.mark.parametrize(("method_name", "_metric_attr", "cm"), SPEC_EVENTS)
    def test_does_not_publish_when_body_raises(
        self,
        method_name: str,
        _metric_attr: str,
        cm: Callable[[], AbstractContextManager[None]],
    ) -> None:
        observer = _RecordingObserver()
        set_observer(observer)

        with pytest.raises(RuntimeError), cm():
            raise RuntimeError("boom")

        assert observer.samples[method_name] == []


class TestGaugeEmissions:
    """Each gauge-style hook forwards into its paired Prometheus gauge."""

    @pytest.mark.parametrize(("method_name", "_metric_attr"), GAUGE_EMISSIONS)
    def test_null_observer_discards(self, method_name: str, _metric_attr: str) -> None:
        getattr(NullObserver(), method_name)(42)

    @pytest.mark.parametrize(("method_name", "_metric_attr"), GAUGE_EMISSIONS)
    def test_prometheus_no_error_when_uninitialized(
        self, method_name: str, _metric_attr: str
    ) -> None:
        getattr(PrometheusObserver(), method_name)(42)

    @pytest.mark.parametrize(("method_name", "metric_attr"), GAUGE_EMISSIONS)
    def test_prometheus_sets_gauge(
        self, fresh_registry: CollectorRegistry, method_name: str, metric_attr: str
    ) -> None:
        _init_metrics(fresh_registry)

        getattr(PrometheusObserver(), method_name)(42)

        assert fresh_registry.get_sample_value(metric_attr) == 42.0

    @pytest.mark.parametrize(("method_name", "metric_attr"), GAUGE_EMISSIONS)
    def test_prometheus_overwrites_gauge(
        self, fresh_registry: CollectorRegistry, method_name: str, metric_attr: str
    ) -> None:
        _init_metrics(fresh_registry)

        observer = PrometheusObserver()
        getattr(observer, method_name)(10)
        getattr(observer, method_name)(25)

        assert fresh_registry.get_sample_value(metric_attr) == 25.0


class TestReorgDetected:
    """reorg_detected bumps the counter and records the depth."""

    def test_null_observer_discards(self) -> None:
        NullObserver().reorg_detected(3)

    def test_prometheus_no_error_when_uninitialized(self) -> None:
        PrometheusObserver().reorg_detected(3)

    def test_prometheus_increments_counter_and_records_depth(
        self, fresh_registry: CollectorRegistry
    ) -> None:
        _init_metrics(fresh_registry)

        PrometheusObserver().reorg_detected(3)

        assert fresh_registry.get_sample_value("lean_fork_choice_reorgs_total") == 1.0
        assert _get_histogram_sum(metrics.lean_fork_choice_reorg_depth) == 3.0


class TestAttestationClassification:
    """attestation_validated / attestation_rejected bump labeled counters."""

    def test_null_observer_discards(self) -> None:
        NullObserver().attestation_validated("gossip")
        NullObserver().attestation_rejected("gossip")

    def test_prometheus_no_error_when_uninitialized(self) -> None:
        PrometheusObserver().attestation_validated("gossip")
        PrometheusObserver().attestation_rejected("gossip")

    def test_prometheus_counters_by_source(self, fresh_registry: CollectorRegistry) -> None:
        _init_metrics(fresh_registry)

        observer = PrometheusObserver()
        observer.attestation_validated("gossip")
        observer.attestation_validated("gossip")
        observer.attestation_rejected("gossip")

        assert (
            fresh_registry.get_sample_value("lean_attestations_valid_total", {"source": "gossip"})
            == 2.0
        )
        assert (
            fresh_registry.get_sample_value("lean_attestations_invalid_total", {"source": "gossip"})
            == 1.0
        )
