"""
DocuSec Database Seeding Script
================================
Creates initial admin user, test users, and departments for development.

Usage:
    python seed_data.py [--clean]

Options:
    --clean     Remove all existing data before seeding (WARNING: Destructive!)
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.database import async_session, engine, Base
from app.models import User, Department, UserRole
from app.crud import get_password_hash
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession


# Seed data configuration
SEED_CONFIG = {
    "admin": {
        "username": "admin",
        "email": "admin@docusec.com",
        "password": "Admin@123",
        "first_name": "System",
        "last_name": "Administrator",
        "role": "admin",
        "department": "IT"
    },
    "users": [
        {
            "username": "john.doe",
            "email": "john.doe@docusec.com",
            "password": "User@123",
            "first_name": "John",
            "last_name": "Doe",
            "role": "user",
            "department": "Engineering"
        },
        {
            "username": "jane.smith",
            "email": "jane.smith@docusec.com",
            "password": "User@123",
            "first_name": "Jane",
            "last_name": "Smith",
            "role": "user",
            "department": "HR"
        },
        {
            "username": "bob.wilson",
            "email": "bob.wilson@docusec.com",
            "password": "User@123",
            "first_name": "Bob",
            "last_name": "Wilson",
            "role": "user",
            "department": "Finance"
        },
        {
            "username": "alice.brown",
            "email": "alice.brown@docusec.com",
            "password": "User@123",
            "first_name": "Alice",
            "last_name": "Brown",
            "role": "user",
            "department": "Marketing"
        },
        {
            "username": "charlie.davis",
            "email": "charlie.davis@docusec.com",
            "password": "User@123",
            "first_name": "Charlie",
            "last_name": "Davis",
            "role": "user",
            "department": "Engineering"
        }
    ],
    "departments": [
        "IT",
        "Engineering",
        "HR",
        "Finance",
        "Marketing",
        "Operations",
        "Legal",
        "Executive"
    ]
}


async def clean_database(db: AsyncSession):
    """Remove all existing data (WARNING: Destructive!)"""
    print("\n⚠️  WARNING: Cleaning all existing data...")
    
    # Delete in order to respect foreign key constraints
    await db.execute(delete(User))
    await db.execute(delete(Department))
    await db.commit()
    
    print("✓ All existing data removed")


async def create_departments(db: AsyncSession):
    """Create departments"""
    print("\n📁 Creating departments...")
    
    created_count = 0
    for dept_name in SEED_CONFIG["departments"]:
        # Check if department already exists
        result = await db.execute(
            select(Department).where(Department.name == dept_name)
        )
        existing_dept = result.scalar_one_or_none()
        
        if existing_dept:
            print(f"  ⏭️  Department '{dept_name}' already exists, skipping")
            continue
        
        department = Department(name=dept_name)
        db.add(department)
        created_count += 1
        print(f"  ✓ Created department: {dept_name}")
    
    await db.commit()
    print(f"\n✓ Created {created_count} department(s)")


async def create_admin(db: AsyncSession):
    """Create admin user"""
    print("\n👤 Creating admin user...")
    
    admin_data = SEED_CONFIG["admin"]
    
    # Check if admin already exists
    result = await db.execute(
        select(User).where(User.username == admin_data["username"])
    )
    existing_admin = result.scalar_one_or_none()
    
    if existing_admin:
        print(f"  ⏭️  Admin user '{admin_data['username']}' already exists, skipping")
        return
    
    # Get department
    result = await db.execute(
        select(Department).where(Department.name == admin_data["department"])
    )
    department = result.scalar_one_or_none()
    
    if not department:
        print(f"  ⚠️  Department '{admin_data['department']}' not found, creating admin without department")
    
    admin_user = User(
        username=admin_data["username"],
        email=admin_data["email"],
        hashed_password=get_password_hash(admin_data["password"]),
        first_name=admin_data["first_name"],
        last_name=admin_data["last_name"],
        role=UserRole.admin,
        department_id=department.id if department else None
    )
    
    db.add(admin_user)
    await db.commit()
    
    print(f"  ✓ Created admin user: {admin_data['username']}")
    print(f"    Email: {admin_data['email']}")
    print(f"    Password: {admin_data['password']}")
    print(f"    Role: {admin_data['role']}")


async def create_users(db: AsyncSession):
    """Create test users"""
    print("\n👥 Creating test users...")
    
    created_count = 0
    for user_data in SEED_CONFIG["users"]:
        # Check if user already exists
        result = await db.execute(
            select(User).where(User.username == user_data["username"])
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            print(f"  ⏭️  User '{user_data['username']}' already exists, skipping")
            continue
        
        # Get department
        result = await db.execute(
            select(Department).where(Department.name == user_data["department"])
        )
        department = result.scalar_one_or_none()
        
        user = User(
            username=user_data["username"],
            email=user_data["email"],
            hashed_password=get_password_hash(user_data["password"]),
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            role=UserRole.user,
            department_id=department.id if department else None
        )
        
        db.add(user)
        created_count += 1
        print(f"  ✓ Created user: {user_data['username']} ({user_data['department']})")
    
    await db.commit()
    print(f"\n✓ Created {created_count} user(s)")


async def display_summary(db: AsyncSession):
    """Display summary of created data"""
    print("\n" + "="*60)
    print("📊 DATABASE SEED SUMMARY")
    print("="*60)
    
    # Count departments
    result = await db.execute(select(Department))
    departments = result.scalars().all()
    print(f"\n📁 Departments: {len(departments)}")
    for dept in departments:
        print(f"  • {dept.name}")
    
    # Count and list users
    result = await db.execute(select(User))
    users = result.scalars().all()
    print(f"\n👥 Users: {len(users)}")
    
    # Admin users
    admin_users = [u for u in users if u.role == UserRole.admin]
    print(f"\n  Admins ({len(admin_users)}):")
    for user in admin_users:
        print(f"    • {user.username} ({user.email}) - {user.department.name if user.department else 'No Dept'}")
    
    # Regular users
    regular_users = [u for u in users if u.role == UserRole.user]
    print(f"\n  Regular Users ({len(regular_users)}):")
    for user in regular_users:
        print(f"    • {user.username} ({user.email}) - {user.department.name if user.department else 'No Dept'}")
    
    print("\n" + "="*60)
    print("✓ SEEDING COMPLETE!")
    print("="*60)
    print("\n🔐 Default Credentials:")
    print(f"  Admin:  username='admin' password='Admin@123'")
    print(f"  Users:  username='<username>' password='User@123'")
    print("\n📝 Note: Please change default passwords in production!")
    print("")


async def seed_database(clean: bool = False):
    """Main seeding function"""
    print("\n" + "="*60)
    print("🌱 DocuSec Database Seeding Script")
    print("="*60)
    
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed data
    async with async_session() as db:
        try:
            if clean:
                await clean_database(db)
            
            await create_departments(db)
            await create_admin(db)
            await create_users(db)
            await display_summary(db)
            
        except Exception as e:
            print(f"\n✗ Error during seeding: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            sys.exit(1)


def main():
    """Entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed DocuSec database with initial data")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove all existing data before seeding (WARNING: Destructive!)"
    )
    
    args = parser.parse_args()
    
    if args.clean:
        print("\n⚠️  WARNING: You are about to delete ALL existing data!")
        confirm = input("Type 'DELETE' to confirm: ")
        if confirm != "DELETE":
            print("Aborted.")
            sys.exit(0)
    
    # Run seeding
    asyncio.run(seed_database(clean=args.clean))


if __name__ == "__main__":
    main()
