"""Fixture format for multi-message aggregate proof split-by-message vectors."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from consensus_testing.keys import XmssKeyManager
from consensus_testing.test_fixtures.base import BaseConsensusFixture
from lean_spec.spec.crypto.merkleization import hash_tree_root
from lean_spec.spec.crypto.xmss.containers import PublicKey
from lean_spec.spec.forks import AggregationBits, Slot, ValidatorIndex
from lean_spec.spec.forks.lstar.containers import (
    AttestationData,
    MultiMessageAggregate,
    SingleMessageAggregate,
)
from lean_spec.spec.ssz import ByteList512KiB, Bytes32


class SplitMultiMessageProofsTest(BaseConsensusFixture):
    """Split a multi-message aggregate proof into one component's single-message proof."""

    format_name: ClassVar[str] = "split_multi_message_proofs_test"

    description: ClassVar[str] = (
        "Tests multi-message proof split-by-message against precomputed proof bytes."
    )

    validator_indices_per_message: list[list[ValidatorIndex]] = Field(exclude=True)
    """Per-component validator lists contributing raw signatures."""

    attestation_data_per_message: list[AttestationData]
    """Signed object for each component."""

    selected_message_index: int
    """Index of the component to extract via split_by_message."""

    # Fields below are populated during generation.
    #
    # Together they form the client-visible portion of the JSON vector.

    public_keys_per_message: list[list[PublicKey]] | None = None
    """Attestation public keys per component, parallel to the participation bits."""

    aggregation_bits_per_message: list[AggregationBits] | None = None
    """Per-component participation bitfields naming each component's contributors."""

    messages: list[Bytes32] | None = None
    """Hash tree root per component, bound into the proof."""

    slots: list[Slot] | None = None
    """Slot per component, bound into the proof."""

    proof: ByteList512KiB | None = None
    """Multi-message aggregate proof bytes the client splits."""

    expected_proof: ByteList512KiB | None = None
    """Expected single-message proof bytes the split should produce."""

    def make_fixture(self) -> SplitMultiMessageProofsTest:
        """Build the multi-message proof, split out the selected component, self-verify, return.

        Raises:
            AssertionError: If the split output fails to verify against its component bindings.
            ValueError: If the inputs are misconfigured.
        """
        key_manager = XmssKeyManager.shared()
        component_count = len(self.attestation_data_per_message)
        if component_count == 0:
            raise ValueError("at least one component is required for a split vector")
        if len(self.validator_indices_per_message) != component_count:
            raise ValueError(
                f"validator_indices_per_message length {len(self.validator_indices_per_message)} "
                f"does not match attestation_data_per_message length {component_count}"
            )
        if not 0 <= self.selected_message_index < component_count:
            raise ValueError(
                f"selected_message_index {self.selected_message_index} "
                f"out of range for {component_count} components"
            )

        # Phase 1: derive the honest bundle for each component.
        messages: list[Bytes32] = []
        slots: list[Slot] = []
        public_keys_per_message: list[list[PublicKey]] = []
        aggregation_bits_per_message: list[AggregationBits] = []
        components: list[SingleMessageAggregate] = []

        for validator_indices, attestation_data in zip(
            self.validator_indices_per_message,
            self.attestation_data_per_message,
            strict=True,
        ):
            messages.append(hash_tree_root(attestation_data))
            slots.append(attestation_data.slot)
            public_keys = [key_manager.get_public_keys(i)[0] for i in validator_indices]
            public_keys_per_message.append(public_keys)
            aggregation_bits_per_message.append(AggregationBits.from_indices(validator_indices))
            components.append(
                self._single_message_aggregate(
                    key_manager, attestation_data, validator_indices, public_keys
                )
            )

        # Phase 2: merge into the multi-message proof.
        merged = MultiMessageAggregate.aggregate(
            components,
            public_keys_per_part=public_keys_per_message,
        )

        # Phase 3a: sanity-verify the merged proof itself.
        try:
            merged.verify(
                public_keys_per_message=public_keys_per_message,
                messages=list(zip(messages, slots, strict=True)),
            )
        except Exception as exception:
            raise AssertionError(
                f"Merged multi-message proof rejected its own bindings: {exception}"
            ) from exception

        # Phase 3b: split out the selected component.
        selected_message = messages[self.selected_message_index]
        selected_participants = aggregation_bits_per_message[self.selected_message_index]
        extracted = merged.split_by_message(
            message=selected_message,
            public_keys_per_message=public_keys_per_message,
            participants=selected_participants,
        )

        # Phase 4: self-verify the extracted proof against its component bindings.
        # A split output that fails its own bindings means clients running the same
        # split would produce something the spec considers invalid.
        selected_keys = public_keys_per_message[self.selected_message_index]
        selected_slot = slots[self.selected_message_index]
        try:
            extracted.verify(selected_keys, selected_message, selected_slot)
        except Exception as exception:
            raise AssertionError(
                f"Split output rejected its own bindings: {exception}"
            ) from exception

        # Phase 5: publish the client-visible outputs and return self.
        self.messages = messages
        self.slots = slots
        self.public_keys_per_message = public_keys_per_message
        self.aggregation_bits_per_message = aggregation_bits_per_message
        self.proof = merged.proof
        self.expected_proof = extracted.proof
        return self

    def _single_message_aggregate(
        self,
        key_manager: XmssKeyManager,
        attestation_data: AttestationData,
        validator_indices: list[ValidatorIndex],
        public_keys: list[PublicKey],
    ) -> SingleMessageAggregate:
        """Aggregate raw signatures from each validator into a single-message component."""
        signatures = [
            key_manager.sign_attestation_data(i, attestation_data) for i in validator_indices
        ]
        return SingleMessageAggregate.aggregate(
            children=[],
            raw_xmss=list(zip(validator_indices, public_keys, signatures, strict=True)),
            message=hash_tree_root(attestation_data),
            slot=attestation_data.slot,
        )
