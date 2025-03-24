#!/bin/bash

# Development helper script for ISP Management Platform

# Function to display help message
show_help() {
    echo "ISP Management Platform Development Helper"
    echo ""
    echo "Usage: ./dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  up              Start all services in development mode"
    echo "  down            Stop all services"
    echo "  build           Rebuild all services"
    echo "  logs [service]  View logs (optionally for a specific service)"
    echo "  test            Run tests"
    echo "  migrate         Run database migrations"
    echo "  shell           Open a shell in the app container"
    echo "  psql            Open PostgreSQL interactive terminal"
    echo "  redis-cli       Open Redis interactive terminal"
    echo "  es-health       Check Elasticsearch health"
    echo "  kibana          Open Kibana in browser (macOS only)"
    echo "  help            Show this help message"
    echo ""
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo "Error: Docker is not running. Please start Docker Desktop first."
        exit 1
    fi
}

# Start services
start_services() {
    echo "Starting ISP Management Platform services..."
    docker-compose up -d
    echo "Services started. Access the API at http://localhost:8000"
    echo "Access Kibana at http://localhost:5601"
}

# Stop services
stop_services() {
    echo "Stopping ISP Management Platform services..."
    docker-compose down
    echo "Services stopped."
}

# Build services
build_services() {
    echo "Building ISP Management Platform services..."
    docker-compose build
    echo "Build completed."
}

# View logs
view_logs() {
    if [ -z "$1" ]; then
        docker-compose logs -f
    else
        docker-compose logs -f "$1"
    fi
}

# Run tests
run_tests() {
    echo "Running tests..."
    docker-compose run --rm app pytest "$@"
}

# Run migrations
run_migrations() {
    echo "Running database migrations..."
    docker-compose run --rm app python -m alembic upgrade head
    echo "Migrations completed."
}

# Open shell in app container
open_shell() {
    echo "Opening shell in app container..."
    docker-compose exec app /bin/bash
}

# Open PostgreSQL interactive terminal
open_psql() {
    echo "Opening PostgreSQL interactive terminal..."
    docker-compose exec postgres psql -U postgres -d isp_management
}

# Open Redis interactive terminal
open_redis_cli() {
    echo "Opening Redis interactive terminal..."
    docker-compose exec redis redis-cli
}

# Check Elasticsearch health
check_es_health() {
    echo "Checking Elasticsearch health..."
    curl -X GET "http://localhost:9200/_cluster/health?pretty"
}

# Open Kibana in browser (macOS only)
open_kibana() {
    echo "Opening Kibana in browser..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open http://localhost:5601
    else
        echo "Please open http://localhost:5601 in your browser."
    fi
}

# Main script logic
check_docker

case "$1" in
    up)
        start_services
        ;;
    down)
        stop_services
        ;;
    build)
        build_services
        ;;
    logs)
        view_logs "$2"
        ;;
    test)
        shift
        run_tests "$@"
        ;;
    migrate)
        run_migrations
        ;;
    shell)
        open_shell
        ;;
    psql)
        open_psql
        ;;
    redis-cli)
        open_redis_cli
        ;;
    es-health)
        check_es_health
        ;;
    kibana)
        open_kibana
        ;;
    help|*)
        show_help
        ;;
esac
