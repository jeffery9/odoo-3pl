from odoo.tests import TransactionCase
from odoo import fields


class TestWmsEnergyManagement(TransactionCase):
    """Test cases for WMS Energy Management module"""

    def setUp(self):
        super().setUp()
        # Create test data
        self.test_owner = self.env['wms.owner'].create({
            'name': 'Test Energy Management Owner',
            'owner_code': 'TEMO',
            'is_warehouse_owner': True,
        })

        self.test_location = self.env['stock.location'].create({
            'name': 'Test Location',
            'usage': 'internal',
        })

        self.test_warehouse = self.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'owner_code': 'TW',
        })

        self.test_equipment = self.env['wms.energy.equipment'].create({
            'name': 'Test Energy Equipment',
            'owner_code': 'TEE',
            'equipment_type': 'lighting',
            'location_id': self.test_location.id,
            'power_rating': 10.0,  # kW
            'voltage': 220.0,  # V
            'current': 45.5,  # A
            'energy_source': 'electricity',
            'efficiency_rating': 95.0,  # %
        })
    def test_create_energy_equipment(self):
        """Test creating energy equipment"""
        equipment = self.env['wms.energy.equipment'].create({
            'name': 'Test Equipment',
            'owner_code': 'TE',
            'equipment_type': 'cooling',
            'location_id': self.test_location.id,
            'power_rating': 15.0,
            'energy_source': 'electricity',
            'efficiency_rating': 90.0,
        })

        self.assertEqual(equipment.name, 'Test Equipment')
        self.assertEqual(equipment.owner_code, 'TE')
        self.assertEqual(equipment.equipment_type, 'cooling')
        self.assertEqual(equipment.power_rating, 15.0)
        self.assertEqual(equipment.efficiency_rating, 90.0)
    def test_create_energy_reading(self):
        """Test creating energy readings"""
        reading = self.env['wms.energy.reading'].create({
            'equipment_id': self.test_equipment.id,
            'reading_date': fields.Datetime.now(),
            'energy_consumed': 50.0,  # kWh
            'peak_demand': 12.0,  # kW
            'cost': 10.50,
            'carbon_emissions': 25.0,  # kg
            'reading_type': 'manual',
        })

        self.assertEqual(reading.equipment_id.id, self.test_equipment.id)
        self.assertEqual(reading.energy_consumed, 50.0)
        self.assertEqual(reading.peak_demand, 12.0)
        self.assertEqual(reading.cost, 10.50)
        self.assertEqual(reading.carbon_emissions, 25.0)
        self.assertEqual(reading.reading_type, 'manual')
        self.assertFalse(reading.is_validated)
    def test_energy_reading_validation(self):
        """Test validating energy readings"""
        reading = self.env['wms.energy.reading'].create({
            'equipment_id': self.test_equipment.id,
            'reading_date': fields.Datetime.now(),
            'energy_consumed': 75.0,
            'cost': 15.75,
            'carbon_emissions': 37.5,
        })

        self.assertFalse(reading.is_validated)

        # Validate the reading
        reading.action_validate_reading()
        self.assertTrue(reading.is_validated)
        self.assertIsNotNone(reading.validated_by)
        self.assertIsNotNone(reading.validation_date)
    def test_create_energy_report(self):
        """Test creating energy reports"""
        energy_report = self.env['wms.energy.report'].create({
            'name': 'Test Energy Report',
            'owner_id': self.test_owner.id,
            'period_start': fields.Date.today(),
            'period_end': fields.Date.add(fields.Date.today(), days=30),
            'warehouse_id': self.test_warehouse.id,
        })

        self.assertTrue(energy_report.report_code.startswith('ENR'))
        self.assertEqual(energy_report.name, 'Test Energy Report')
        self.assertEqual(energy_report.owner_id.id, self.test_owner.id)
        self.assertEqual(energy_report.status, 'draft')
    def test_energy_report_totals_computation(self):
        """Test computed totals for energy reports"""
        # Create an energy report
        energy_report = self.env['wms.energy.report'].create({
            'name': 'Totals Computation Test',
            'owner_id': self.test_owner.id,
            'period_start': fields.Date.today(),
            'period_end': fields.Date.add(fields.Date.today(), days=7),
            'warehouse_id': self.test_warehouse.id,
        })

        # Create some readings within the report period
        self.env['wms.energy.reading'].create([
            {
                'equipment_id': self.test_equipment.id,
                'reading_date': fields.Datetime.now(),
                'energy_consumed': 100.0,
                'cost': 20.0,
                'carbon_emissions': 50.0,
            },
            {
                'equipment_id': self.test_equipment.id,
                'reading_date': fields.Datetime.add(fields.Datetime.now(), days=1),
                'energy_consumed': 150.0,
                'cost': 30.0,
                'carbon_emissions': 75.0,
            },
        ])

        # Refresh to get updated computed values
        energy_report.refresh()

        # Check that totals are computed correctly
        self.assertEqual(energy_report.total_energy_consumed, 250.0)  # 100 + 150
        self.assertEqual(energy_report.total_cost, 50.0)  # 20 + 30
        self.assertEqual(energy_report.total_carbon_emissions, 125.0)  # 50 + 75

    def test_energy_report_status_flow(self):
        """Test the status flow of energy reports"""
        energy_report = self.env['wms.energy.report'].create({
            'name': 'Status Flow Test',
            'owner_id': self.test_owner.id,
            'period_start': fields.Date.today(),
            'period_end': fields.Date.add(fields.Date.today(), days=30),
        })

        self.assertEqual(energy_report.status, 'draft')

        # Generate the report
        energy_report.action_generate_report()
        self.assertEqual(energy_report.status, 'generated')

        # Validate the report
        energy_report.action_validate_report()
        self.assertEqual(energy_report.status, 'validated')
    def test_energy_target_creation(self):
        """Test creating energy targets"""
        energy_target = self.env['wms.energy.target'].create({
            'name': 'Test Energy Target',
            'equipment_id': self.test_equipment.id,
            'target_month': '1',
            'target_year': 2024,
            'target_energy': 1000.0,  # kWh
        })

        self.assertEqual(energy_target.name, 'Test Energy Target')
        self.assertEqual(energy_target.equipment_id.id, self.test_equipment.id)
        self.assertEqual(energy_target.target_month, '1')
        self.assertEqual(energy_target.target_year, 2024)
        self.assertEqual(energy_target.target_energy, 1000.0)
        self.assertEqual(energy_target.actual_energy, 0.0)  # Initially 0
        self.assertEqual(energy_target.variance, 1000.0)  # 1000 - 0
        self.assertEqual(energy_target.variance_percentage, 100.0)  # (1000/1000)*100
        self.assertTrue(energy_target.achieved)  # 0 <= 1000, so achieved

    def test_energy_alert_creation(self):
        """Test creating energy alerts"""
        energy_alert = self.env['wms.energy.alert'].create({
            'name': 'Test Energy Alert',
            'equipment_id': self.test_equipment.id,
            'alert_type': 'high_consumption',
            'severity': 'high',
            'message': 'Energy consumption is significantly above normal levels',
        })

        self.assertEqual(energy_alert.name, 'Test Energy Alert')
        self.assertEqual(energy_alert.equipment_id.id, self.test_equipment.id)
        self.assertEqual(energy_alert.alert_type, 'high_consumption')
        self.assertEqual(energy_alert.severity, 'high')
        self.assertFalse(energy_alert.is_resolved)
    def test_energy_alert_resolution(self):
        """Test resolving energy alerts"""
        energy_alert = self.env['wms.energy.alert'].create({
            'name': 'Resolution Test',
            'equipment_id': self.test_equipment.id,
            'alert_type': 'peak_demand',
            'severity': 'medium',
            'message': 'Peak demand threshold exceeded',
        })

        self.assertFalse(energy_alert.is_resolved)

        # Resolve the alert
        energy_alert.action_resolve_alert()
        self.assertTrue(energy_alert.is_resolved)
        self.assertIsNotNone(energy_alert.resolved_by)
        self.assertIsNotNone(energy_alert.resolved_date)
    def test_energy_equipment_maintenance_dates(self):
        """Test energy equipment maintenance date fields"""
        from datetime import date

        equipment = self.env['wms.energy.equipment'].create({
            'name': 'Maintenance Test Equipment',
            'owner_code': 'MTE',
            'equipment_type': 'heating',
            'installation_date': date(2023, 1, 1),
            'last_maintenance_date': date(2024, 1, 1),
            'next_maintenance_date': date(2024, 7, 1),
        })

        self.assertEqual(equipment.installation_date, date(2023, 1, 1))
        self.assertEqual(equipment.last_maintenance_date, date(2024, 1, 1))
        self.assertEqual(equipment.next_maintenance_date, date(2024, 7, 1))
    def test_energy_reading_positive_values_constraint(self):
        """Test that energy readings must have positive values"""
        # Test negative energy consumed
        with self.assertRaises(Exception):
            self.env['wms.energy.reading'].create({
                'equipment_id': self.test_equipment.id,
                'reading_date': fields.Datetime.now(),
                'energy_consumed': -50.0,  # Negative value
                'cost': 10.0,
            })

        # Test negative cost
        with self.assertRaises(Exception):
            self.env['wms.energy.reading'].create({
                'equipment_id': self.test_equipment.id,
                'reading_date': fields.Datetime.now(),
                'energy_consumed': 50.0,
                'cost': -10.0,  # Negative value
            })
    def test_energy_target_achievement_computation(self):
        """Test energy target achievement computation"""
        # Create a target
        energy_target = self.env['wms.energy.target'].create({
            'name': 'Achievement Test',
            'target_month': '1',
            'target_year': 2024,
            'target_energy': 1000.0,
        })

        self.assertTrue(energy_target.achieved)  # Initially achieved since actual is 0

        # Create a reading that exceeds the target
        self.env['wms.energy.reading'].create({
            'equipment_id': self.test_equipment.id,
            'reading_date': fields.Datetime.now().replace(month=1, year=2024),
            'energy_consumed': 1200.0,
        })

        # Refresh to get updated computed values
        energy_target.refresh()

        # With 1200 actual vs 1000 target, should not be achieved
        self.assertFalse(energy_target.achieved)
    def test_energy_equipment_efficiency_rating(self):
        """Test energy equipment efficiency rating"""
        equipment = self.env['wms.energy.equipment'].create({
            'name': 'Efficiency Test Equipment',
            'owner_code': 'ETE',
            'equipment_type': 'machinery',
            'efficiency_rating': 85.5,  # 85.5%
        })

        self.assertEqual(equipment.efficiency_rating, 85.5)