#!/bin/bash
# File: scripts/bdd/run_bdd_tests.sh
# Description: Dedicated script to run the complete BDD Feature Suite for all WMS modules.
# Usage: docker-compose exec web /path/to/your/odoo-binary test --module bdd_test

set -e # Exit immediately if a command exits with a non-zero status.

echo "============================================================="
echo "Starting BDD Feature Test Suite Execution (WMS Modules)"
echo "Running against Odoo database: odoo_test_run"
echo "-------------------------------------------------------------"

# Check for required environment variables and services first (e.g., waiting for PostgreSQL)
# You might need to add explicit wait steps here if the service is not guaranteed to be ready.

# --- Core BDD Test Execution ---
# This command assumes:
# 1. The Odoo container 'web' is running via docker-compose.
# 2. The test_adapter.py (which handles Gherkin parsing) has been installed/copied into the appropriate test path within the web container.

echo "Executing BDD Adapter Test Class..."

# Use the standard odoo execution method, pointing to our dedicated adapter module for tests.
# Adjust the 'odoo-bin' path and database name as necessary for your environment.
docker-compose exec web odoo -c /etc/odoo/odoo.conf -d odoo_test_run --module bdd_test --test-enable \
    --init wms_owner,wms_putaway,wms_wave,wms_billing,wms_crossdock --stop-after-init --no-http

# Note: The actual test command execution within the container might need to be adjusted based on how your Odoo version/custom setup processes module loading for testing purposes.
echo "============================================================="
echo "✅ BDD Feature Test Suite Execution Completed Successfully."
echo "All core WMS workflows have been validated against Gherkin specifications."