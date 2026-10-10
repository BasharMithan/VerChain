# source/tests/e2eNetworkTest.py
import time
import uuid
import itertools

import pytest

from services.peer import Peer
from models.Models import Authority, Block, CHID, Credential, Document, User


pytestmark = pytest.mark.integration

_portCounter = itertools.count(31000, step=5)

@pytest.mark.integration
def _freePortBlock() -> int:
    """Hands out a fresh, well-spaced port per peer so repeated/parallel test
    runs don't collide on already-bound sockets."""
    return next(_portCounter)


@pytest.fixture
def spawnPeer():
    """Factory fixture: spawns a real Peer with a unique title/port, starts its
    network thread, and tears it down (network stop + ledger file cleanup) after."""
    spawned = []

    def _spawn(name: str) -> Peer:
        uniqueTitle = f"{name}-{uuid.uuid4().hex[:8]}"
        port = _freePortBlock()
        peer = Peer(uniqueTitle, "127.0.0.1", port)
        peer.startNetwork()
        spawned.append(peer)
        return peer

    yield _spawn

    for peer in spawned:
        try:
            peer.stopNetwork()
        except Exception:
            pass
        try:
            peer.ledger.filePath.unlink(missing_ok=True)
        except Exception:
            pass


@pytestmark
def _connect(a: Peer, b: Peer, settle: float = 1.0) -> None:
    """Connects `a` outbound to `b`, then waits for the handshake to settle."""
    a.network.connect_with_node(host=b.host, port=b.port)
    time.sleep(settle)


@pytestmark
def _makeBlock(tag: str, nationalNumber: int, documentID: int, businessID: int) -> Block:
    user = User(name=f"User-{tag}", nationalNumber=nationalNumber, phone=1, age=25, email="test@bc.io", birth="")
    auth = Authority(name=f"Auth-{tag}", businessID=businessID)
    doc = Credential(
        document=Document(documentFormat="text/plain", documentTitle="", documentContentSize=0, documentHash=""),
        documentID=documentID,
    )
    chid = CHID(user=user, credential=doc, issuer=auth)
    return Block(data=chid)



@pytestmark
def test_registered_block_propagates_to_directly_connected_peer(spawnPeer):
    peerA = spawnPeer("A")
    peerB = spawnPeer("B")
    _connect(peerA, peerB)

    block = _makeBlock("AB", nationalNumber=1001, documentID=1, businessID=10)
    result = peerA.registerBlock(block)

    assert result is not None
    assert result.isMined()

    time.sleep(1.5)  # let the broadcast + receiveBlock settle on B

    assert len(peerA.ledger.blocks) == 2  # genesis + new block
    assert len(peerB.ledger.blocks) == 2

    aChids = {b["data"]["chid"] for b in peerA.ledger.blocks}
    bChids = {b["data"]["chid"] for b in peerB.ledger.blocks}
    assert aChids == bChids


@pytestmark
def test_status_and_chain_agree_across_connected_peers(spawnPeer):
    peerA = spawnPeer("A")
    peerB = spawnPeer("B")
    _connect(peerA, peerB)

    block = _makeBlock("STATUS", nationalNumber=2002, documentID=2, businessID=20)
    peerA.registerBlock(block)
    time.sleep(1.5)

    assert len(peerA.ledger.blocks) == len(peerB.ledger.blocks)
    assert peerA.ledger.blocks[-1]["hash"] == peerB.ledger.blocks[-1]["hash"]




@pytestmark
def test_verification_succeeds_on_peer_that_did_not_originate_block(spawnPeer):
    from services.verifier import Verifier
    from models.Models import Query, Response

    peerA = spawnPeer("A")
    peerB = spawnPeer("B")
    _connect(peerA, peerB)

    chid = CHID(
        user=User(name="Remote", nationalNumber=3003, phone=1, age=40, email="test@bc.io", birth=""),
        credential=Credential(
            document=Document(documentFormat="text/plain", documentTitle="", documentContentSize=0, documentHash=""),
            documentID=3,
        ),
        issuer=Authority(name="RemoteAuth", businessID=30),
    )
    peerA.registerBlock(Block(data=chid))
    time.sleep(1.5)

    query = Query(user=chid.user, credential=chid.credential, issuer=chid.issuer)
    result = Verifier.check(query, peerB.ledger.blocks)  # B's own ledger, not A's

    assert result == Response.appove



@pytestmark
def test_three_peer_mesh_all_receive_direct_broadcast(spawnPeer):
    peerA = spawnPeer("A")
    peerB = spawnPeer("B")
    peerC = spawnPeer("C")

    _connect(peerA, peerB)
    _connect(peerA, peerC)
    _connect(peerB, peerC)

    block = _makeBlock("MESH", nationalNumber=4004, documentID=4, businessID=40)
    peerB.registerBlock(block)
    time.sleep(2)

    for peer in (peerA, peerB, peerC):
        assert len(peer.ledger.blocks) == 2, f"{peer.title} did not receive the broadcast block"




@pytestmark
def test_late_joining_peer_syncs_existing_chain(spawnPeer):
    peerA = spawnPeer("A")
    for i in range(3):
        block = _makeBlock(f"PRE{i}", nationalNumber=5000 + i, documentID=5 + i, businessID=50 + i)
        peerA.registerBlock(block)
    assert len(peerA.ledger.blocks) == 4  # genesis + 3

    peerD = spawnPeer("D")
    assert len(peerD.ledger.blocks) == 1  # just its own genesis

    _connect(peerD, peerA)
    peerD.requestChainSync()
    time.sleep(2)

    assert len(peerD.ledger.blocks) == len(peerA.ledger.blocks)
    assert peerD.ledger.blocks[-1]["hash"] == peerA.ledger.blocks[-1]["hash"]



# source/tests/e2eNetworkTest.py — replace the xfail test with:
@pytestmark
def test_block_propagates_through_a_line_topology(spawnPeer):
    """A-B-C line, no direct A-C link. Registering on A must reach C via B's relay."""
    peerA = spawnPeer("A")
    peerB = spawnPeer("B")
    peerC = spawnPeer("C")

    _connect(peerA, peerB)
    _connect(peerB, peerC)  # A and C are NOT directly connected

    block = _makeBlock("LINE", nationalNumber=6006, documentID=6, businessID=60)
    peerA.registerBlock(block)
    time.sleep(2.5)  # one extra hop needs a bit more settle time

    assert len(peerC.ledger.blocks) == 2, "block should have relayed through B to reach C"
    assert peerC.ledger.blocks[-1]["hash"] == peerA.ledger.blocks[-1]["hash"]


@pytestmark
def test_mesh_relay_does_not_duplicate_or_loop(spawnPeer):
    """In a fully-connected 3-peer mesh, relaying must not cause duplicate
    block insertion attempts or infinite re-broadcast loops."""
    peerA = spawnPeer("A")
    peerB = spawnPeer("B")
    peerC = spawnPeer("C")

    _connect(peerA, peerB)
    _connect(peerA, peerC)
    _connect(peerB, peerC)

    block = _makeBlock("NOLOOP", nationalNumber=7007, documentID=7, businessID=70)
    peerA.registerBlock(block)
    time.sleep(2.5)

    for peer in (peerA, peerB, peerC):
        assert len(peer.ledger.blocks) == 2  # exactly once, not duplicated