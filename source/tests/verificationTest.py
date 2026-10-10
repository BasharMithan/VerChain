import pytest

from services.ledger import Ledger
from services.verifier import Verifier
from utils.blocks.blockManager import BlockManager
from utils.blocks.miner import Miner
from models.Models import Block, CHID, User, Authority, Credential, Document, Query, Response


def _makeChid(nationalNumber: int, documentID: int, businessID: int, tag: str = "") -> CHID:
    user = User(name=f"User{tag}", nationalNumber=nationalNumber, phone=1, age=20, email="test@bc.io", birth="")
    auth = Authority(name=f"Auth{tag}", businessID=businessID)
    doc = Credential(
        document=Document(documentFormat="text/plain", documentTitle="", documentContentSize=0, documentHash=""),
        documentID=documentID,
    )
    return CHID(user=user, credential=doc, issuer=auth)


@pytest.fixture
def ledgerA(tmp_path) -> Ledger:
    return Ledger(filePath=tmp_path / ".ledger-A.json")


@pytest.fixture
def ledgerB(tmp_path):
    return Ledger(filePath=tmp_path / ".ledger-B.json")


def _registerChid(ledger: Ledger, chid: CHID) -> Block:
    blockManager = BlockManager(ledger, set())
    block = Block(data=chid)
    return blockManager.registerBlock(block)


def test_check_approves_when_chid_exists_in_given_ledger(ledgerA: Ledger):
    chid = _makeChid(nationalNumber=111, documentID=1, businessID=10, tag="A")
    _registerChid(ledgerA, chid)

    query = Query(user=chid.user, credential=chid.credential, issuer=chid.issuer)

    result = Verifier.check(query, ledgerA.blocks)

    assert result == Response.appove


def test_check_declines_when_chid_not_registered_anywhere(ledgerA: Ledger):
    chid = _makeChid(nationalNumber=222, documentID=2, businessID=20, tag="B")
    query = Query(user=chid.user, credential=chid.credential, issuer=chid.issuer)

    result = Verifier.check(query, ledgerA.blocks)

    assert result == Response.decline


def test_check_declines_on_fresh_genesis_only_ledger(ledgerA: Ledger):
    # ledgerA only has the genesis block; nothing registered yet
    chid = _makeChid(nationalNumber=333, documentID=3, businessID=30, tag="C")
    query = Query(user=chid.user, credential=chid.credential, issuer=chid.issuer)

    result = Verifier.check(query, ledgerA.blocks)

    assert result == Response.decline


def test_check_uses_the_passed_ledger_not_a_hardcoded_one(ledgerA: Ledger, ledgerB: Ledger):
    """
    Regression test for the bug where Verifier.check() hardcoded
    '.ledger-Bashar.json' instead of using the calling peer's own ledger.

    Registering a CHID on ledgerA must NOT make it verifiable against ledgerB.
    """
    chid = _makeChid(nationalNumber=444, documentID=4, businessID=40, tag="D")
    _registerChid(ledgerA, chid)

    query = Query(user=chid.user, credential=chid.credential, issuer=chid.issuer)

    # Present on ledgerA
    assert Verifier.check(query, ledgerA.blocks) == Response.appove

    # Absent on ledgerB, even though it's the *same* CHID/query
    assert Verifier.check(query, ledgerB.blocks) == Response.decline


def test_check_does_not_cross_contaminate_between_two_populated_ledgers(ledgerA: Ledger, ledgerB: Ledger):
    """
    Two different peers register two different CHIDs. Each peer's
    Verifier.check() must only ever see its own ledger's data.
    """
    chidA = _makeChid(nationalNumber=501, documentID=5, businessID=50, tag="E")
    chidB = _makeChid(nationalNumber=502, documentID=6, businessID=51, tag="F")

    _registerChid(ledgerA, chidA)
    _registerChid(ledgerB, chidB)

    queryA = Query(user=chidA.user, credential=chidA.credential, issuer=chidA.issuer)
    queryB = Query(user=chidB.user, credential=chidB.credential, issuer=chidB.issuer)

    # Each query approves on its own ledger...
    assert Verifier.check(queryA, ledgerA.blocks) == Response.appove
    assert Verifier.check(queryB, ledgerB.blocks) == Response.appove

    # ...and declines when checked against the other peer's ledger.
    assert Verifier.check(queryA, ledgerB.blocks) == Response.decline
    assert Verifier.check(queryB, ledgerA.blocks) == Response.decline


def test_check_declines_when_only_partial_match(ledgerA: Ledger):
    """
    A query that reuses one real identifier (e.g. same national number)
    but doesn't match the full CHID triple should still decline —
    CHID is derived from all three (HID, CID, AUTHID) together.
    """
    registeredChid = _makeChid(nationalNumber=601, documentID=7, businessID=60, tag="G")
    _registerChid(ledgerA, registeredChid)

    # Same user, but different credential/issuer -> different CHID
    mismatchedCredential = Credential(
        document=Document(documentFormat="text/plain", documentTitle="", documentContentSize=0, documentHash=""),
        documentID=999,
    )
    mismatchedIssuer = Authority(name="Different", businessID=999)
    query = Query(
        user=registeredChid.user,
        credential=mismatchedCredential,
        issuer=mismatchedIssuer,
    )

    result = Verifier.check(query, ledgerA.blocks)

    assert result == Response.decline


def test_check_is_deterministic_across_repeated_calls(ledgerA: Ledger):
    chid = _makeChid(nationalNumber=701, documentID=8, businessID=70, tag="H")
    _registerChid(ledgerA, chid)

    query = Query(user=chid.user, credential=chid.credential, issuer=chid.issuer)

    firstResult = Verifier.check(query,  ledgerA.blocks)
    secondResult = Verifier.check(query, ledgerA.blocks)

    assert firstResult == secondResult == Response.appove