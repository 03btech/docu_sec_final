from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from .. import crud, schemas
from ..dependencies import get_current_user
from ..models import User

router = APIRouter()

@router.post("/departments", response_model=schemas.Department)
async def create_department(department: schemas.DepartmentCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # For now, allow any authenticated user to create departments; in production, add admin check
    return await crud.create_department(db, department)

@router.get("/departments", response_model=list[schemas.Department])
async def read_departments(db: AsyncSession = Depends(get_db)):
    departments = await crud.get_departments(db)
    return departments

@router.put("/departments/{dept_id}", response_model=schemas.Department)
async def update_department(dept_id: int, department: schemas.DepartmentCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    updated = await crud.update_department(db, dept_id, department.name)
    if not updated:
        raise HTTPException(status_code=404, detail="Department not found")
    return updated

@router.delete("/departments/{dept_id}")
async def delete_department(dept_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    deleted = await crud.delete_department(db, dept_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Department not found")
    return {"message": "Department deleted successfully"}
