#!/bin/bash

# Aura Project - Automated Structure Creation Script
# Sprint 1: Water Breathing - First Form

set -e  # Exit on any error

PROJECT_DIR="/home/cosmin/projects/aura"

echo "🚀 Creating Aura Project Structure..."

# Create main project directory
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Create directory structure
echo "📁 Creating directories..."

# Secure version directories
mkdir -p secure-version/{models,routes,templates,static/{css,js},utils}

# Vulnerable version directories
mkdir -p vulnerable-version/{models,routes,templates,static/{css,js},utils}

# Shared directories
mkdir -p database
mkdir -p docs
mkdir -p tests
mkdir -p scripts

echo "✅ Directory structure created!"

# Create __init__.py files for Python packages
echo "🐍 Creating Python package files..."

touch secure-version/models/__init__.py
touch secure-version/routes/__init__.py
touch secure-version/utils/__init__.py

touch vulnerable-version/models/__init__.py
touch vulnerable-version/routes/__init__.py
touch vulnerable-version/utils/__init__.py

touch tests/__init__.py

echo "✅ Python packages initialized!"

# Create .gitignore
echo "📝 Creating .gitignore..."
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Flask
instance/
.webassets-cache

# Database
*.db
*.sqlite
*.sqlite3

# Docker
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Environment variables
.env
.env.local

# Secrets (DO NOT COMMIT)
secrets/
*.key
*.pem
EOF

echo "✅ .gitignore created!"

# Initialize Git repository
echo "🔧 Initializing Git repository..."
git init
git config core.ignorecase false

echo "✅ Git repository initialized!"

# Create initial branches
echo "🌿 Creating Git branches..."
git checkout -b main

echo "✅ Git branches created!"

echo ""
echo "🎉 Project structure created successfully!"
echo "📍 Location: $PROJECT_DIR"
echo ""
echo "Next steps:"
echo "1. Navigate to project: cd $PROJECT_DIR"
echo "2. Review the structure: tree -L 3 (or ls -R)"
echo "3. Ready for file generation!"
echo ""
EOF

# Make script executable
chmod +x create-aura-structure.sh
