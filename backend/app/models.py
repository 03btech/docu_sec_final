from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, Text, Enum, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base
import enum

class ClassificationLevel(enum.Enum):
    public = "public"
    internal = "internal"
    confidential = "confidential"
    unclassified = "unclassified"

# ⚠️ SYNC: Enum values and ORDER must match the CREATE TYPE classificationstatus
# statement in main.py lifespan handler. PostgreSQL enum ordering matters for
# comparisons (<, >). If you add/reorder values here, update the SQL to match.
class ClassificationStatus(enum.Enum):
    queued = "queued"
    extracting_text = "extracting_text"   # Text extraction from file
    classifying = "classifying"           # Gemini API call in progress
    completed = "completed"               # Classification done
    failed = "failed"                     # All retries exhausted

class PermissionLevel(enum.Enum):
    view = "view"
    edit = "edit"

class UserRole(enum.Enum):
    user = "user"
    admin = "admin"

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)

    users = relationship("User", back_populates="department")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.user, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    department = relationship("Department", back_populates="users")
    documents = relationship("Document", back_populates="owner")
    document_permissions = relationship("DocumentPermission", back_populates="user")
    access_logs = relationship("AccessLog", back_populates="user")
    security_logs = relationship("SecurityLog", back_populates="user")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    upload_date = Column(TIMESTAMP(timezone=True), server_default=func.now())
    classification = Column(Enum(ClassificationLevel), default=ClassificationLevel.unclassified)
    classification_status = Column(Enum(ClassificationStatus), default=ClassificationStatus.queued)
    classification_error = Column(String(500), nullable=True)
    # ⚠️ P1-REVIEW-6: Timestamp for accurate stale detection.
    # Set to NOW() when the pipeline starts, not at upload time.
    classification_queued_at = Column(TIMESTAMP(timezone=True), nullable=True)

    owner = relationship("User", back_populates="documents")
    document_permissions = relationship("DocumentPermission", back_populates="document", cascade="all, delete-orphan")
    access_logs = relationship("AccessLog", back_populates="document", cascade="all, delete-orphan")

class DocumentPermission(Base):
    __tablename__ = "document_permissions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    permission = Column(Enum(PermissionLevel), default=PermissionLevel.view)

    document = relationship("Document", back_populates="document_permissions")
    user = relationship("User", back_populates="document_permissions")

class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    access_time = Column(TIMESTAMP(timezone=True), server_default=func.now())
    action = Column(String(50), nullable=False)

    document = relationship("Document", back_populates="access_logs")
    user = relationship("User", back_populates="access_logs")

class SecurityLog(Base):
    __tablename__ = "security_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    activity_type = Column(String(100), nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now())
    details = Column('metadata', JSON, nullable=True)

    user = relationship("User", back_populates="security_logs")
