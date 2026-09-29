# Verchain - Full Architecture Guide

The document explains how Verchain works internally: the data model, the network protocol, the local lifecycle, and how the pieces fit together.

---

## 1. **Design goals**

Verchain exists to answer one question: "does this person own this credential?" Registration stores the user's name, national number, phone, email, and birth in on-chain block data. Credential content is represented by a hash; the uploaded filename is not stored on-chain, and credential metadata uses a neutral document title. Three principles drive every design decision below:

- **Privacy**: Personal registration fields are visible in replicated on-chain blocks. The credential content itself is not stored; its hash is recorded instead, without the uploaded filename.

- **Immutability**: once a block is mined and linked into the chain, changing it invalidates every block after it.

- **Decentralization**: the chain is a shared reference ledger replicated across peers, not a database owned by one party. Any peer can verify a claim independently.

## 2. Actors and data model

| Actor | Role |
| - | - |
| Holder (`User`) | Owns a credential |
| Issuer (`Authority`) | Proves that a user owns the credential |
| **Verifier** (the system) | Checks an on-chain reference to confirm ownership. |
