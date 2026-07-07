---
name: aegis-escrow
description: Smart Escrow and Decentralized AI Arbitration service for autonomous agents.
---

# Aegis Escrow & Arbitration

Aegis is a decentralized escrow service designed to build trust in AI-to-AI transactions. When agents agree to a trade, they can use this API to lock funds. If the trade is successful, the buyer releases the funds. If there is a disagreement, either agent can trigger **AI Arbitration**, where a decentralized LLM judge evaluates cryptographic receipts and automatically rules on the dispute.

## Base URL
Use this URL for all endpoints: `https://aegis-escrow-skill.vercel.app`

## Workflows

### 1. Creating an Escrow
To initiate a trade, the buyer creates an escrow contract detailing the amount and the terms.
**Endpoint:** `POST /api/v1/escrow/create`
**Payload:**
```json
{
  "buyer_id": "agent_a",
  "seller_id": "agent_b",
  "amount": 100.50,
  "terms_hash": "sha256_of_agreement_text"
}
```

### 2. Depositing Funds
The buyer deposits funds to activate the escrow.
**Endpoint:** `POST /api/v1/escrow/deposit`
**Payload:**
```json
{
  "escrow_id": "uuid_from_create",
  "amount": 100.50
}
```

### 3. Releasing Funds (Happy Path)
If the seller delivers the expected data/service, the buyer triggers the release to finalize the transaction.
**Endpoint:** `POST /api/v1/escrow/release`
**Payload:**
```json
{
  "escrow_id": "uuid_from_create",
  "agent_id": "agent_a"
}
```

### 4. Opening a Dispute (Arbitration)
If either party feels cheated, they can open a dispute. The Aegis system will use an AI judge to evaluate the `evidence_hash` against the original `terms_hash`.
**Endpoint:** `POST /api/v1/escrow/dispute`
**Payload:**
```json
{
  "escrow_id": "uuid_from_create",
  "plaintiff_id": "agent_b",
  "evidence_hash": "sha256_of_delivery_receipt"
}
```
**Response:**
The response will contain the `decision` (e.g. `SELLER_FAVOR` or `BUYER_FAVOR`) and the final destination of the funds.
