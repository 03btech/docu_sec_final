from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from .models import ClassificationLevel, PermissionLevel, UserRole

class DepartmentBase(BaseModel):
    name: str

class DepartmentCreate(DepartmentBase):
    pass

class Department(DepartmentBase):
    id: int

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    role: Optional[UserRole] = UserRole.user
    department_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    email: str
    first_name: str
    last_name: str
    username: str
    role: UserRole
    department_id: Optional[int] = None

class PasswordReset(BaseModel):
    """Schema for admin password reset"""
    new_password: str

class ProfileUpdate(BaseModel):
    """Schema for user profile update (non-admin)"""
    email: str
    first_name: str
    last_name: str
    department_id: Optional[int] = None

class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserBasic(BaseModel):
    """Basic user info for sharing/listing purposes"""
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    role: UserRole
    department_id: Optional[int] = None

    class Config:
        from_attributes = True

class DocumentBase(BaseModel):
    filename: str
    classification: Optional[ClassificationLevel] = ClassificationLevel.unclassified

class DocumentCreate(DocumentBase):
    pass

class Document(DocumentBase):
    id: int
    file_path: str
    owner_id: int
    owner: Optional[User] = None
    upload_date: datetime

    class Config:
        from_attributes = True

class DocumentPermissionBase(BaseModel):
    document_id: int
    user_id: int
    permission: PermissionLevel = PermissionLevel.view

class DocumentPermissionCreate(BaseModel):
    """Schema for creating a document permission - document_id comes from URL"""
    user_id: int
    permission: PermissionLevel = PermissionLevel.view

class DocumentPermission(DocumentPermissionBase):
    id: int

    class Config:
        from_attributes = True

class DocumentPermissionWithUser(BaseModel):
    """Document permission with user details"""
    id: int
    document_id: int
    user_id: int
    permission: PermissionLevel
    user: UserBasic

    class Config:
        from_attributes = True

class AccessLogBase(BaseModel):
    document_id: int
    user_id: int
    action: str

class AccessLogCreate(AccessLogBase):
    pass

class AccessLog(AccessLogBase):
    id: int
    access_time: datetime
    user: Optional['User'] = None
    document: Optional['Document'] = None

    class Config:
        from_attributes = True

class SecurityLogBase(BaseModel):
    user_id: Optional[int] = None
    activity_type: str
    details: Optional[dict] = None

class SecurityLogCreate(SecurityLogBase):
    metadata: Optional[dict] = None

class SecurityLog(SecurityLogBase):
    id: int
    timestamp: datetime
    user: Optional['User'] = None

    class Config:
        from_attributes = True
