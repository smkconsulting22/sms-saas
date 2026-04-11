from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactOut
from app.dependencies import get_current_tenant
from app.services.campaign import (
    import_contacts_from_csv,
    import_contacts_from_excel,
    validate_phone
)

router = APIRouter(prefix="/contacts", tags=["Contacts"])

@router.post("/", response_model=ContactOut, status_code=201)
def create_contact(
    payload: ContactCreate,
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_tenant)
):
    phone = validate_phone(payload.phone)
    if not phone:
        raise HTTPException(status_code=400, detail="Numéro invalide")

    contact = Contact(
        tenant_id=current["tenant_id"],
        phone=phone,
        full_name=payload.full_name
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact

@router.get("/", response_model=List[ContactOut])
def list_contacts(
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_tenant)
):
    return db.query(Contact).filter(
        Contact.tenant_id == current["tenant_id"]
    ).all()

@router.post("/import")
async def import_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_tenant)
):
    filename = file.filename.lower()

    if not (filename.endswith(".csv") or filename.endswith(".xlsx")):
        raise HTTPException(
            status_code=400,
            detail="Format non supporté. Utilisez .csv ou .xlsx"
        )

    content = await file.read()

    if filename.endswith(".xlsx"):
        result = import_contacts_from_excel(db, current["tenant_id"], content)
    else:
        result = import_contacts_from_csv(db, current["tenant_id"], content)

    return result

@router.delete("/{contact_id}")
def delete_contact(
    contact_id: str,
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_tenant)
):
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.tenant_id == current["tenant_id"]
    ).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact introuvable")
    db.delete(contact)
    db.commit()
    return {"message": "Contact supprimé"}

@router.post("/{contact_id}/optout")
def optout_contact(
    contact_id: str,
    db: Session = Depends(get_db),
    current: dict = Depends(get_current_tenant)
):
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.tenant_id == current["tenant_id"]
    ).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact introuvable")
    contact.is_optout = True
    db.commit()
    return {"message": "Contact désabonné"}