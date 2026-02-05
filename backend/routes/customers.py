"""Customer CRUD endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.db_models import Customer
from models.schemas import CustomerCreate, CustomerResponse

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.post("", response_model=CustomerResponse)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    """Create a new customer."""
    existing = db.query(Customer).filter(Customer.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Customer with this name already exists")

    customer = Customer(name=data.name)
    db.add(customer)
    db.commit()
    db.refresh(customer)

    return CustomerResponse(
        id=customer.id,
        name=customer.name,
        created_at=customer.created_at,
        reference_doc_count=0,
        document_count=0,
    )


@router.get("", response_model=list[CustomerResponse])
def list_customers(db: Session = Depends(get_db)):
    """List all customers."""
    customers = db.query(Customer).order_by(Customer.name).all()
    return [
        CustomerResponse(
            id=c.id,
            name=c.name,
            created_at=c.created_at,
            reference_doc_count=len(c.reference_documents),
            document_count=len(c.documents),
        )
        for c in customers
    ]


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """Get a customer with doc counts."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return CustomerResponse(
        id=customer.id,
        name=customer.name,
        created_at=customer.created_at,
        reference_doc_count=len(customer.reference_documents),
        document_count=len(customer.documents),
    )


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    """Delete a customer and cascade to reference docs. Documents are unlinked (customer_id set to null)."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Unlink documents (don't delete them)
    for doc in customer.documents:
        doc.customer_id = None

    db.delete(customer)
    db.commit()
    return {"message": "Customer deleted"}
