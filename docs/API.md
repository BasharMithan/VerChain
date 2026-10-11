# API Description

Every node runs a small HTTP API next to its P2P listener. The API port is the P2P port **plus 10000**, so a node created with `Peer("Blockchain", "localhost", 8000)` serves the API at `http://localhost:18000`. Interactive Swagger docs are available at `/docs`.

Both `/register` and `/check` take **multipart form data**, because the credential is uploaded as a file (currently PDF only). The uploaded file is validated and hashed in memory; its bytes are never stored in the ledger or sent to other peers.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/register` | Register a credential: derive the IDs, mine a block, store it on-chain |
| `POST` | `/check` | Check that a holder owns a credential |
| `GET` | `/credential-constraints` | Upload limits and supported formats |
| `GET` | `/status` | Node name, address, chain validity and block count |
| `GET` | `/chain` | The node's full chain and the node's own metadata |

## `POST /register`

Builds `User -> Authority -> Credential -> CHID -> Block`, mines the block and inserts it into the ledger. Personal data is used to derive hashes; the credential file itself is not stored.

| Form field | Type | Notes |
|---|---|---|
| `user.name` | text | |
| `user.nationalNumber` | integer | Identifies the holder |
| `user.phone` | integer | |
| `user.age` | integer | |
| `user.email` | text | |
| `user.birth` | text | |
| `credential.documentID` | integer | Must be unique in the ledger |
| `credential.document` | file | PDF, up to `maxUploadSize` |
| `issuer.name` | text | |
| `issuer.issuerID` | integer | The authority's business ID |

```bash
curl -X POST http://localhost:18000/register \
  -F "user.name=Alice" \
  -F "user.nationalNumber=123456" \
  -F "user.phone=5551234" \
  -F "user.age=24" \
  -F "user.email=alice@example.com" \
  -F "user.birth=2002-01-01" \
  -F "credential.documentID=101" \
  -F "issuer.name=JPUF" \
  -F "issuer.issuerID=3423" \
  -F "credential.document=@diploma.pdf;type=application/pdf"
```

**Responses**

| Status | Meaning |
|---|---|
| `201` | The mined block, including `HID`, `CID`, `AUTHID`, `chid`, `hash` and `nonce`. The `document` object contains the title, format, size and `documentHash`, but no content. |
| `400` | The file was rejected: unsupported format, larger than `maxUploadSize`, or not a valid, unencrypted PDF. |
| `409` | The block could not be added: duplicate block, duplicate `documentID`, conflicting holder data, or an invalid chain. `detail` explains which. |
| `422` | A required form field is missing or has the wrong type. |

## `POST /check`

Recomputes the credential hash from the uploaded file and `documentID`, then looks it up in the ledger and compares the derived `CHID`. Nothing is written.

| Form field | Type | Maps to |
|---|---|---|
| `username` | text | `user.name` |
| `userID` | integer | `user.nationalNumber` |
| `document` | file | The same PDF that was registered |
| `documentID` | integer | `credential.documentID` |
| `issuer` | text | `issuer.name` |
| `issuerID` | integer | `issuer.issuerID` |

```bash
curl -X POST http://localhost:18000/check \
  -F "username=Alice" -F "userID=123456" \
  -F "documentID=101" \
  -F "issuer=JPUF" -F "issuerID=3423" \
  -F "document=@diploma.pdf;type=application/pdf"
```

**Responses**

| Status | Body |
|---|---|
| `200` | `"APPROVED"` if the holder, credential and issuer match a registered `CHID`, otherwise `"DECLINED"` |
| `404` | `{"detail": {"error": "...", "message": "..."}}` with `error` one of `User-not-found`, `Issuer-not-found`, `Credential-not-found`. `Credential-not-found` also covers a changed file or a wrong `documentID`. |
| `400` | The uploaded file was rejected (same rules as `/register`). |
| `422` | A required form field is missing or has the wrong type. |

## `GET /credential-constraints`

```json
{ "maxUploadSize": 5242880, "supportedFormats": [".pdf"] }
```

## `GET /status`

```json
{ "name": "Blockchain", "host": "localhost", "port": 8000, "chainValidity": true, "blocksCount": 12 }
```

`chainValidity` is computed by validating the whole chain on every call, so the cost grows with the ledger.

## `GET /chain`

Returns `{"sender": <node metadata>, "chain": [<block>, ...]}`. Used by peers during chain sync.

## How verification works

The hashes are described in [Hashing in Verchain](Hashing-in-Verchain.md), and the upload path in [Document Flow](Document-Flow.md). In short:

```python
documentHash = sha256(content : format : documentID)
CID          = sha256(documentHash : documentID)
CHID         = sha256(HID : CID : AUTHID)
```

On `/check` the node rebuilds these IDs from the request and the uploaded file, looks the credential up by `documentHash`, and approves only if the rebuilt `CHID` is on the ledger.
