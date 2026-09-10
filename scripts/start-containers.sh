#!/bin/bash

###############################################################################
# Aura Financial Tracker - Container Startup Script
# Sprint 1: Water Breathing - First Form
#
# Usage:
#   ./scripts/start-containers.sh [vulnerable|secure|both]
#
# Examples:
#   ./scripts/start-containers.sh vulnerable  # Start vulnerable version only
#   ./scripts/start-containers.sh secure      # Start secure version only
#   ./scripts/start-containers.sh both        # Start both versions
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project directory
PROJECT_DIR="/home/cosmin/projects/aura"

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    print_info "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    
    print_success "Docker is running"
}

# Function to check if docker-compose is available
check_docker_compose() {
    print_info "Checking Docker Compose installation..."
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Docker Compose is available"
}

# Function to navigate to project directory
navigate_to_project() {
    print_info "Navigating to project directory..."
    
    if [ ! -d "$PROJECT_DIR" ]; then
        print_error "Project directory not found: $PROJECT_DIR"
        exit 1
    fi
    
    cd "$PROJECT_DIR"
    print_success "In project directory: $(pwd)"
}

# Function to stop existing containers
stop_containers() {
    print_info "Stopping existing containers..."
    docker-compose down 2>/dev/null || true
    print_success "Existing containers stopped"
}

# Function to start vulnerable version
start_vulnerable() {
    print_info "Starting VULNERABLE version..."
    echo ""
    print_warning "⚠️  WARNING: This version contains intentional security vulnerabilities!"
    print_warning "⚠️  DO NOT use with real data or expose to the internet!"
    echo ""
    
    docker-compose up -d mysql-vulnerable app-vulnerable
    
    echo ""
    print_success "Vulnerable version started!"
    print_info "Access at: ${GREEN}http://localhost:5001${NC}"
    print_info "Database port: ${GREEN}3307${NC}"
    echo ""
    print_info "Default credentials:"
    print_info "  Username: testuser"
    print_info "  Password: VulnPass123"
    echo ""
}

# Function to start secure version
start_secure() {
    print_info "Starting SECURE version..."
    
    docker-compose up -d mysql-secure app-secure
    
    echo ""
    print_success "Secure version started!"
    print_info "Access at: ${GREEN}http://localhost:5000${NC}"
    print_info "Database port: ${GREEN}3306${NC}"
    echo ""
    print_info "Default credentials:"
    print_info "  Username: testuser"
    print_info "  Password: SecurePass123!"
    echo ""
}

# Function to start both versions
start_both() {
    print_info "Starting BOTH versions..."
    echo ""
    print_warning "⚠️  WARNING: Vulnerable version contains intentional security flaws!"
    echo ""
    
    docker-compose up -d
    
    echo ""
    print_success "Both versions started!"
    echo ""
    print_info "VULNERABLE VERSION:"
    print_info "  URL: ${RED}http://localhost:5001${NC}"
    print_info "  Database: port 3307"
    print_info "  Credentials: testuser / VulnPass123"
    echo ""
    print_info "SECURE VERSION:"
    print_info "  URL: ${GREEN}http://localhost:5000${NC}"
    print_info "  Database: port 3306"
    print_info "  Credentials: testuser / SecurePass123!"
    echo ""
}

# Function to show logs
show_logs() {
    print_info "Container logs will appear below..."
    print_info "Press Ctrl+C to stop viewing logs (containers will keep running)"
    echo ""
    sleep 2
    docker-compose logs -f
}

# Function to show status
show_status() {
    echo ""
    print_info "Container Status:"
    docker-compose ps
    echo ""
}

# Main script
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                                                            ║"
    echo "║        💰 Aura Financial Tracker - Startup Script         ║"
    echo "║        Sprint 1: Water Breathing - First Form             ║"
    echo "║                                                            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Get mode from argument
    MODE=${1:-both}
    
    # Validate mode
    if [[ ! "$MODE" =~ ^(vulnerable|secure|both)$ ]]; then
        print_error "Invalid mode: $MODE"
        echo ""
        echo "Usage: $0 [vulnerable|secure|both]"
        echo ""
        echo "Examples:"
        echo "  $0 vulnerable  # Start vulnerable version only"
        echo "  $0 secure      # Start secure version only"
        echo "  $0 both        # Start both versions (default)"
        echo ""
        exit 1
    fi
    
    # Run checks
    check_docker
    check_docker_compose
    navigate_to_project
    
    # Stop existing containers
    stop_containers
    
    # Start requested version(s)
    case $MODE in
        vulnerable)
            start_vulnerable
            ;;
        secure)
            start_secure
            ;;
        both)
            start_both
            ;;
    esac
    
    # Show status
    show_status
    
    # Ask if user wants to see logs
    read -p "$(echo -e ${BLUE}[INFO]${NC}) View container logs? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        show_logs
    else
        print_info "Containers are running in the background"
        print_info "View logs with: ${GREEN}docker-compose logs -f${NC}"
        print_info "Stop containers with: ${GREEN}docker-compose down${NC}"
    fi
    
    echo ""
    print_success "Startup complete! 🚀"
    echo ""
}

# Run main function
main "$@"
