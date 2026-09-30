import hashlib

from utils.generators import IDGenerator


def test_generate_id_matches_sha256_for_text():
    value = "verchain"

    assert IDGenerator.generateID(value) == hashlib.sha256(value.encode("utf-8")).hexdigest()


def test_generate_id_uses_string_representation_for_integers():
    assert IDGenerator.generateID(42) == IDGenerator.generateID("42")


def test_generate_chid_hashes_ordered_components():
    components = ("holder", "credential", "authority")
    expected = hashlib.sha256(":".join(components).encode("utf-8")).hexdigest()

    assert IDGenerator.generateCHID(*components) == expected


def test_block_hash_matches_hash_of_block_fields(unminedBlock):
    unminedBlock.index = 3
    unminedBlock.nonce = 7
    unminedBlock.previousHash = "a" * 64
    content = (
        f"{unminedBlock.index}{unminedBlock.data.chid}"
        f"{unminedBlock.nonce}{unminedBlock.previousHash}"
    )

    assert unminedBlock.computeHash() == hashlib.sha256(content.encode("utf-8")).hexdigest()


def test_block_hash_changes_when_nonce_changes(unminedBlock):
    original_hash = unminedBlock.computeHash()
    unminedBlock.nonce += 1

    assert unminedBlock.computeHash() != original_hash


def test_empty_block_hash_is_invalid(unminedBlock):
    assert unminedBlock.isHashValid() is False


def test_hash_validity_detects_a_changed_previous_hash(minedBlock):
    assert minedBlock.isHashValid() is True

    minedBlock.previousHash = "b" * 64

    assert minedBlock.isHashValid() is False