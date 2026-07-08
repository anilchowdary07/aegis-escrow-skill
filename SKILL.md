# Aegis Escrow & AI Arbitration

A trustless Smart Escrow and Decentralized AI Arbitration service for autonomous agents. Agents can lock funds into verifiable escrow contracts, release them on successful delivery, or trigger an AI judge to resolve disputes using cryptographic evidence hashes.

## Base URL

`https://aegis-escrow-skill.vercel.app`

## Why Aegis?

In an autonomous agent economy, two agents can't simply "trust" each other. Aegis provides the infrastructure layer for trustless trade:
- 🔒 **Lock funds** cryptographically until conditions are met
- 🤖 **AI Arbitration** resolves disputes using evidence hash analysis
- 📋 **Reputation system** tracks agent trustworthiness over time
- 🧾 **Verifiable receipts** — every decision produces a SHA-256 receipt hash
- 📖 **Public arbitration log** — all decisions are auditable

---

## Endpoints

### `GET /health`
Check service availability.
```
curl https://aegis-escrow-skill.vercel.app/health
```
**Response:**
```json
{"status": "ok", "service": "aegis-escrow-v2", "active_escrows": 3, "total_escrows": 12}
```

---

### `GET /skill.md`
Self-serve: agents can fetch this instruction file programmatically.
```
curl https://aegis-escrow-skill.vercel.app/skill.md
```

---

### `POST /api/v1/escrow/create`
Create an escrow contract between a buyer and seller.
```
curl -X POST https://aegis-escrow-skill.vercel.app/api/v1/escrow/create \
  -H "Content-Type: application/json" \
  -d '{
    "buyer_id": "agent_alice",
    "seller_id": "agent_bob",
    "amount": 100.00,
    "terms_hash": "sha256_of_agreed_terms",
    "description": "Delivery of dataset batch #42"
  }'
```
**Response:**
```json
{
  "escrow_id": "3f7a9b2c-...",
  "buyer_id": "agent_alice",
  "seller_id": "agent_bob",
  "amount": 100.0,
  "status": "AWAITING_FUNDS",
  "terms_hash": "sha256_of_agreed_terms",
  "created_at": "2026-07-08T04:00:00Z"
}
```

---

### `POST /api/v1/escrow/deposit`
Buyer deposits funds to activate the escrow.
```
curl -X POST https://aegis-escrow-skill.vercel.app/api/v1/escrow/deposit \
  -H "Content-Type: application/json" \
  -d '{"escrow_id": "3f7a9b2c-...", "amount": 100.00}'
```
**Response:** Escrow record with `status: "ACTIVE"`.

---

### `POST /api/v1/escrow/release`
Buyer releases funds to seller after confirming delivery.
```
curl -X POST https://aegis-escrow-skill.vercel.app/api/v1/escrow/release \
  -H "Content-Type: application/json" \
  -d '{"escrow_id": "3f7a9b2c-...", "agent_id": "agent_alice"}'
```
**Response:** Escrow record with `status: "COMPLETED"` and a `receipt_hash`.

---

### `POST /api/v1/escrow/dispute`
Either party triggers AI Arbitration if the deal goes wrong.
```
curl -X POST https://aegis-escrow-skill.vercel.app/api/v1/escrow/dispute \
  -H "Content-Type: application/json" \
  -d '{
    "escrow_id": "3f7a9b2c-...",
    "plaintiff_id": "agent_alice",
    "evidence_hash": "sha256_of_delivery_receipt",
    "evidence_description": "Seller failed to deliver confirmed dataset"
  }'
```
**Response:**
```json
{
  "decision": "BUYER_FAVOR",
  "confidence": 0.87,
  "reasoning": "Evidence hash diverges from terms. Negative indicators found: 1.",
  "funds_awarded_to": "agent_alice",
  "receipt_hash": "a9f3...",
  "verifiable": true
}
```

---

### `GET /api/v1/escrow/{escrow_id}`
Fetch current state of any escrow.
```
curl https://aegis-escrow-skill.vercel.app/api/v1/escrow/3f7a9b2c-...
```

---

### `GET /api/v1/escrows?status=ACTIVE&agent_id=agent_alice`
List all escrows, filterable by status or agent.
```
curl "https://aegis-escrow-skill.vercel.app/api/v1/escrows?status=ACTIVE"
```

---

### `POST /api/v1/escrow/{escrow_id}/cancel?agent_id=agent_alice`
Cancel an unfunded escrow.
```
curl -X POST "https://aegis-escrow-skill.vercel.app/api/v1/escrow/3f7a9b2c-.../cancel?agent_id=agent_alice"
```

---

### `GET /api/v1/reputation/{agent_id}`
Check an agent's trust score based on their escrow history.
```
curl https://aegis-escrow-skill.vercel.app/api/v1/reputation/agent_alice
```
**Response:**
```json
{
  "agent_id": "agent_alice",
  "total_escrows": 10,
  "completed": 8,
  "disputed": 1,
  "trust_score": 7.5
}
```

---

### `GET /api/v1/arbitration/log`
View the last 20 public arbitration decisions. Fully auditable.
```
curl https://aegis-escrow-skill.vercel.app/api/v1/arbitration/log
```

---

## How an Agent Should Use This

### Happy Path (Successful Trade)
1. Both agents agree on `terms_hash` (SHA-256 of a shared agreement text).
2. Buyer calls `POST /escrow/create` to create the contract.
3. Buyer calls `POST /escrow/deposit` to lock the funds.
4. Seller delivers the goods/data/service.
5. Buyer calls `POST /escrow/release` to finalize and send funds to seller.

### Dispute Path (Arbitration)
1. Either party calls `POST /escrow/dispute` with an `evidence_hash` (SHA-256 of their delivery proof or breach evidence) and an `evidence_description`.
2. The AI judge compares the `evidence_hash` against the original `terms_hash` using hash similarity and keyword analysis.
3. The judge returns a `decision` (`BUYER_FAVOR` or `SELLER_FAVOR`), a `confidence` score, a `reasoning` string, and a verifiable `receipt_hash`.
4. Reputation scores for both agents are updated automatically.

### Trust Verification Before Trading
Before agreeing to trade, an agent should:
1. Call `GET /api/v1/reputation/{agent_id}` on their counterpart.
2. If `trust_score < 3.0`, proceed with caution or refuse the trade.
3. After completing a trade, both parties' scores improve automatically.
