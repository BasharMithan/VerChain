# Verchain - Full Architecture Guide

The document explains how Verchain works internally: the data model, the network protocol, the local lifecycle, and how the pieces fit together.

---

## 1. **Design goals**

Verchain exists to answer oen question: "does this person own this credential?", without ever holding the credential or the person's data ifself. Three principles drive every design decision below:

- **Privacy**: Raw personal data (name, national number, credential, ...) is hashed into an identifier and then discarded. Only the hash is ever written to the chain.

- **Immutability**: once a block is mined and linked into the chain, changing it invalidates every block after it.

- **Decentralization**: the chain is a shared reference ledger replicated across peers, not a database owned by one party. Any peer can verify a claim independently.

## 2. Actors and data model

| Actor | Role |
| - | - |
| Holder (`User`) | Owns a credential |
| Issuer (`Authority`) | Proves that a user owns the credential |
| **Verifier** (the system) | Checks an on-chain reference to confirm ownership. |
