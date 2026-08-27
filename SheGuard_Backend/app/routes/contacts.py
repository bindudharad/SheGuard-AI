from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import ContactCreate
from app.database import get_db
from app.models import EmergencyContact, User
from app.services.auth import get_current_user


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
def add_contact(payload: ContactCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if payload.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Cannot add a contact for another user")
    if not db.get(User, payload.user_id):
        raise HTTPException(status_code=404, detail="User not found")
    contact = EmergencyContact(**payload.dict())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact_out(contact)


@router.get("/contacts/{user_id}")
def list_contacts(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Cannot view another user's contacts")
    rows = db.scalars(select(EmergencyContact).where(EmergencyContact.user_id == user_id).order_by(EmergencyContact.contact_id.desc())).all()
    return {"count": len(rows), "contacts": [contact_out(row) for row in rows]}
