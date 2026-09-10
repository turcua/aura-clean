# 💰 Aura - Personal Financial Tracker

**A dual-version web application for financial tracking and cybersecurity learning**

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-green.svg)](https://flask.palletsprojects.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Private-red.svg)]()

---

## 📋 Project Overview

**Aura** is a personal financial tracking application built with two parallel implementations:

- 🔒 **Secure Version** - Production-ready with security best practices
- ⚠️ **Vulnerable Version** - Intentionally insecure for pentesting practice (CTF-style)

### 🎯 Project Goals

1. Build a functional financial tracking web application
2. Learn web development (Flask, MySQL, Docker)
3. Practice cybersecurity through intentional vulnerabilities
4. Improve pentesting skills in a safe environment

---

## 🏗️ Architecture

### Technology Stack

- **Backend**: Python 3.11 + Flask 3.0
- **Database**: MySQL 8.0
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Containerization**: Docker & Docker Compose
- **Future**: Kubernetes + Prometheus/Grafana monitoring

### Project Structure
```
aura/
├── secure-version/              # Secure implementation
│   ├── app.py                   # Main Flask application
│   ├── config.py                # Configuration
│   ├── models/                  # Database models
│   ├── routes/                  # Application routes
│   ├── templates/               # HTML templates
│   ├── static/                  # CSS, JS, images
│   ├── utils/                   # Utility functions
│   ├── Dockerfile
│   └── requirements.txt
│
├── vulnerable-version/          # Vulnerable implementation (CTF)
│   ├── app.py
│   ├── config.py
│   ├── models/
│   ├── routes/
│   ├── templates/
│   ├── static/
│   ├── utils/
│   ├── Dockerfile
│   └── requirements.txt
│
├── database/                    # Database schemas
│   ├── init-secure.sql
│   └── init-vulnerable.sql
│
├── docs/                        # Documentation
│   ├── setup-guide.md
│   ├── pentester-guide.md
│   ├── vulnerability-matrix.md
│   └── development-log.md
│
├── tests/                       # Test files
├── scripts/                     # Utility scripts
├── docker-compose.yml           # Docker orchestration
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git installed
- 4GB RAM minimum
- Ubuntu/Linux environment (or WSL2 on Windows)

### Installation

1. **Clone the repository** (if using Git):
```bash
   cd /home/cosmin/projects/aura
```

2. **Start the application**:
```bash
   # Start vulnerable version
   ./scripts/start-containers.sh vulnerable
   
   # OR start secure version
   ./scripts/start-containers.sh secure
   
   # OR start both
   docker-compose up -d
```

3. **Access the application**:
   - **Vulnerable Version**: http://localhost:5001
   - **Secure Version**: http://localhost:5000

4. **Default test credentials**:
   - Username: `testuser`
   - Password (Vulnerable): `VulnPass123`
   - Password (Secure): `SecurePass123!`

---

## 📖 Documentation

- **[Setup Guide](docs/setup-guide.md)** - Detailed installation and configuration
- **[Pentester Guide](docs/pentester-guide.md)** - Vulnerability documentation and exploitation
- **[Vulnerability Matrix](docs/vulnerability-matrix.md)** - Complete vulnerability tracking
- **[Development Log](docs/development-log.md)** - Sprint progress and decisions

---

## 🎌 Release Information

### **Release 1: "Hashira Foundation"** (Demon Slayer)
*Current Release - Foundation & Authentication*

#### Sprint 1: "Water Breathing - First Form" ✅
**Status**: COMPLETE  
**Features**:
- ✅ Development environment setup (Docker)
- ✅ User authentication (registration, login, logout)
- ✅ Session management
- ✅ Basic dashboard
- ✅ Intentional vulnerabilities (SQL Injection, XSS, IDOR, etc.)

---

## 🔒 Security Notice

### ⚠️ **IMPORTANT - Vulnerable Version Warning**

The **vulnerable version** of this application contains **intentional security flaws** for educational purposes:

- ❌ **DO NOT** deploy to production
- ❌ **DO NOT** use with real financial data
- ❌ **DO NOT** expose to the internet
- ✅ **USE ONLY** in isolated local/VM environments
- ✅ **USE FOR** learning and pentesting practice

### Known Vulnerabilities (Vulnerable Version)

See [Pentester Guide](docs/pentester-guide.md) for complete list.

**Difficulty Levels**:
- 🟢 **Easy**: SQL Injection, Weak Password Storage, Missing Authentication
- 🟡 **Medium**: Session Hijacking, CSRF, IDOR, XSS
- 🔴 **Hard**: Business Logic Flaws, Race Conditions (future sprints)

---

## 🧪 Testing

### Running Tests
```bash
# Build containers
docker-compose build

# Start containers
docker-compose up -d

# View logs
docker-compose logs -f app-vulnerable

# Stop containers
docker-compose down
```

### Manual Testing Checklist

- [ ] Registration with valid data
- [ ] Registration with SQL injection
- [ ] Login with valid credentials
- [ ] Login with SQL injection bypass
- [ ] Access admin panel without authentication
- [ ] IDOR attack on user profiles
- [ ] XSS in username field
- [ ] Session hijacking

---

## 📊 Development Methodology

This project follows **Agile methodology**:

- **Sprint Length**: 1 week
- **Ceremonies**:
  - Sprint Planning (start of week)
  - Daily Standups
  - Testing/Regression (every 2 days)
  - Sprint Review/Retro (end of week)

### Backlog Structure
```
Release → Sprint → Epic → Feature → User Story → Tasks
```

---

## 🛠️ Development Commands

### Docker Commands
```bash
# Build all containers
docker-compose build

# Start vulnerable version only
docker-compose up -d mysql-vulnerable app-vulnerable

# Start secure version only
docker-compose up -d mysql-secure app-secure

# View logs
docker-compose logs -f [service-name]

# Stop all containers
docker-compose down

# Remove volumes (fresh start)
docker-compose down -v
```

### Database Access
```bash
# Connect to vulnerable database
docker exec -it aura-mysql-vulnerable mysql -u aura_user -p
# Password: VulnUserPass123!

# Connect to secure database
docker exec -it aura-mysql-secure mysql -u aura_user -p
# Password: SecureUserPass123!
```

---

## 🎯 Roadmap

### Completed Features ✅
- [x] Docker environment setup
- [x] User authentication system
- [x] Vulnerable & secure versions
- [x] SQL injection vulnerabilities
- [x] XSS vulnerabilities
- [x] IDOR vulnerabilities
- [x] Session management issues

### Upcoming Features 🚀

**Sprint 2: "Thunder Breathing - Second Form"**
- [ ] Transaction management (income/expense)
- [ ] Category management
- [ ] Basic dashboard charts

**Sprint 3: "Flame Breathing - Third Form"**
- [ ] Recurring transactions
- [ ] Multi-currency support
- [ ] Import/Export (Excel)

**Future Sprints**
- [ ] Advanced reporting
- [ ] AI-powered insights
- [ ] Kubernetes deployment
- [ ] Monitoring (Prometheus/Grafana)

---

## 👨‍💻 Contributing

This is a personal learning project. Contributions are not currently accepted.

---

## 📝 License

This project is private and for educational purposes only.

---

## 🙏 Acknowledgments

- **Anime References**: Demon Slayer, Solo Leveling, Naruto (for release naming)
- **Learning Resources**: OWASP, PortSwigger Web Security Academy
- **Technologies**: Flask, MySQL, Docker, Bootstrap

---

## 📞 Support

For issues or questions about this project, please refer to the documentation in the `docs/` folder.

---

**Version**: 1.0.0  
**Last Updated**: Sprint 1 Completion  
**Status**: ✅ Sprint 1 Complete | 🚧 Sprint 2 Upcoming
