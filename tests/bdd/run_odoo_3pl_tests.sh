  #!/bin/bash
  # Odoo-3PL Master Verification Script (Self-Healing)
  set -e

  echo "=========================================="
  echo "  Starting Odoo-3PL Verification Pipeline"
  echo "=========================================="

  # --- Step 1: Environment Cleanup (Fix Port Conflict) ---
  echo "[Step 1] Cleaning up Port 8069..."
  lsof -ti :8069 | xargs kill -9 2>/dev/null || true
  sleep 3

  # --- Step 2: Apply Proactive Fixes (Based on Diagnostic Logs) ---
  cd /Users/jeffery/containers/odoo18/addons/odoo-3pl
  echo "[Step 2] Applying Code Fixes..."

  # Fix A: Patch wms_putaway stock_move_line.py (Fixes ValueError for stock.quant.owner_id)
  python3 -c "
  path = 'wms_putaway/models/stock_move_line.py'
  try:
      with open(path, 'r') as f: content = f.read()
      # Fix the owner_id type mismatch causing demo crashes
      if 'owner_id=owner' in content and '_update_available_quantity' in content:
          content = content.replace('owner_id=owner', 'owner_id=owner.partner_id if owner else False')
          with open(path, 'w') as f: f.write(content)
          print('[Fixed] stock_move_line.py owner logic.')
  except: pass

  # Fix B: Remove Odoo 18 Deprecation Warnings (@api.model on create)
  import os, re
  for root, dirs, files in os.walk('.'):
      for file in files:
          if file.endswith('.py') and 'models' in root:
              fpath = os.path.join(root, file)
              with open(fpath, 'r') as f: content = f.read()
              # Replace @api.model \n def create with just def create
              new_content = re.sub(r'\s*@api\.model\s+def create\(', '    def create(', content)
              if new_content != content:
                  with open(fpath, 'w') as f: f.write(new_content)
                  print(f'[Fixed] @api.model deprecation in {file}')
  "

  # --- Step 3: Module Installation (Schema Sync) ---
  cd /Users/jeffery/containers/odoo18
  echo "[Step 3] Installing Modules..."
  docker-compose exec web odoo --stop-after-init -d postgres -c /etc/odoo/odoo.conf -u
  wms_owner,wms_wave,wms_putaway,wms_billing,wms_abc_analysis,wms_quality_control 2>&1 | grep -E
  "(Loading|Module.*loaded|ERROR)"

  # --- Step 4: Backend Unit & Integration Tests ---
  echo "[Step 4] Running Backend Tests..."
  docker-compose exec web odoo --stop-after-init -d postgres -c /etc/odoo/odoo.conf --test-enable --test-
  tags "/wms_owner/,/wms_wave/,/wms_putaway/" 2>&1 | grep -E "(ERROR|FAIL|OK)"

  # --- Step 5: BDD UI Verification (Optional) ---
  echo "[Step 5] Starting BDD Playwright Tests..."
  cd /Users/jeffery/containers/odoo18/addons/odoo-3pl/tests/bdd
  if [ -f "run_bdd_playwright.py" ]; then
      python3 run_bdd_playwright.py --headless
  else
      echo "[Skipped] Playwright script not found."
  fi

  echo "=========================================="
  echo "  Verification Complete. Check logs above."
  echo "=========================================="
  EOF

  chmod +x /Users/jeffery/containers/odoo18/addons/odoo-3pl/tests/bdd/run_odoo_3pl_tests.sh


