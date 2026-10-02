# API Description

The main way to access the system's functionalities is via API calls. Each path in the system is accessible by API calls.

## How It Works

**Registration** - full object in, `CHID` derived and stored on-chain.

```json
POST /register
{
  "user":       { "name": "Alice", "nationalNumber": 123456, ... },
  "issuer":     { "name": "JPUF", "businessID": 3423 },
  "credential": { "documentID": 101, "image": "..." }
}
```

The node builds `User -> Authority -> Credential -> CHID -> Block`, mines it, stores the `CHID` on-chain. The full personal data is never written anywhere. It's used to derive the hash and discarded.

**Verification** - three integers in, ledger search:

```json
POST /verify
{
  "nationalNumber": 123456,
  "documentID":   101,
  "businessID":     3423
}
```

The node scans every block in the ledger looking for one where all three conditions are met simultaneously. If a block matches all three $\rightarrow$ `APPROVE`. If not $\rightarrow$ `DECLINE`.

##  Why This Works Without Hashing

The blocks already store the full nested data structure: `User`, `Credential`, `Issuer` are all in `Block.data`. So we don't need to reconstruct the `CHID` at all during the verification. We just search for the block directly. 