from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from passlib.context import CryptContext
from typing import Optional, List
from . import models, schemas

# Use pbkdf2_sha256 instead of bcrypt to avoid the 72-byte limitation
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"], 
    deprecated="auto"
)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(models.User).where(models.User.username == username))
    return result.scalars().first()

async def create_user(db: AsyncSession, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        username=user.username, 
        hashed_password=hashed_password, 
        department_id=user.department_id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def authenticate_user(db: AsyncSession, username: str, password: str):
    user = await get_user_by_username(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

async def update_user_password(db: AsyncSession, user_id: int, new_password: str) -> bool:
    """Update user password with new hashed password."""
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        return False
    
    user.hashed_password = get_password_hash(new_password)
    await db.commit()
    return True

async def get_user_by_id(db: AsyncSession, user_id: int):
    """Get user by ID."""
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    return result.scalars().first()

async def update_user(db: AsyncSession, user_id: int, user_update: dict):
    """Update user profile information."""
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        return None
    
    # Update fields
    for key, value in user_update.items():
        if hasattr(user, key) and key != 'id' and key != 'hashed_password':
            setattr(user, key, value)
    
    await db.commit()
    await db.refresh(user)
    return user

async def delete_user(db: AsyncSession, user_id: int) -> bool:
    """Delete a user by ID."""
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        return False
    
    await db.delete(user)
    await db.commit()
    return True

async def create_department(db: AsyncSession, department: schemas.DepartmentCreate):
    db_dept = models.Department(name=department.name)
    db.add(db_dept)
    await db.commit()
    await db.refresh(db_dept)
    return db_dept

async def get_departments(db: AsyncSession):
    result = await db.execute(select(models.Department))
    return result.scalars().all()

async def update_department(db: AsyncSession, dept_id: int, name: str):
    result = await db.execute(select(models.Department).where(models.Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        return None
    dept.name = name
    await db.commit()
    await db.refresh(dept)
    return dept

async def delete_department(db: AsyncSession, dept_id: int):
    result = await db.execute(select(models.Department).where(models.Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        return False
    # Unassign users from this department before deleting
    await db.execute(
        models.User.__table__.update()
        .where(models.User.department_id == dept_id)
        .values(department_id=None)
    )
    await db.delete(dept)
    await db.commit()
    return True

async def get_all_users(db: AsyncSession, exclude_user_id: Optional[int] = None, search: Optional[str] = None):
    """Get all users with optional search and exclusion."""
    query = select(models.User)
    
    # Exclude specific user (typically the current user)
    if exclude_user_id:
        query = query.where(models.User.id != exclude_user_id)
    
    # Search by username, first name, last name, or email
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (models.User.username.ilike(search_pattern)) |
            (models.User.first_name.ilike(search_pattern)) |
            (models.User.last_name.ilike(search_pattern)) |
            (models.User.email.ilike(search_pattern))
        )
    
    result = await db.execute(query)
    return result.scalars().all()

async def authorize_document_action(db: AsyncSession, document_id: int, current_user: models.User, required_action: str):
    # Fetch document with owner and department tags
    result = await db.execute(
        select(models.Document)
        .options(
            selectinload(models.Document.owner),
            selectinload(models.Document.document_departments).selectinload(models.DocumentDepartment.department),
        )
        .where(models.Document.id == document_id)
    )
    document = result.scalars().first()
    if not document:
        print(f"🔍 AUTH DEBUG: Document {document_id} not found")
        return False, "Document not found"

    owner = document.owner
    current_user_dept = current_user.department_id
    owner_dept = owner.department_id

    # Build set of department IDs tagged on this document
    doc_dept_ids = {dd.department_id for dd in document.document_departments}

    # Check permissions based on classification and action
    classification = document.classification

    print(f"🔍 AUTH DEBUG: Doc={document_id}, Classification={classification.value}, Action={required_action}")
    print(f"🔍 AUTH DEBUG: Current User={current_user.id}, Dept={current_user_dept}")
    print(f"🔍 AUTH DEBUG: Owner={owner.id}, Dept={owner_dept}, Doc Depts={doc_dept_ids}")

    if required_action == 'view':
        if classification == models.ClassificationLevel.public:
            print(f"✅ AUTH: PUBLIC document - access granted")
            return True, None
        elif classification == models.ClassificationLevel.internal:
            print(f"🔍 AUTH: INTERNAL document check")
            # Owner always has access
            if current_user.id == owner.id:
                print(f"✅ AUTH: User is owner - access granted")
                return True, None
            # Check if user's department is in the document's tagged departments
            if current_user_dept and doc_dept_ids and current_user_dept in doc_dept_ids:
                print(f"✅ AUTH: User's department is in document's tagged departments - access granted")
                return True, None
            # Fallback: if no department tags, check owner's department (backward compat)
            if not doc_dept_ids and current_user_dept == owner_dept:
                print(f"✅ AUTH: No department tags, falling back to owner dept match - access granted")
                return True, None
            print(f"❌ AUTH: Department mismatch and not owner - access denied")
            return False, "Access denied: Internal document - requires matching department"
        elif classification in [models.ClassificationLevel.confidential, models.ClassificationLevel.unclassified]:
            print(f"🔍 AUTH: CONFIDENTIAL/UNCLASSIFIED document check")
            # Check if owner or has explicit permission
            if current_user.id == owner.id:
                print(f"✅ AUTH: User is owner - access granted")
                return True, None
            perm_result = await db.execute(
                select(models.DocumentPermission).where(
                    models.DocumentPermission.document_id == document_id,
                    models.DocumentPermission.user_id == current_user.id
                )
            )
            perm = perm_result.scalars().first()
            if perm:
                print(f"✅ AUTH: User has explicit permission - access granted")
                return True, None
            print(f"❌ AUTH: Not owner and no explicit permission - access denied")
            return False, "Access denied: Confidential document - requires owner or explicit permission"

    elif required_action in ['edit', 'delete']:
        if current_user.id == owner.id:
            print(f"✅ AUTH: User is owner - edit/delete granted")
            return True, None
        print(f"❌ AUTH: Only owner can edit/delete - access denied")
        return False, "Only owner can edit or delete"

    print(f"❌ AUTH: Invalid action '{required_action}'")
    return False, "Invalid action"

async def create_document(db: AsyncSession, document: schemas.DocumentCreate, owner_id: int, file_path: str):
    db_doc = models.Document(
        filename=document.filename,
        file_path=file_path,
        owner_id=owner_id,
        classification=document.classification
    )
    db.add(db_doc)
    await db.commit()
    await db.refresh(db_doc)
    return db_doc

async def get_documents_for_user(db: AsyncSession, current_user: models.User):
    # Get all documents user can view
    documents = []

    # Public documents
    result = await db.execute(
        select(models.Document)
        .options(
            selectinload(models.Document.owner),
            selectinload(models.Document.document_departments).selectinload(models.DocumentDepartment.department),
        )
        .where(models.Document.classification == models.ClassificationLevel.public)
    )
    documents.extend(result.scalars().all())

    # Internal documents from document's tagged departments (not owner)
    if current_user.department_id:
        result = await db.execute(
            select(models.Document)
            .options(
                selectinload(models.Document.owner),
                selectinload(models.Document.document_departments).selectinload(models.DocumentDepartment.department),
            )
            .join(models.DocumentDepartment, models.Document.id == models.DocumentDepartment.document_id)
            .where(
                models.Document.classification == models.ClassificationLevel.internal,
                models.Document.owner_id != current_user.id,
                models.DocumentDepartment.department_id == current_user.department_id,
            )
        )
        documents.extend(result.scalars().all())

        # Fallback: internal docs with NO department tags but owner in same department
        result = await db.execute(
            select(models.Document)
            .options(
                selectinload(models.Document.owner),
                selectinload(models.Document.document_departments).selectinload(models.DocumentDepartment.department),
            )
            .where(
                models.Document.classification == models.ClassificationLevel.internal,
                models.Document.owner_id != current_user.id,
                models.Document.owner.has(models.User.department_id == current_user.department_id),
                ~models.Document.document_departments.any(),
            )
        )
        documents.extend(result.scalars().all())

    # Confidential/unclassified: owned or shared
    result = await db.execute(
        select(models.Document)
        .options(
            selectinload(models.Document.owner),
            selectinload(models.Document.document_departments).selectinload(models.DocumentDepartment.department),
        )
        .where(
            models.Document.classification.in_([models.ClassificationLevel.confidential, models.ClassificationLevel.unclassified]),
            (models.Document.owner_id == current_user.id) |
            models.Document.document_permissions.any(models.DocumentPermission.user_id == current_user.id)
        )
    )
    documents.extend(result.scalars().all())

    # Remove duplicates
    seen = set()
    unique_docs = []
    for doc in documents:
        if doc.id not in seen:
            seen.add(doc.id)
            unique_docs.append(doc)
    return unique_docs

async def get_documents_by_owner(db: AsyncSession, owner_id: int):
    result = await db.execute(
        select(models.Document)
        .options(
            selectinload(models.Document.owner),
            selectinload(models.Document.document_departments).selectinload(models.DocumentDepartment.department),
        )
        .where(models.Document.owner_id == owner_id)
    )
    return result.scalars().all()

async def get_shared_documents_for_user(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(models.Document)
        .join(models.DocumentPermission)
        .where(models.DocumentPermission.user_id == user_id)
        .options(
            selectinload(models.Document.owner),
            selectinload(models.Document.document_departments).selectinload(models.DocumentDepartment.department),
        )
    )
    return result.scalars().all()

async def get_department_documents(db: AsyncSession, department_id: int, user_id: int):
    # Get all documents tagged with this department (via AI-inferred DocumentDepartment)
    # Only includes: public, internal, and unclassified documents
    # Confidential documents require explicit sharing permissions
    result = await db.execute(
        select(models.Document)
        .join(models.DocumentDepartment, models.Document.id == models.DocumentDepartment.document_id)
        .where(
            models.DocumentDepartment.department_id == department_id,
            models.Document.classification.in_([
                models.ClassificationLevel.public,
                models.ClassificationLevel.internal,
                models.ClassificationLevel.unclassified
            ])
        )
        .options(
            selectinload(models.Document.owner),
            selectinload(models.Document.document_departments).selectinload(models.DocumentDepartment.department),
        )
    )
    dept_docs = list(result.scalars().all())

    # Fallback: also include documents with NO department tags from users in the same department
    result = await db.execute(
        select(models.Document)
        .join(models.User, models.Document.owner_id == models.User.id)
        .where(
            models.User.department_id == department_id,
            models.Document.classification.in_([
                models.ClassificationLevel.public,
                models.ClassificationLevel.internal,
                models.ClassificationLevel.unclassified
            ]),
            ~models.Document.document_departments.any(),
        )
        .options(
            selectinload(models.Document.owner),
            selectinload(models.Document.document_departments).selectinload(models.DocumentDepartment.department),
        )
    )
    fallback_docs = result.scalars().all()

    # Merge and deduplicate
    seen = {d.id for d in dept_docs}
    for doc in fallback_docs:
        if doc.id not in seen:
            dept_docs.append(doc)
            seen.add(doc.id)

    return dept_docs

async def get_document(db: AsyncSession, doc_id: int):
    result = await db.execute(
        select(models.Document).where(models.Document.id == doc_id)
    )
    return result.scalars().first()

async def user_can_access_document(db: AsyncSession, user_id: int, doc_id: int):
    doc = await get_document(db, doc_id)
    if not doc:
        return False
    
    if doc.owner_id == user_id:
        return True

    if doc.classification == models.ClassificationLevel.public:
        return True

    user = await db.get(models.User, user_id)
    if not user:
        return False

    if doc.classification == models.ClassificationLevel.internal:
        # Check if user's department is in doc's tagged departments
        if user.department_id:
            dept_tag = await db.execute(
                select(models.DocumentDepartment).where(
                    models.DocumentDepartment.document_id == doc_id,
                    models.DocumentDepartment.department_id == user.department_id,
                )
            )
            if dept_tag.scalars().first():
                return True
        # Fallback: check owner's department (for untagged docs)
        owner = await db.get(models.User, doc.owner_id)
        if owner and owner.department_id == user.department_id:
            # Only use fallback if doc has no department tags
            has_tags = await db.execute(
                select(models.DocumentDepartment.id).where(
                    models.DocumentDepartment.document_id == doc_id
                ).limit(1)
            )
            if not has_tags.scalars().first():
                return True

    # Check for explicit share
    perm_result = await db.execute(
        select(models.DocumentPermission).where(
            models.DocumentPermission.document_id == doc_id,
            models.DocumentPermission.user_id == user_id
        )
    )
    if perm_result.scalars().first():
        return True

    return False

async def create_access_log(db: AsyncSession, log: schemas.AccessLogCreate):
    data = log.dict()
    # Resolve and store document_name for audit persistence
    if data.get('document_id') and not data.get('document_name'):
        result = await db.execute(
            select(models.Document.filename).where(models.Document.id == data['document_id'])
        )
        filename = result.scalar()
        if filename:
            data['document_name'] = filename
    db_log = models.AccessLog(**data)
    db.add(db_log)
    await db.commit()
    await db.refresh(db_log)
    return db_log

async def share_document(db: AsyncSession, document_id: int, permission: schemas.DocumentPermissionCreate, current_user: models.User):
    # Check if owner
    result = await db.execute(
        select(models.Document).where(models.Document.id == document_id)
    )
    doc = result.scalars().first()
    if not doc or doc.owner_id != current_user.id:
        return False, "Only owner can share"

    # Check if already shared
    existing = await db.execute(
        select(models.DocumentPermission).where(
            models.DocumentPermission.document_id == document_id,
            models.DocumentPermission.user_id == permission.user_id
        )
    )
    if existing.scalars().first():
        return False, "Already shared"

    db_perm = models.DocumentPermission(
        document_id=document_id,
        user_id=permission.user_id,
        permission=permission.permission
    )
    db.add(db_perm)
    await db.commit()
    await db.refresh(db_perm)
    return True, db_perm

async def get_document_permissions(db: AsyncSession, document_id: int, current_user: models.User):
    """Get all permissions for a document (owner only)."""
    # Check if owner
    result = await db.execute(
        select(models.Document).where(models.Document.id == document_id)
    )
    doc = result.scalars().first()
    if not doc or doc.owner_id != current_user.id:
        return False
    
    # Get all permissions with user details
    result = await db.execute(
        select(models.DocumentPermission)
        .options(selectinload(models.DocumentPermission.user))
        .where(models.DocumentPermission.document_id == document_id)
    )
    return result.scalars().all()

async def revoke_document_permission(db: AsyncSession, document_id: int, permission_id: int, current_user: models.User):
    """Revoke a document permission (owner only)."""
    # Check if owner
    result = await db.execute(
        select(models.Document).where(models.Document.id == document_id)
    )
    doc = result.scalars().first()
    if not doc or doc.owner_id != current_user.id:
        return False, "Only owner can revoke permissions"
    
    # Get the permission
    result = await db.execute(
        select(models.DocumentPermission).where(
            models.DocumentPermission.id == permission_id,
            models.DocumentPermission.document_id == document_id
        )
    )
    perm = result.scalars().first()
    if not perm:
        return False, "Permission not found"
    
    await db.delete(perm)
    await db.commit()
    return True, "Permission revoked"

async def update_document_permission(db: AsyncSession, document_id: int, permission_id: int, permission_level: str, current_user: models.User):
    """Update a document permission level (owner only)."""
    # Check if owner
    result = await db.execute(
        select(models.Document).where(models.Document.id == document_id)
    )
    doc = result.scalars().first()
    if not doc or doc.owner_id != current_user.id:
        return False, "Only owner can update permissions"
    
    # Get the permission
    result = await db.execute(
        select(models.DocumentPermission).where(
            models.DocumentPermission.id == permission_id,
            models.DocumentPermission.document_id == document_id
        )
    )
    perm = result.scalars().first()
    if not perm:
        return False, "Permission not found"
    
    # Update permission level
    if permission_level not in ['view', 'edit']:
        return False, "Invalid permission level"
    
    perm.permission = models.PermissionLevel[permission_level]
    await db.commit()
    return True, "Permission updated"

async def delete_document(db: AsyncSession, document_id: int, current_user: models.User):
    result = await db.execute(
        select(models.Document).where(models.Document.id == document_id)
    )
    doc = result.scalars().first()
    if not doc or doc.owner_id != current_user.id:
        return False, "Only owner can delete"
    await db.delete(doc)
    await db.commit()
    return True, None

async def get_dashboard_summary(db: AsyncSession, current_user: models.User):
    # Count all documents
    total_docs = await db.execute(select(func.count(models.Document.id)))
    total_documents = total_docs.scalar()

    # Count documents owned by current_user
    owned_docs = await db.execute(
        select(func.count(models.Document.id)).where(models.Document.owner_id == current_user.id)
    )
    owned_documents = owned_docs.scalar()

    # Count documents where current_user has permissions
    shared_docs = await db.execute(
        select(func.count(models.DocumentPermission.id)).where(models.DocumentPermission.user_id == current_user.id)
    )
    shared_documents = shared_docs.scalar()

    # Count department documents (public, internal, unclassified) from same department
    if current_user.department_id:
        dept_docs = await db.execute(
            select(func.count(models.Document.id))
            .join(models.User, models.Document.owner_id == models.User.id)
            .where(
                models.User.department_id == current_user.department_id,
                models.Document.classification.in_([
                    models.ClassificationLevel.public,
                    models.ClassificationLevel.internal,
                    models.ClassificationLevel.unclassified
                ])
            )
        )
        department_documents = dept_docs.scalar()
    else:
        department_documents = 0

    # Count documents by classification
    classification_counts = await db.execute(
        select(
            models.Document.classification,
            func.count(models.Document.id)
        ).group_by(models.Document.classification)
    )
    classification_summary = {row[0].value: row[1] for row in classification_counts.all()}

    # Recent security logs (last 10)
    security_logs_result = await db.execute(
        select(models.SecurityLog)
        .options(selectinload(models.SecurityLog.user))
        .order_by(models.SecurityLog.timestamp.desc())
        .limit(10)
    )
    recent_security_logs = [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "activity_type": log.activity_type,
            "details": log.details,
            "user": {"username": log.user.username} if log.user else None
        }
        for log in security_logs_result.scalars().all()
    ]

    # Recent access logs (last 10)
    access_logs_result = await db.execute(
        select(models.AccessLog)
        .options(selectinload(models.AccessLog.user), selectinload(models.AccessLog.document))
        .order_by(models.AccessLog.access_time.desc())
        .limit(10)
    )
    recent_access_logs = [
        {
            "id": log.id,
            "timestamp": log.access_time.isoformat(),
            "action": log.action,
            "document": {"filename": log.document.filename} if log.document else None,
            "user": {"username": log.user.username} if log.user else None
        }
        for log in access_logs_result.scalars().all()
    ]

    return {
        "total_documents": total_documents,
        "owned_documents": owned_documents,
        "shared_documents": shared_documents,
        "internal_department_documents": department_documents,
        "classification_summary": classification_summary,
        "recent_security_logs": recent_security_logs,
        "recent_access_logs": recent_access_logs
    }
