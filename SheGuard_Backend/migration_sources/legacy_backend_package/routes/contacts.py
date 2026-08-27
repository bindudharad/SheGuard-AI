from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.schemas import ContactCreate
from backend.database import get_db
from backend.models import EmergencyContact, User


router = APIRouter(tags=["contacts"])


def contact_out(row: EmergencyContact) -> dict:
    return {
        "contact_id": row.contact_id,
        "user_id": row.user_id,
        "relation": row.relation,
        "contact_name": row.contact_name,
        "phone_number": row.phone_number,
    }


@router.post("/contacts/add")
def add_contact(payload: ContactCreate, db: Session = Depends(get_db)):
    if not db.get(User, payload.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    contact = EmergencyContact(**payload.dict())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact_out(contact)


@router.get("/contacts/{user_id}")
def list_contacts(user_id: int, db: Session = Depends(get_db)):
    rows = db.scalars(select(EmergencyContact).where(EmergencyContact.user_id == user_id).order_by(EmergencyContact.contact_id.desc())).all()
    return {"count": len(rows), "contacts": [contact_out(row) for row in rows]}
