# DocuSec - Document Security Management System

A comprehensive document security management system with backend (FastAPI + PostgreSQL) and frontend (PyQt6 desktop app) components.

## 🚀 Quick Start for Developers

### Prerequisites

- **Docker Desktop** installed and running
- **Python 3.10+** for frontend
- **Git** for version control

### 1. Clone the Repository

```powershell
git clone https://github.com/03btech/docu_sec_final.git
cd docu_sec_final
```

### 2. Start Backend Services (Docker)

```powershell
# Build and start Docker containers (backend + database)
.\build_docker.ps1
```

This will:
- ✅ Check Docker is running
- ✅ Create `.env` file with secure credentials
- ✅ Build Docker images
- ✅ Start PostgreSQL database
- ✅ Start FastAPI backend
- ✅ Display service URLs and status

### 3. Seed the Database

```powershell
# Create initial admin user, test users, and departments
.\seed_database.ps1
```

**Default Credentials:**
- **Admin**: username=`admin`, password=`Admin@123`
- **Users**: username=`john.doe` (and others), password=`User@123`

### 4. Run Frontend Application

```powershell
cd frontend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

---

## 📦 Docker Management

### Quick Commands

```powershell
# Build and start
.\build_docker.ps1

# Stop all containers
.\build_docker.ps1 -Stop

# Check status
.\build_docker.ps1 -Status

# View logs
.\build_docker.ps1 -Logs

# Clean rebuild (remove old data)
.\build_docker.ps1 -Clean -Rebuild
```

### Full Management Tool

```powershell
# Start containers
.\manage_docker.ps1 start

# Stop containers
.\manage_docker.ps1 stop

# Restart containers
.\manage_docker.ps1 restart

# View live logs
.\manage_docker.ps1 logs

# Check health status
.\manage_docker.ps1 status

# Backup database
.\manage_docker.ps1 backup

# Restore database
.\manage_docker.ps1 restore

# Open backend shell
.\manage_docker.ps1 shell

# Clean everything (WARNING: Destructive!)
.\manage_docker.ps1 clean

# Show all commands
.\manage_docker.ps1 help
```

---

## 🏗️ Project Structure

```
docu_sec/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI application entry point
│   │   ├── models.py          # SQLAlchemy database models
│   │   ├── crud.py            # Database operations
│   │   ├── rbac.py            # Role-based access control
│   │   ├── schemas.py         # Pydantic schemas
│   │   ├── dependencies.py    # FastAPI dependencies
│   │   └── routers/           # API route modules
│   │       ├── auth.py        # Authentication endpoints
│   │       ├── documents.py   # Document management
│   │       ├── admin.py       # Admin operations
│   │       ├── dashboard.py   # Dashboard/analytics
│   │       └── security.py    # Security logging
│   ├── ml/
│   │   └── classifier.py      # ML document classification
│   ├── seed_data.py           # Database seeding script
│   ├── Dockerfile             # Backend Docker image
│   └── requirements.txt       # Python dependencies
│
├── frontend/                   # PyQt6 desktop application
│   ├── main.py                # Application entry point
│   ├── api/
│   │   └── client.py          # Backend API client
│   ├── views/                 # UI view components
│   ├── widgets/               # Custom UI widgets
│   ├── workers/               # Background thread workers
│   ├── utils/                 # Utility functions
│   └── requirements.txt       # Python dependencies
│
├── docker-compose.yml         # Docker services configuration
├── build_docker.ps1           # Quick Docker build script
├── manage_docker.ps1          # Docker management script
└── seed_database.ps1          # Database seeding wrapper
```

---

## 🔐 Security Features

- **Authentication**: Session-based authentication with secure password hashing
- **Authorization**: Role-based access control (Admin/User roles)
- **Document Classification**: 4 levels (Public, Internal, Confidential, Unclassified)
- **ML Classification**: Automatic document classification using BART zero-shot
- **YOLOv8 Monitoring**: Real-time person/phone detection for confidential documents
- **Screen Protection**: Screen capture prevention (Windows)
- **Watermarking**: Dynamic watermarks on documents
- **Audit Logging**: Comprehensive access and security logs

---

## 🗄️ Database Schema

### Main Tables

- **users**: User accounts with roles and departments
- **departments**: Organizational departments
- **documents**: Document metadata with classification levels
- **document_permissions**: Fine-grained document sharing
- **access_logs**: Document access audit trail
- **security_logs**: Security event logging

### Classification Levels

- `public`: Accessible to all users
- `internal`: Accessible to users in same department
- `confidential`: Restricted access with enhanced security
- `unclassified`: Default classification for new documents

---

## 🌐 API Documentation

Once the backend is running, access interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🔧 Configuration

### Backend Configuration

Edit `backend/.env` file (auto-created on first run):

```env
# Database
DATABASE_URL=postgresql+asyncpg://docusec_user:infosysyrab@db:5432/docu_security_db

