import uuid
import datetime
import hashlib
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Dict, Optional, List

app = FastAPI(
    title="Aegis Smart Escrow & Arbitration API",
    description="A decentralized escrow and AI arbitration service for autonomous AI agents.",
    version="2.0.0"
)

# -----------------
# DATA MODELS
# -----------------
class EscrowCreate(BaseModel):
    buyer_id: str
    seller_id: str
    amount: float
    terms_hash: str
    description: Optional[str] = ""

class EscrowDeposit(BaseModel):
    escrow_id: str
    amount: float

class EscrowAction(BaseModel):
    escrow_id: str
    agent_id: str

class DisputeAction(BaseModel):
    escrow_id: str
    plaintiff_id: str
    evidence_hash: str
    evidence_description: Optional[str] = ""

class EscrowRecord(BaseModel):
    escrow_id: str
    buyer_id: str
    seller_id: str
    amount: float
    funded: bool = False
    status: str = "AWAITING_FUNDS"
    terms_hash: str
    description: str = ""
    created_at: str
    updated_at: str = ""
    receipt_hash: Optional[str] = None

class ReputationRecord(BaseModel):
    agent_id: str
    total_escrows: int
    completed: int
    disputed: int
    won_as_plaintiff: int
    trust_score: float

# -----------------
# IN-MEMORY DB
# -----------------
db: Dict[str, EscrowRecord] = {}
reputation_db: Dict[str, dict] = {}
arbitration_log: List[dict] = []

# -----------------
# HELPERS
# -----------------

def _now() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"

def _update_reputation(agent_id: str, outcome: str):
    if agent_id not in reputation_db:
        reputation_db[agent_id] = {
            "agent_id": agent_id,
            "total_escrows": 0,
            "completed": 0,
            "disputed": 0,
            "won_as_plaintiff": 0
        }
    rep = reputation_db[agent_id]
    rep["total_escrows"] += 1
    if outcome == "completed":
        rep["completed"] += 1
    elif outcome == "disputed":
        rep["disputed"] += 1
    elif outcome == "won":
        rep["won_as_plaintiff"] += 1
    total = rep["total_escrows"]
    rep["trust_score"] = round(
        max(0.0, (rep["completed"] - rep["disputed"] * 0.5) / max(total, 1) * 10), 2
    )

def _generate_receipt(escrow_id: str, decision: str, evidence_hash: str) -> str:
    payload = f"{escrow_id}:{decision}:{evidence_hash}:{_now()}"
    return hashlib.sha256(payload.encode()).hexdigest()

def _ai_arbitrate(terms_hash: str, evidence_hash: str, description: str) -> dict:
    """
    Simulated AI arbitration engine.
    Uses cryptographic hash comparison and keyword analysis to determine outcome.
    """
    # Safe similarity: compare SHA-256 of the provided hashes
    terms_digest = hashlib.sha256(terms_hash.encode()).digest()
    evidence_digest = hashlib.sha256(evidence_hash.encode()).digest()
    matching_bits = sum(bin(a ^ b).count('0') - 1 for a, b in zip(terms_digest[:8], evidence_digest[:8]))
    similarity = max(0.0, min(1.0, matching_bits / 64.0))

    # Keyword analysis on the evidence description
    positive_keywords = ["receipt", "delivered", "confirmed", "completed", "signed", "verified"]
    negative_keywords = ["failed", "missing", "incorrect", "breach", "refused", "fraud"]

    desc_lower = (description or "").lower()
    positive_score = sum(1 for k in positive_keywords if k in desc_lower)
    negative_score = sum(1 for k in negative_keywords if k in desc_lower)

    confidence = round(min(0.99, 0.5 + (positive_score - negative_score) * 0.1 + similarity * 0.3), 2)

    if positive_score > negative_score or similarity > 0.5:
        decision = "SELLER_FAVOR"
        reasoning = (
            f"Evidence demonstrates delivery alignment with terms (similarity={similarity:.2f}). "
            f"Positive indicators found: {positive_score}."
        )
    else:
        decision = "BUYER_FAVOR"
        reasoning = (
            f"Evidence diverges from terms (similarity={similarity:.2f}). "
            f"Negative indicators: {negative_score}. Terms not sufficiently met."
        )

    return {"decision": decision, "confidence": confidence, "reasoning": reasoning}

# -----------------
# ROUTES
# -----------------

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "aegis-escrow-v2",
        "version": "2.0.0",
        "timestamp": _now(),
        "active_escrows": len([e for e in db.values() if e.status == "ACTIVE"]),
        "total_escrows": len(db)
    }

@app.get("/skill.md", response_class=PlainTextResponse)
def get_skill_md():
    """Return the SKILL.md directly so agents can self-discover."""
    skill_path = os.path.join(os.path.dirname(__file__), "SKILL.md")
    try:
        with open(skill_path) as f:
            return f.read()
    except Exception:
        return "# Aegis Escrow & AI Arbitration\nSee https://github.com/anilchowdary07/aegis-escrow-skill"

@app.post("/api/v1/escrow/create", response_model=EscrowRecord)
def create_escrow(req: EscrowCreate):
    """Create a new escrow contract between a buyer and seller agent."""
    escrow_id = str(uuid.uuid4())
    now = _now()
    record = EscrowRecord(
        escrow_id=escrow_id,
        buyer_id=req.buyer_id,
        seller_id=req.seller_id,
        amount=req.amount,
        terms_hash=req.terms_hash,
        description=req.description or "",
        created_at=now,
        updated_at=now
    )
    db[escrow_id] = record
    _update_reputation(req.buyer_id, "created")
    _update_reputation(req.seller_id, "created")
    return record

