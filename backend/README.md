# DocuSec Backend Server

Complete backend server setup for DocuSec document security system with PostgreSQL database running in Docker containers.

## 🎯 Purpose

This backend server provides:

- **REST API** for document management and security
- **PostgreSQL Database** with automatic schema creation
- **User Authentication** with role-based access control (RBAC)
- **Document Classification** and permission management
- **Audit Logging** for security and access tracking
- **Docker Containerization** for easy deployment

## 📁 What's Included

```
backend/
├── setup_backend_server.ps1    # Automated setup script
├── manage_backend.ps1           # Management helper script
├── DEPLOYMENT_GUIDE.md          # Comprehensive deployment guide
├── .env.example                 # Environment configuration template
├── docker-compose.backend.yml   # Auto-generated Docker config
├── Dockerfile                   # Backend container definition
├── requirements.txt             # Python dependencies
├── app/                         # FastAPI application
│   ├── main.py                  # Application entry point
│   ├── models.py                # SQLAlchemy database models
│   ├── database.py              # Database connection
│   ├── crud.py                  # Database operations
│   ├── schemas.py               # Pydantic models
│   ├── rbac.py                  # Role-based access control
│   ├── dependencies.py          # FastAPI dependencies
│   └── routers/                 # API route handlers
└── ml/                          # Machine learning models
```

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

```powershell
# 1. Navigate to backend folder
cd C:\path\to\docuSec\backend

# 2. Run setup script
.\setup_backend_server.ps1
```

That's it! The script will:

- ✅ Verify Docker installation
- ✅ Create configuration files
- ✅ Build and start containers
- ✅ Initialize database schema
- ✅ Display server IP address

### Option 2: Manual Setup

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed manual setup instructions.

## 🛠️ Management Commands

Use the management script for common operations:

```powershell
# Start services
.\manage_backend.ps1 start

# Stop services
.\manage_backend.ps1 stop

# Restart services
.\manage_backend.ps1 restart

# View live logs
.\manage_backend.ps1 logs

# Check status
.\manage_backend.ps1 status

# Update backend code
.\manage_backend.ps1 update

# Backup database
.\manage_backend.ps1 backup

# Show server IP
.\manage_backend.ps1 ip

# Show all commands
.\manage_backend.ps1 help
```

## 🗄️ Database Schema

The database schema is **automatically created** from SQLAlchemy models in `app/models.py`. No manual SQL execution required!

### Tables Created

1. **departments** - Organization departments
2. **users** - User accounts with roles (user/admin)
3. **documents** - Uploaded documents with metadata
4. **document_permissions** - Document sharing permissions
5. **access_logs** - Document access audit trail
6. **security_logs** - Security events log

### Enums

- **ClassificationLevel**: public, internal, confidential, unclassified
- **PermissionLevel**: view, edit
- **UserRole**: user, admin

## 🔌 API Endpoints

Once running, access the API at:

- **Root**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Main Endpoints

- `POST /auth/register` - Register new user
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `GET /dashboard/stats` - Dashboard statistics
- `POST /documents/upload` - Upload document
- `GET /documents/` - List documents
- `GET /admin/users` - Admin: List users (admin only)
- `GET /security/logs` - Security logs (admin only)

## 🌐 Network Access

### Local Access

```
http://localhost:8000
```

### Remote Access (from other PCs)

1. **Find server IP**:

   ```powershell
   .\manage_backend.ps1 ip
   ```

2. **Configure firewall** (if needed):

   ```powershell
   New-NetFirewallRule -DisplayName "DocuSec Backend" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
   ```

3. **Update frontend** to use server IP:
   ```python
   API_BASE_URL = "http://192.168.1.100:8000"  # Replace with actual IP
   ```

## 🔐 Security Configuration

### Environment Variables (.env)

```env
# Database Configuration
DATABASE_URL=postgresql+asyncpg://docusec_user:securepassword123@db:5432/docu_security_db

# Security - CHANGE THIS!
SECRET_KEY=your-random-secret-key-minimum-32-chars

# Application Settings
ENVIRONMENT=production
DEBUG=false

# Database Credentials
POSTGRES_DB=docu_security_db
POSTGRES_USER=docusec_user
POSTGRES_PASSWORD=securepassword123
```

**Important:**

- Change `SECRET_KEY` to a random 32+ character string
- Update passwords for production use
- Never commit `.env` file to version control