# Security
SECRET_KEY=<auto-generated>

# Application
ENVIRONMENT=production
DEBUG=false

# Database Credentials
POSTGRES_DB=docu_security_db
POSTGRES_USER=docusec_user
POSTGRES_PASSWORD=infosysyrab  # CHANGE IN PRODUCTION!
```

### Frontend Configuration

Edit `frontend/api/client.py` to change API base URL:

```python
self.base_url = "http://localhost:8000"  # Change for remote backend
```

---

## 📊 Development Workflow

### Starting Fresh

```powershell
# 1. Build containers
.\build_docker.ps1

# 2. Seed database
.\seed_database.ps1

# 3. Run frontend
cd frontend
python main.py
```

### Making Backend Changes

```powershell
# Edit code in backend/app/

# Restart backend container to apply changes
.\manage_docker.ps1 restart

# View logs to debug
.\manage_docker.ps1 logs
```

### Database Backups

```powershell
# Create backup
.\manage_docker.ps1 backup
# Creates: backup_YYYYMMDD_HHMMSS.sql

# Restore from backup
.\manage_docker.ps1 restore
# Shows list of available backups
```

---

## 🌍 Network Access (Multi-PC Setup)

To run backend on one PC and frontend on another:

### On Backend PC:

```powershell
# Start backend
.\build_docker.ps1

# Note the IP address shown (e.g., 192.168.1.100)
```

### On Frontend PC:

1. Edit `frontend/api/client.py`:
   ```python
   self.base_url = "http://192.168.1.100:8000"  # Use backend PC's IP
   ```

2. Run frontend:
   ```powershell
   cd frontend
   python main.py
   ```

### Firewall Configuration

On backend PC, allow port 8000:

```powershell
New-NetFirewallRule -DisplayName "DocuSec Backend" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

---

## 🐛 Troubleshooting

### Docker Issues

```powershell
# Check if Docker is running
docker ps

# Check container logs
.\manage_docker.ps1 logs

# Nuclear option: clean rebuild
.\build_docker.ps1 -Clean -Rebuild
```

### Database Issues

```powershell
# Check database health
.\manage_docker.ps1 status

# Restart database
docker restart docu_sec-db-1

# Seed fresh data
.\seed_database.ps1 -Clean  # WARNING: Deletes existing data!
```

### Frontend Issues

```powershell
# Check backend is reachable
curl http://localhost:8000

# Reinstall dependencies
cd frontend
pip install -r requirements.txt --force-reinstall

# Check Python environment
python --version  # Should be 3.10+
```

---

## 📝 Testing Accounts

After running `.\seed_database.ps1`, you'll have:

### Admin Account
- **Username**: `admin`
- **Password**: `Admin@123`
- **Email**: `admin@docusec.com`
- **Department**: IT

### Test Users
- **john.doe** (Engineering)
- **jane.smith** (HR)
- **bob.wilson** (Finance)
- **alice.brown** (Marketing)
- **charlie.davis** (Engineering)

**All test users**: password=`User@123`

---

## 🔄 Updating from Git

```powershell
# Pull latest changes
git pull origin master

# Rebuild containers
.\build_docker.ps1 -Rebuild

# Restart frontend
cd frontend
python main.py
```

---

## ⚠️ Production Deployment

**Before deploying to production:**

1. ✅ Change default passwords in `backend/.env`
2. ✅ Generate new `SECRET_KEY`
3. ✅ Set `DEBUG=false`
4. ✅ Configure proper firewall rules
5. ✅ Enable HTTPS/TLS
6. ✅ Set up automated backups
7. ✅ Review and harden security settings

---

## 📚 Additional Resources

- **Docker Documentation**: https://docs.docker.com/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **PyQt6 Documentation**: https://doc.qt.io/qtforpython/
- **SQLAlchemy Documentation**: https://docs.sqlalchemy.org/

---

## 📄 License

[Add your license information here]

---

## 🤝 Contributing

[Add contribution guidelines here]

---

## 📧 Support

For issues or questions, please create an issue on GitHub or contact the development team.