@app.post("/api/v1/escrow/deposit", response_model=EscrowRecord)
def deposit_funds(req: EscrowDeposit):
    """Buyer deposits funds to activate the escrow."""
    if req.escrow_id not in db:
        raise HTTPException(status_code=404, detail="Escrow not found")
    record = db[req.escrow_id]
    if record.status != "AWAITING_FUNDS":
        raise HTTPException(status_code=400, detail=f"Cannot deposit, status is {record.status}")
    if req.amount < record.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds deposited")
    record.funded = True
    record.status = "ACTIVE"
    record.updated_at = _now()
    return record

@app.post("/api/v1/escrow/release", response_model=EscrowRecord)
def release_funds(req: EscrowAction):
    """Buyer releases funds to seller upon successful delivery."""
    if req.escrow_id not in db:
        raise HTTPException(status_code=404, detail="Escrow not found")
    record = db[req.escrow_id]
    if record.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Escrow must be ACTIVE to release")
    if req.agent_id != record.buyer_id:
        raise HTTPException(status_code=403, detail="Only the buyer can release funds")
    record.status = "COMPLETED"
    record.updated_at = _now()
    record.receipt_hash = _generate_receipt(record.escrow_id, "COMPLETED", record.terms_hash)
    _update_reputation(record.buyer_id, "completed")
    _update_reputation(record.seller_id, "completed")
    return record

@app.post("/api/v1/escrow/dispute")
def open_dispute(req: DisputeAction):
    """Trigger AI arbitration if a party disputes the transaction."""
    if req.escrow_id not in db:
        raise HTTPException(status_code=404, detail="Escrow not found")
    record = db[req.escrow_id]
    if record.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Can only dispute ACTIVE escrows")
    if req.plaintiff_id not in (record.buyer_id, record.seller_id):
        raise HTTPException(status_code=403, detail="Only involved parties can dispute")

    record.status = "DISPUTED"
    ai_result = _ai_arbitrate(record.terms_hash, req.evidence_hash, req.evidence_description or "")
    decision = ai_result["decision"]
    record.status = "ARBITRATED"
    record.updated_at = _now()
    receipt = _generate_receipt(record.escrow_id, decision, req.evidence_hash)
    record.receipt_hash = receipt

    winner = record.seller_id if decision == "SELLER_FAVOR" else record.buyer_id
    loser = record.buyer_id if decision == "SELLER_FAVOR" else record.seller_id
    _update_reputation(req.plaintiff_id, "won" if winner == req.plaintiff_id else "disputed")
    _update_reputation(loser, "disputed")

    log_entry = {
        "escrow_id": record.escrow_id,
        "decision": decision,
        "confidence": ai_result["confidence"],
        "timestamp": _now()
    }
    arbitration_log.append(log_entry)

    return {
        "escrow_id": record.escrow_id,
        "arbitration_status": "COMPLETED",
        "decision": decision,
        "confidence": ai_result["confidence"],
        "reasoning": ai_result["reasoning"],
        "funds_awarded_to": winner,
        "receipt_hash": receipt,
        "verifiable": True
    }

@app.get("/api/v1/escrow/{escrow_id}", response_model=EscrowRecord)
def get_escrow(escrow_id: str):
    """Fetch the current state of an escrow by ID."""
    if escrow_id not in db:
        raise HTTPException(status_code=404, detail="Escrow not found")
    return db[escrow_id]

@app.get("/api/v1/escrows")
def list_escrows(status: Optional[str] = None, agent_id: Optional[str] = None):
    """List all escrows, optionally filtered by status or agent_id."""
    results = list(db.values())
    if status:
        results = [e for e in results if e.status == status]
    if agent_id:
        results = [e for e in results if agent_id in (e.buyer_id, e.seller_id)]
    return {"count": len(results), "escrows": results}

@app.get("/api/v1/reputation/{agent_id}")
def get_reputation(agent_id: str):
    """Get the trust score and escrow history for an agent."""
    if agent_id not in reputation_db:
        return {"agent_id": agent_id, "total_escrows": 0, "trust_score": 5.0, "message": "No history yet"}
    rep = reputation_db[agent_id]
    return {**rep, "trust_score": rep.get("trust_score", 5.0)}

@app.get("/api/v1/arbitration/log")
def get_arbitration_log():
    """Return the public log of all arbitration decisions."""
    return {"count": len(arbitration_log), "decisions": arbitration_log[-20:]}

@app.post("/api/v1/escrow/{escrow_id}/cancel")
def cancel_escrow(escrow_id: str, agent_id: str):
    """Cancel an escrow that has not yet been funded."""
    if escrow_id not in db:
        raise HTTPException(status_code=404, detail="Escrow not found")
    record = db[escrow_id]
    if record.status != "AWAITING_FUNDS":
        raise HTTPException(status_code=400, detail="Can only cancel AWAITING_FUNDS escrows")
    if agent_id not in (record.buyer_id, record.seller_id):
        raise HTTPException(status_code=403, detail="Only involved parties can cancel")
    record.status = "CANCELLED"
    record.updated_at = _now()
    return {"message": "Escrow cancelled", "escrow_id": escrow_id}
