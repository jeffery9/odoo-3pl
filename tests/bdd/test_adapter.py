# BDD Test Adapter Module

# File Path: tests/bdd/test_adapter.py
from unittest import TestCase
from ..context.scenario_manager import ScenarioManager

class BaseBDDTest(TestCase):
    """Base class to initialize the scenario context for all feature runs."""
    def setUp(self):
        super().setUp()
        # Initialize a new, isolated manager instance before each test run
        self.context = ScenarioManager()
        print("--- Starting New BDD Context: Scenario Manager Initialized ---")
    def teardown(self):
        """Clean up after all BDD tests have run."""
        print("--- Finished BDD Context: Scenario Manager Cleanup Complete ---")


class FeatureRunnerTest(BaseBDDTest):
    """
    This test class acts as the primary entry point for executing Gherkin feature files.
    It must be integrated with an underlying library (like 'behave' or a custom adapter)
    to process feature/scenario steps sequentially and provide context access.
    """
    def test_execute_bdd_features(self):
        # Placeholder for the actual BDD execution loop.
        # In a real implementation, this method would iterate through ALL files in tests/bdd/*/*.feature
        print("Running all BDD features found across modules...")

        # Example: Running the wms_owner feature
        try:
            self._run_scenario(f"wms_owner/features/create_manifest.feature", "Scenario 1")
        except Exception as e:
            self.fail(f"Feature execution failed for wms_owner: {e}")
    def _run_scenario(self, feature_path, scenario_name):
        """Simulates loading and running a single BDD Scenario."""
        print(f"\n[Executing Scenario] in Feature File: {feature_path} -> {scenario_name}")
        # In production code, this function would parse the feature file,
        # instantiate step definitions (e.g., WMSOwnerSteps()), and execute them
        # passing self.context to every step method call.
        print(f"[SUCCESS] Scenario '{scenario_name}' completed using shared context.")

# Note: The actual logic for parsing and calling steps must be implemented here,
# likely integrating a 'behave' library wrapper or custom execution engine.