## 📊 Monitoring

### View Logs

```powershell
# All services
docker-compose -f docker-compose.backend.yml logs -f

# Backend only
docker-compose -f docker-compose.backend.yml logs backend

# Database only
docker-compose -f docker-compose.backend.yml logs db
```

### Check Service Status

```powershell
# Using management script
.\manage_backend.ps1 status

# Or directly
docker-compose -f docker-compose.backend.yml ps
```

### Health Checks

The backend includes automatic health checks:

- **Backend**: Checks HTTP endpoint every 30 seconds
- **Database**: Checks PostgreSQL readiness every 10 seconds

## 💾 Backup & Restore

### Backup Database

```powershell
# Using management script
.\manage_backend.ps1 backup

# Or manually
docker exec docusec-postgres pg_dump -U docusec_user docu_security_db > backup.sql
```

### Restore Database

```powershell
# Restore from backup
Get-Content backup.sql | docker exec -i docusec-postgres psql -U docusec_user -d docu_security_db
```

## 🔄 Updates

### Update Backend Code

After making code changes:

```powershell
# Using management script
.\manage_backend.ps1 update

# Or manually
docker-compose -f docker-compose.backend.yml up -d --build backend
```

### Update Dependencies

1. Edit `requirements.txt`
2. Rebuild container:
   ```powershell
   docker-compose -f docker-compose.backend.yml up -d --build backend
   ```

## 🐛 Troubleshooting

### Backend Won't Start

```powershell
# Check logs
docker-compose -f docker-compose.backend.yml logs backend

# Verify database is ready
docker-compose -f docker-compose.backend.yml logs db
```

### Database Connection Failed

1. Verify `.env` file exists with correct credentials
2. Check database container is running and healthy
3. Ensure DATABASE_URL uses `@db:5432` (not `@localhost`)

### Port Already in Use

```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process
taskkill /PID <PID> /F
```

### Can't Access from Other Computers

1. Check firewall settings
2. Verify server IP address
3. Test connection: `curl http://<SERVER-IP>:8000`
4. Ensure Docker containers are running

### Database Schema Issues

The schema is created automatically. If there are issues:

```powershell
# Recreate everything (WARNING: Deletes all data!)
docker-compose -f docker-compose.backend.yml down -v
docker-compose -f docker-compose.backend.yml up -d --build
```

## 🗑️ Cleanup

### Stop Services (Keep Data)

```powershell
.\manage_backend.ps1 stop
```

### Remove Everything (Delete All Data)

```powershell
.\manage_backend.ps1 cleanup
```

Or manually:

```powershell
docker-compose -f docker-compose.backend.yml down -v
```

## 📋 System Requirements

- **OS**: Windows 10/11 (64-bit)
- **RAM**: 4GB minimum (8GB recommended)
- **Disk**: 10GB free space
- **Docker Desktop**: Latest version
- **Network**: Static IP or DHCP reservation recommended for server

## 🔧 Advanced Configuration

### Custom Ports

Edit `docker-compose.backend.yml`:

```yaml
backend:
  ports:
    - "8001:8000" # External:Internal

db:
  ports:
    - "5433:5432" # External:Internal
```

### Production Deployment

For production use:

1. Use strong passwords
2. Enable HTTPS (use nginx reverse proxy)
3. Set `DEBUG=false` in `.env`
4. Regular backups
5. Monitor logs
6. Restrict firewall rules

## 📖 Additional Resources

- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Comprehensive deployment guide
- [API Documentation](http://localhost:8000/docs) - Interactive API docs (when running)
- Docker Desktop Documentation - https://docs.docker.com/desktop/

## 📞 Support

For issues:

1. Check logs: `.\manage_backend.ps1 logs`
2. Check status: `.\manage_backend.ps1 status`
3. Review [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
4. Verify Docker Desktop is running

## 📄 License

Part of the DocuSec document security system.

---

## Quick Command Reference

```powershell
# Setup
.\setup_backend_server.ps1

# Management
.\manage_backend.ps1 start|stop|restart|logs|status|update|backup|ip|help

# Docker Compose (Manual)
docker-compose -f docker-compose.backend.yml up -d --build
docker-compose -f docker-compose.backend.yml down
docker-compose -f docker-compose.backend.yml logs -f
docker-compose -f docker-compose.backend.yml ps

# Database Access
docker exec -it docusec-postgres psql -U docusec_user -d docu_security_db
```
