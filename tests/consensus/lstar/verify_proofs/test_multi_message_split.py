"""Multi-message aggregate proof split-by-message vectors."""

import pytest
from consensus_testing import SplitMultiMessageProofsTestFiller

from lean_spec.config import LEAN_ENV
from lean_spec.spec.forks import Checkpoint, Slot, ValidatorIndex
from lean_spec.spec.forks.lstar.containers import AttestationData
from lean_spec.spec.ssz import Bytes32

pytestmark = [
    pytest.mark.valid_until("Lstar"),
    pytest.mark.skipif(
        LEAN_ENV != "prod",
        reason="split_by_message requires a lean_multisig_py build with the test-config fix",
    ),
]


def test_multi_message_split_first_of_two_components(
    split_multi_message_proofs_test: SplitMultiMessageProofsTestFiller,
) -> None:
    """Splitting the first component from a two-component proof yields its single-message proof."""
    split_multi_message_proofs_test(
        validator_indices_per_message=[
            [ValidatorIndex(0), ValidatorIndex(1)],
            [ValidatorIndex(2), ValidatorIndex(3)],
        ],
        attestation_data_per_message=[
            AttestationData(
                slot=Slot(28),
                head=Checkpoint(root=Bytes32(b"\x11" * 32), slot=Slot(28)),
                target=Checkpoint(root=Bytes32(b"\x22" * 32), slot=Slot(28)),
                source=Checkpoint(root=Bytes32(b"\x33" * 32), slot=Slot(0)),
            ),
            AttestationData(
                slot=Slot(29),
                head=Checkpoint(root=Bytes32(b"\x11" * 32), slot=Slot(29)),
                target=Checkpoint(root=Bytes32(b"\x22" * 32), slot=Slot(29)),
                source=Checkpoint(root=Bytes32(b"\x33" * 32), slot=Slot(0)),
            ),
        ],
        selected_message_index=0,
    )


def test_multi_message_split_last_of_two_components(
    split_multi_message_proofs_test: SplitMultiMessageProofsTestFiller,
) -> None:
    """Splitting the last component from a two-component proof yields its single-message proof."""
    split_multi_message_proofs_test(
        validator_indices_per_message=[
            [ValidatorIndex(0), ValidatorIndex(1)],
            [ValidatorIndex(2), ValidatorIndex(3)],
        ],
        attestation_data_per_message=[
            AttestationData(
                slot=Slot(30),
                head=Checkpoint(root=Bytes32(b"\x11" * 32), slot=Slot(30)),
                target=Checkpoint(root=Bytes32(b"\x22" * 32), slot=Slot(30)),
                source=Checkpoint(root=Bytes32(b"\x33" * 32), slot=Slot(0)),
            ),
            AttestationData(
                slot=Slot(31),
                head=Checkpoint(root=Bytes32(b"\x11" * 32), slot=Slot(31)),
                target=Checkpoint(root=Bytes32(b"\x22" * 32), slot=Slot(31)),
                source=Checkpoint(root=Bytes32(b"\x33" * 32), slot=Slot(0)),
            ),
        ],
        selected_message_index=1,
    )


def test_multi_message_split_middle_of_three_components(
    split_multi_message_proofs_test: SplitMultiMessageProofsTestFiller,
) -> None:
    """Splitting the middle component from a three-component proof yields its component proof."""
    split_multi_message_proofs_test(
        validator_indices_per_message=[
            [ValidatorIndex(0)],
            [ValidatorIndex(1), ValidatorIndex(2)],
            [ValidatorIndex(3)],
        ],
        attestation_data_per_message=[
            AttestationData(
                slot=Slot(8),
                head=Checkpoint(root=Bytes32(b"\x11" * 32), slot=Slot(8)),
                target=Checkpoint(root=Bytes32(b"\x22" * 32), slot=Slot(8)),
                source=Checkpoint(root=Bytes32(b"\x33" * 32), slot=Slot(0)),
            ),
            AttestationData(
                slot=Slot(9),
                head=Checkpoint(root=Bytes32(b"\x11" * 32), slot=Slot(9)),
                target=Checkpoint(root=Bytes32(b"\x22" * 32), slot=Slot(9)),
                source=Checkpoint(root=Bytes32(b"\x33" * 32), slot=Slot(0)),
            ),
            AttestationData(
                slot=Slot(0),
                head=Checkpoint(root=Bytes32(b"\x11" * 32), slot=Slot(0)),
                target=Checkpoint(root=Bytes32(b"\x22" * 32), slot=Slot(0)),
                source=Checkpoint(root=Bytes32(b"\x33" * 32), slot=Slot(0)),
            ),
        ],
        selected_message_index=1,
    )
