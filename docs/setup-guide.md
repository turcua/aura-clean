# 🛠️ Aura - Setup Guide

Complete guide for setting up the Aura Financial Tracker application.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Docker Setup](#docker-setup)
4. [Database Setup](#database-setup)
5. [Running the Application](#running-the-application)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Configuration](#advanced-configuration)

---

## 1. Prerequisites

### System Requirements

- **OS**: Ubuntu 24.04 (or similar Linux distribution)
- **RAM**: Minimum 4GB
- **Storage**: 10GB free space
- **CPU**: 2+ cores recommended

### Software Requirements

Install the following software:

#### Docker & Docker Compose
```bash
# Update package list
sudo apt update

# Install Docker
sudo apt install docker.io -y

# Install Docker Compose
sudo apt install docker-compose -y

# Add user to docker group (to run without sudo)
sudo usermod -aG docker $USER

# Log out and log back in for group changes to take effect
```

#### Git
```bash
# Install Git
sudo apt install git -y

# Configure Git
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
```

#### Verify Installations
```bash
# Check Docker version
docker --version
# Expected: Docker version 20.10.x or higher

# Check Docker Compose version
docker-compose --version
# Expected: docker-compose version 1.29.x or higher

# Check Git version
git --version
# Expected: git version 2.x.x
```

### Windows Setup (Alternative to the Linux steps above)

Everything from Section 2 onward (cloning, `docker-compose build`/`up`, the
troubleshooting section, etc.) works identically once these prerequisites are
in place — Docker Compose commands are cross-platform. This section only
covers what's different about getting there on Windows.

#### 1. Docker Desktop

Install from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
— this bundles Docker Engine + Docker Compose, so there's no separate
`docker-compose` install step the way there is on Ubuntu. Requires **WSL2**
(Windows Subsystem for Linux); the installer normally prompts for this
automatically on first run. If it doesn't, run in an admin PowerShell:
```powershell
wsl --install
```
Needs Windows 10 (build 2004+) or Windows 11, and virtualization enabled in
BIOS (on by default on most modern hardware). A reboot is often required
after WSL2 finishes installing before Docker Desktop will start correctly.

#### 2. Git for Windows

Install from [git-scm.com/download/win](https://git-scm.com/download/win).
This also installs **Git Bash**, which is the easiest place to run every
command in the rest of this guide as-is — native PowerShell/CMD equivalents
work too, but Git Bash means nothing needs translating.

#### 3. `.env` — real credentials, not committed

`.env` is gitignored (see `.gitignore`), so a fresh `git clone` on a new
machine will **not** bring along anyone else's real Groq API keys — each
setup needs its own `.env` in the project root:
```
GROQ_API_KEY_SECURE=<your key>
GROQ_API_KEY_VULNERABLE=<your key>
```
Free keys are available at [console.groq.com](https://console.groq.com/) —
two separate keys, matching how the app is built (one per version). This
file can be skipped entirely if the AI Advisor (Solis) chat feature isn't
needed — `groq_client.py` fails gracefully ("AI advisor is not configured")
rather than crashing when no key is present.

#### 4. Verify Installations

Same commands as the Linux section above — `docker --version`,
`docker-compose --version` (or `docker compose version` on newer Docker
Desktop releases, which folded Compose into the main `docker` CLI as a
subcommand), `git --version` — all work identically in Git Bash.

#### A safety note before running the vulnerable version

`vulnerable-version/` has real, intentional vulnerabilities (SQL injection,
IDOR, etc. — that's the whole point of this half of the project). Fine on
`localhost`; don't port-forward it or expose it to an actual network —
treat it like any other deliberately-vulnerable lab target (DVWA, Juice
Shop, etc.).

---

## 2. Initial Setup

### Project Location

The project is located at:
```
/home/cosmin/projects/aura
```

### Directory Structure Verification
```bash
cd /home/cosmin/projects/aura

# List directory structure
tree -L 2
# Or if tree is not installed:
ls -R
```

Expected structure:
```
aura/
├── docker-compose.yml
├── secure-version/
├── vulnerable-version/
├── database/
├── docs/
├── tests/
└── scripts/
```

---

## 3. Docker Setup

### Build Docker Images
```bash
cd /home/cosmin/projects/aura

# Build all services
docker-compose build

# This will build:
# - MySQL containers (secure and vulnerable)
# - Flask app containers (secure and vulnerable)
```

### Verify Images
```bash
# List Docker images
docker images | grep aura

# Expected output:
# aura-app-secure
# aura-app-vulnerable
```

---

## 4. Database Setup

### Database Configuration

The application uses two separate MySQL databases:

**Secure Database**:
- Host: `mysql-secure`
- Port: `3306` (host) → `3306` (container)
- Database: `aura_secure`
- User: `aura_user`
- Password: `SecureUserPass123!`

**Vulnerable Database**:
- Host: `mysql-vulnerable`
- Port: `3307` (host) → `3306` (container)
- Database: `aura_vulnerable`
- User: `aura_user`
- Password: `VulnUserPass123!`

### Database Initialization

Databases are automatically initialized when containers start for the first time using:
- `database/init-secure.sql`
- `database/init-vulnerable.sql`

### Manual Database Access
```bash
# Access vulnerable database
docker exec -it aura-mysql-vulnerable mysql -u aura_user -p
# Enter password: VulnUserPass123!

# Access secure database
docker exec -it aura-mysql-secure mysql -u aura_user -p
# Enter password: SecureUserPass123!

# Once connected, you can run SQL commands:
USE aura_vulnerable;
SHOW TABLES;
SELECT * FROM users;
```

---

## 5. Running the Application

### Start All Services
```bash
cd /home/cosmin/projects/aura

# Start all containers in background
docker-compose up -d

# View logs (all services)
docker-compose logs -f

# View logs for specific service
docker-compose logs -f app-vulnerable
```

### Start Specific Version
```bash
# Start ONLY vulnerable version
docker-compose up -d mysql-vulnerable app-vulnerable

# Start ONLY secure version
docker-compose up -d mysql-secure app-secure
```

### Access the Application

**Vulnerable Version**:
- URL: http://localhost:5001
- Features: Intentional vulnerabilities for pentesting

**Secure Version**:
- URL: http://localhost:5000
- Features: Production-ready security controls

### Default Test Accounts

**Vulnerable Version**:
- Username: `testuser`
- Password: `VulnPass123`

**Secure Version**:
- Username: `testuser`
- Password: `SecurePass123!`

### Stop Services
```bash
# Stop all containers
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v
```

---

## 6. Troubleshooting

### Common Issues

#### Issue: Port Already in Use

**Error**: `Bind for 0.0.0.0:5001 failed: port is already allocated`

**Solution**:
```bash
# Find process using the port
sudo lsof -i :5001

# Kill the process
sudo kill -9 <PID>

# Or change port in docker-compose.yml
```

#### Issue: Database Connection Failed

**Error**: `Can't connect to MySQL server`

**Solution**:
```bash
# Check if MySQL container is running
docker ps | grep mysql

# Check MySQL logs
docker-compose logs mysql-vulnerable

# Restart MySQL container
docker-compose restart mysql-vulnerable
```

#### Issue: Permission Denied

**Error**: `Permission denied while trying to connect to Docker daemon`

**Solution**:
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and log back in
# Or run with sudo (not recommended)
sudo docker-compose up -d
```

#### Issue: Container Keeps Restarting

**Solution**:
```bash
# View container logs
docker-compose logs app-vulnerable

# Common causes:
# - Python import errors (check requirements.txt)
# - Database not ready (wait 30 seconds and retry)
# - Port conflicts
```

#### Issue: Database Tables Not Created

**Solution**:
```bash
# Remove volumes and restart
docker-compose down -v
docker-compose up -d

# Wait for initialization (check logs)
docker-compose logs -f mysql-vulnerable
```

### View Container Status
```bash
# List all containers
docker ps -a

# Check specific container
docker inspect aura-app-vulnerable

# View resource usage
docker stats
```

### Restart Services
```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart app-vulnerable

# Rebuild and restart
docker-compose up -d --build
```

---

## 7. Advanced Configuration

### Environment Variables

You can override default configurations using environment variables:
```bash
# Create .env file (optional)
nano .env

# Add custom configurations:
DATABASE_HOST=mysql-vulnerable
DATABASE_PORT=3306
FLASK_ENV=development
SECRET_KEY=your-custom-secret-key
```

### Custom Database Initialization

To add custom data or modify schema:

1. Edit `database/init-vulnerable.sql`
2. Remove existing volume:
```bash
   docker-compose down -v
```
3. Restart containers:
```bash
   docker-compose up -d
```

### Performance Tuning
```bash
# Allocate more resources to containers
# Edit docker-compose.yml:

services:
  app-vulnerable:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          memory: 1G
```

### Logging Configuration
```bash
# View logs with timestamps
docker-compose logs -f --timestamps

# Save logs to file
docker-compose logs > aura-logs.txt

# Follow logs for specific service
docker-compose logs -f app-vulnerable
```

### Backup and Restore

#### Backup Database
```bash
# Backup vulnerable database
docker exec aura-mysql-vulnerable mysqldump -u aura_user -pVulnUserPass123! aura_vulnerable > backup-vuln.sql

# Backup secure database
docker exec aura-mysql-secure mysqldump -u aura_user -pSecureUserPass123! aura_secure > backup-secure.sql
```

#### Restore Database
```bash
# Restore vulnerable database
docker exec -i aura-mysql-vulnerable mysql -u aura_user -pVulnUserPass123! aura_vulnerable < backup-vuln.sql

# Restore secure database
docker exec -i aura-mysql-secure mysql -u aura_user -pSecureUserPass123! aura_secure < backup-secure.sql
```

---

## 🎯 Quick Reference

### Essential Commands
```bash
# Start application
docker-compose up -d

# Stop application
docker-compose down

# View logs
docker-compose logs -f

# Rebuild containers
docker-compose up -d --build

# Fresh start (remove all data)
docker-compose down -v && docker-compose up -d

# Access database
docker exec -it aura-mysql-vulnerable mysql -u aura_user -p
```

### URLs

- Vulnerable Version: http://localhost:5001
- Secure Version: http://localhost:5000

---

## ✅ Verification Checklist

After setup, verify:

- [ ] Docker and Docker Compose installed
- [ ] All containers running (`docker ps`)
- [ ] Can access vulnerable version (http://localhost:5001)
- [ ] Can access secure version (http://localhost:5000)
- [ ] Can register new user
- [ ] Can login with test credentials
- [ ] Database contains users table
- [ ] No error messages in logs

---

**Setup complete! Ready for development and testing.** 🚀
