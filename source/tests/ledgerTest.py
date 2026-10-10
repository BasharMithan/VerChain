import json
import pytest

from services.ledger import Ledger
from utils.blocks.miner import Miner
from errors import LedgerCorruptError, InvalidChainError, BlockHashMismatchError
from errors.blockErrors import BlockIntegrationError
from models.Models import *


def test_fresh_ledger_has_genesis(tempLedgerPath):
    ledger = Ledger(filePath=tempLedgerPath)

    assert len(ledger.blocks) == 1
    assert ledger.blocks[0]["index"] == 0
    assert ledger.blocks[0]["previousHash"] == "0" * 64


def test_genesis_is_mined_and_hash_valid(tempLedgerPath):
    ledger = Ledger(filePath=tempLedgerPath)

    from models.Models import Block
    genesis = Block.model_validate(ledger.blocks[0])

    assert genesis.isMined() is True
    assert genesis.isHashValid() is True


# def test_document_binary_content_round_trips_through_json():
#     content = b"PDF data with non-UTF-8 bytes: \x00\xff\x80"
#     document = Document(documentContent=content)

#     restored = Document.model_validate_json(document.model_dump_json())

#     assert restored.documentContent == content


def test_insert_persists_to_disk(ledgerWithTwoBlocks):
    # ledgerWithTwoBlocks fixture already inserted a second block
    onDisk = json.loads(ledgerWithTwoBlocks.filePath.read_text())
    assert len(onDisk) == 2
    assert onDisk[0]["index"] == 0
    assert onDisk[1]["index"] == 1


def test_reload_from_disk_matches_in_memory(ledgerWithTwoBlocks):
    reloaded = Ledger(filePath=ledgerWithTwoBlocks.filePath)

    assert len(reloaded.blocks) == len(ledgerWithTwoBlocks.blocks)
    assert reloaded.blocks[-1]["hash"] == ledgerWithTwoBlocks.blocks[-1]["hash"]


def test_credentials_are_loaded_from_ledger_by_document_hash(ledgerWithTwoBlocks):
    ledger = Ledger(filePath=ledgerWithTwoBlocks.filePath)

    for block in ledger.blocks:
        credential_hash = block["data"]["credential"]["document"]["documentHash"]
        if credential_hash:
            assert credential_hash in ledger.credentials
            assert ledger.findCredential(credential_hash) is not None


def test_corrupt_ledger_file_raises_on_load(tempLedgerPath):
    # Write a bare JSON object instead of a list
    tempLedgerPath.write_text(json.dumps({"not": "a list"}))

    with pytest.raises(LedgerCorruptError):
        Ledger(filePath=tempLedgerPath)


def test_malformed_json_raises_on_load(tempLedgerPath):
    tempLedgerPath.write_text("{not valid json")

    with pytest.raises(LedgerCorruptError):
        Ledger(filePath=tempLedgerPath)


def test_invalid_document_content_size_raises_ledger_corrupt(tempLedgerPath):
    Ledger(filePath=tempLedgerPath)
    blocks = json.loads(tempLedgerPath.read_text())
    blocks[0]["data"]["credential"]["document"]["documentContentSize"] = "not-an-int"
    tempLedgerPath.write_text(json.dumps(blocks))

    with pytest.raises(LedgerCorruptError):
        Ledger(filePath=tempLedgerPath)


def test_all_blocks_returns_full_chain(ledgerWithTwoBlocks):
    all_blocks = ledgerWithTwoBlocks.allBlocks()

    assert len(all_blocks) == 2
    assert all_blocks is ledgerWithTwoBlocks.blocks  # same list reference


def test_insert_on_invalid_chain_raises(ledgerWithTwoBlocks):
    blocks = json.loads(ledgerWithTwoBlocks.filePath.read_text())
    blocks[0]["nonce"] = 999999
    ledgerWithTwoBlocks.filePath.write_text(json.dumps(blocks))
    ledgerWithTwoBlocks.blocks = blocks  # sync in-memory state

    # Different user — different CHID
    user = User(name="Unique", nationalNumber=9999, phone=9, age=40, email="test@bc.io", birth="")
    auth = Authority(name="B", businessID=2)
    doc  = Credential(
        document=Document(documentFormat="text/plain", documentTitle="", documentContentSize=0, documentHash=""),
        documentID=9,
    )
    chid = CHID(user=user, credential=doc, issuer=auth)
    block = Block(data=chid)
    block.index = 2
    block.previousHash = blocks[-1]["hash"]
    mined = Miner.mine(block)

    with pytest.raises(BlockIntegrationError):
        print(ledgerWithTwoBlocks.blocks)
        ledgerWithTwoBlocks.insertBlock(mined)