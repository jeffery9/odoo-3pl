#!/bin/bash
# Odoo-3PL BDD Acceptance Verification Pipeline
# Wrapper script to execute the validation process defined by odoo-testing-pipeline.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname $(dirname $(dirname $SCRIPT_DIR)))"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"
ODOO_MODULE="odoo-3pl"
TEMP_DB="test_${ODOO_MODULE}_acceptance_$(date +%s)"

echo "============================================================"
echo "  Odoo-3PL BDD ACCEPTANCE VERIFICATION (验收)"
echo "============================================================"

# Phase 1: Circuit Breaker - Environment & Schema Check
echo -e "\n[Phase 1] Circuit Breaker & Schema Synchronization..."
if ! docker-compose -f $COMPOSE_FILE exec -T web odoo --version > /dev/null 2>&1; then
    echo "[ERROR] Odoo service is not reachable. Please ensure containers are running."
    exit 1
fi

echo "Executing mandatory schema upgrade (-u $ODOO_MODULE)..."
docker-compose -f $COMPOSE_FILE exec -T web odoo \
    --stop-after-init \
    -c /etc/odoo/odoo.conf \
    -d $TEMP_DB \
    -i $ODOO_MODULE 2>&1 | tail -n 5

echo -e "\n[Phase 2] Running Backend Unit & Integration Tests..."
docker-compose -f $COMPOSE_FILE exec -T web odoo \
    -c /etc/odoo/odoo.conf \
    -d $TEMP_DB \
    --test-enable \
    --stop-after-init \
    --test-tags=/modules/$ODOO_MODULE/ 2>&1 | tail -n 10

echo -e "\n[Phase 3] Running BDD E2E / UAT via Playwright..."
# Run the Python playwright orchestrator
python3 "$SCRIPT_DIR/run_odoo_3pl_pipeline.py"

echo -e "\n[Cleanup] Dropping temporary database $TEMP_DB..."
docker-compose -f $COMPOSE_FILE exec -T web dropdb --if-exists $TEMP_DB 2>/dev/null || true

echo -e "\n============================================================"
echo "  Verification Complete. Check 'reports/' for details."
echo "============================================================"
