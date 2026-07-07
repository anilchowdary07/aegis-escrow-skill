import uuid
import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional

app = FastAPI(
    title="Aegis Smart Escrow & Arbitration API",
    description="A decentralized escrow and dispute arbitration service for autonomous AI agents.",
    version="1.0.0"
)

# -----------------
# DATA MODELS
# -----------------
class EscrowCreate(BaseModel):
    buyer_id: str
    seller_id: str
    amount: float
    terms_hash: str

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

class EscrowRecord(BaseModel):
    escrow_id: str
    buyer_id: str
    seller_id: str
    amount: float
    funded: bool = False
    status: str = "AWAITING_FUNDS" # AWAITING_FUNDS, ACTIVE, COMPLETED, DISPUTED, ARBITRATED
    terms_hash: str
    created_at: str

# -----------------
# IN-MEMORY DB
# -----------------
db: Dict[str, EscrowRecord] = {}

# -----------------
# ROUTES
# -----------------

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "aegis-escrow", "timestamp": datetime.datetime.utcnow().isoformat() + "Z"}

@app.post("/api/v1/escrow/create", response_model=EscrowRecord)
def create_escrow(req: EscrowCreate):
    escrow_id = str(uuid.uuid4())
    record = EscrowRecord(
        escrow_id=escrow_id,
        buyer_id=req.buyer_id,
        seller_id=req.seller_id,
        amount=req.amount,
        terms_hash=req.terms_hash,
        created_at=datetime.datetime.utcnow().isoformat() + "Z"
    )
    db[escrow_id] = record
    return record

@app.post("/api/v1/escrow/deposit", response_model=EscrowRecord)
def deposit_funds(req: EscrowDeposit):
    if req.escrow_id not in db:
        raise HTTPException(status_code=404, detail="Escrow not found")
    
    record = db[req.escrow_id]
    if record.status != "AWAITING_FUNDS":
        raise HTTPException(status_code=400, detail=f"Cannot deposit, status is {record.status}")
        
    if req.amount < record.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds deposited")
        
    record.funded = True
    record.status = "ACTIVE"
    return record

@app.post("/api/v1/escrow/release", response_model=EscrowRecord)
def release_funds(req: EscrowAction):
    """The buyer triggers this when they are satisfied with the delivery."""
    if req.escrow_id not in db:
        raise HTTPException(status_code=404, detail="Escrow not found")
        
    record = db[req.escrow_id]
    if record.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Escrow must be ACTIVE to release")
        
    if req.agent_id != record.buyer_id:
        raise HTTPException(status_code=403, detail="Only the buyer can release funds")
        
    record.status = "COMPLETED"
    return record

@app.post("/api/v1/escrow/dispute", response_model=dict)
def open_dispute(req: DisputeAction):
    """Either party can trigger a dispute if they are unhappy."""
    if req.escrow_id not in db:
        raise HTTPException(status_code=404, detail="Escrow not found")
        
    record = db[req.escrow_id]
    if record.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Can only dispute ACTIVE escrows")
        
    if req.plaintiff_id not in (record.buyer_id, record.seller_id):
        raise HTTPException(status_code=403, detail="Only involved parties can dispute")
        
    record.status = "DISPUTED"
    
    # Triggering the AI Arbitration system (Simulated)
    # The AI evaluates the evidence_hash against the terms_hash
    decision = "SELLER_FAVOR" if "receipt" in req.evidence_hash else "BUYER_FAVOR"
    record.status = "ARBITRATED"
    
    return {
        "escrow_id": record.escrow_id,
        "arbitration_status": "COMPLETED",
        "decision": decision,
        "evidence_hash_evaluated": req.evidence_hash,
        "funds_awarded_to": record.seller_id if decision == "SELLER_FAVOR" else record.buyer_id
    }

@app.get("/api/v1/escrow/{escrow_id}", response_model=EscrowRecord)
def get_escrow(escrow_id: str):
    if escrow_id not in db:
        raise HTTPException(status_code=404, detail="Escrow not found")
    return db[escrow_id]
