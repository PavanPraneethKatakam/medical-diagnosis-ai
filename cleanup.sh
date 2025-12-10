#!/bin/bash
# Cleanup script - Remove unnecessary files from project

echo "🧹 Cleaning up project directory..."
echo ""

# Files to KEEP (essential for project)
KEEP_FILES=(
    "app.py"
    "requirements.txt"
    ".env"
    ".gitignore"
    "README.md"
    "add_patient_history.py"
)

# Directories to KEEP
KEEP_DIRS=(
    "agents"
    "api"
    "database"
    "frontend"
    "tests"
    "logs"
    "scripts"
    "backend"
)

# Remove unnecessary documentation files
echo "📄 Removing duplicate/temporary documentation..."
rm -f DOCKER_DEPLOYMENT.md 2>/dev/null && echo "  ✓ Removed DOCKER_DEPLOYMENT.md"
rm -f DEPLOYMENT_GUIDE.md 2>/dev/null && echo "  ✓ Removed DEPLOYMENT_GUIDE.md"
rm -f REVERT_COMPLETE.md 2>/dev/null && echo "  ✓ Removed REVERT_COMPLETE.md"
rm -f FRONTEND_ACCESS.md 2>/dev/null && echo "  ✓ Removed FRONTEND_ACCESS.md"
rm -f FRONTEND_AUTH_FIX.md 2>/dev/null && echo "  ✓ Removed FRONTEND_AUTH_FIX.md"
rm -f UI_ENHANCEMENTS_COMPLETE.md 2>/dev/null && echo "  ✓ Removed UI_ENHANCEMENTS_COMPLETE.md"
rm -f UI_ENHANCEMENT_PLAN.md 2>/dev/null && echo "  ✓ Removed UI_ENHANCEMENT_PLAN.md"
rm -f FIXES_APPLIED.md 2>/dev/null && echo "  ✓ Removed FIXES_APPLIED.md"
rm -f SESSION_SUMMARY.md 2>/dev/null && echo "  ✓ Removed SESSION_SUMMARY.md"
rm -f FINAL_SUMMARY.md 2>/dev/null && echo "  ✓ Removed FINAL_SUMMARY.md"
rm -f FINAL_DELIVERY_REPORT.md 2>/dev/null && echo "  ✓ Removed FINAL_DELIVERY_REPORT.md"
rm -f PRODUCTION_CHECKLIST.md 2>/dev/null && echo "  ✓ Removed PRODUCTION_CHECKLIST.md"
rm -f CLEANUP_SUMMARY.md 2>/dev/null && echo "  ✓ Removed CLEANUP_SUMMARY.md"

# Remove Docker files (not using Docker)
echo ""
echo "🐳 Removing Docker files..."
rm -f Dockerfile 2>/dev/null && echo "  ✓ Removed Dockerfile"
rm -f docker-compose.yml 2>/dev/null && echo "  ✓ Removed docker-compose.yml"
rm -f .dockerignore 2>/dev/null && echo "  ✓ Removed .dockerignore"
rm -rf nginx/ 2>/dev/null && echo "  ✓ Removed nginx/"

# Remove deployment scripts (not needed)
echo ""
echo "📜 Removing unused scripts..."
rm -f deploy.sh 2>/dev/null && echo "  ✓ Removed deploy.sh"
rm -f deploy-production.sh 2>/dev/null && echo "  ✓ Removed deploy-production.sh"
rm -f stop-production.sh 2>/dev/null && echo "  ✓ Removed stop-production.sh"
rm -f logging.conf 2>/dev/null && echo "  ✓ Removed logging.conf"
rm -f start.sh 2>/dev/null && echo "  ✓ Removed start.sh"
rm -f run.sh 2>/dev/null && echo "  ✓ Removed run.sh"

# Remove .env.example (we have .env)
rm -f .env.example 2>/dev/null && echo "  ✓ Removed .env.example"

# Remove backup files
echo ""
echo "🗑️  Removing backup files..."
find . -name "*.backup" -type f -delete 2>/dev/null && echo "  ✓ Removed *.backup files"
find . -name "*.bak" -type f -delete 2>/dev/null && echo "  ✓ Removed *.bak files"
find . -name "*.tmp" -type f -delete 2>/dev/null && echo "  ✓ Removed *.tmp files"

# Remove Python cache
echo ""
echo "🐍 Removing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null && echo "  ✓ Removed __pycache__"
find . -name "*.pyc" -delete 2>/dev/null && echo "  ✓ Removed *.pyc files"

# Remove .DS_Store files (Mac)
find . -name ".DS_Store" -delete 2>/dev/null && echo "  ✓ Removed .DS_Store files"

# Remove PID files
rm -f .app.pid 2>/dev/null && echo "  ✓ Removed .app.pid"

# Remove verify script (temporary)
rm -f verify_api.py 2>/dev/null && echo "  ✓ Removed verify_api.py"

echo ""
echo "=" * 60
echo "✅ Cleanup complete!"
echo "=" * 60
echo ""

# Show what's left
echo "📁 Remaining files in root directory:"
ls -1 | grep -v "^agents$\|^api$\|^database$\|^frontend$\|^tests$\|^logs$\|^scripts$\|^backend$"

echo ""
echo "📊 Directory summary:"
echo "  Files: $(find . -maxdepth 1 -type f | wc -l)"
echo "  Directories: $(find . -maxdepth 1 -type d | wc -l)"
