import pytest
from models.Models import Block, CHID, User, Authority, Identity
from utils.blocks.miner import Miner
from services.ledger import Ledger
from services.peer import Peer


@pytest.fixture
def unminedBlock():
    """A Block with nonce=0, hash='' — not yet mined."""
    user = User(name="Test", nationalNumber=1, phone=1, age=20, email="test@bc.io", birth="")
    auth = Authority(name="TestAuth", businessID=1)
    doc = Identity(image="", credentialID=1)
    chid = CHID(user=user, credential=doc, issuer=auth)
    return Block(data=chid)


@pytest.fixture
def minedBlock(unminedBlock):
    """A fully mined, valid Block."""
    return Miner.mine(unminedBlock)


@pytest.fixture
def tempLedgerPath(tmp_path):
    """An isolated ledger file path for Ledger/BlockManager tests."""
    return tmp_path / ".ledger-test.json"


@pytest.fixture
def ledgerWithTwoBlocks(tempLedgerPath, unminedBlock):
    """A Ledger with genesis + one additional valid block."""
    ledger = Ledger(filePath=tempLedgerPath)  # genesis auto-created

    unminedBlock.index = len(ledger.blocks)
    unminedBlock.previousHash = ledger.blocks[-1]["hash"]
    mined = Miner.mine(unminedBlock)
    ledger.insertBlock(mined)

    return ledger


@pytest.fixture
def fulledger(tempLedgerPath) -> Ledger:
    ledger = Ledger(tempLedgerPath)
    return ledger


@pytest.fixture
def peer():
    Peer("Testing", "localhost", 121212)