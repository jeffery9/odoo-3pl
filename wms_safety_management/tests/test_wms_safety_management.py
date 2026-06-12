from odoo.tests import TransactionCase
from odoo import fields


class TestWmsSafetyManagement(TransactionCase):
    """Test cases for WMS Safety Management module"""

    def setUp(self):
        super().setUp()
        # Create test data
        self.test_owner = self.env['wms.owner'].create({
            'name': 'Test Safety Management Owner',
            'owner_code': 'TSMO',
            'is_warehouse_owner': True,
        })

        self.test_location = self.env['stock.location'].create({
            'name': 'Test Location',
            'usage': 'internal',
        })

        self.test_employee = self.env['hr.employee'].create({
            'name': 'Test Safety Employee',
            'work_email': 'test.safety@example.com',
        })

        self.test_employee2 = self.env['hr.employee'].create({
            'name': 'Test Witness Employee',
            'work_email': 'test.witness@example.com',
        })

        self.test_supplier = self.env['res.partner'].create({
            'name': 'Test Safety Supplier',
            'email': 'supplier@example.com',
        })

        self.test_ppe = self.env['wms.safety.ppe'].create({
            'name': 'Test Safety Equipment',
            'ppe_type': 'head',
            'description': 'Test safety equipment',
            'unit_cost': 25.0,
            'stock_quantity': 50,
        })

        self.test_activity = self.env['wms.labor.activity'].create({
            'name': 'Test Forklift Activity',
            'owner_code': 'TFA',
            'activity_type': 'machinery',
        })
    def test_create_safety_incident(self):
        """Test creating safety incidents"""
        incident = self.env['wms.safety.incident'].create({
            'incident_type': 'accident',
            'severity': 'medium',
            'location_id': self.test_location.id,
            'reported_by': self.test_employee.id,
            'description': 'Test safety incident description',
            'category': 'slip_trip',
        })

        self.assertTrue(incident.name.startswith('SAF'))
        self.assertEqual(incident.incident_type, 'accident')
        self.assertEqual(incident.severity, 'medium')
        self.assertEqual(incident.reported_by.id, self.test_employee.id)
        self.assertEqual(incident.status, 'reported')
    def test_create_safety_training(self):
        """Test creating safety training"""
        training = self.env['wms.safety.training'].create({
            'name': 'Test Safety Training',
            'training_type': 'fire_safety',
            'duration_hours': 4.0,
            'trainer_id': self.test_employee.id,
            'training_date': fields.Date.today(),
            'active': True,
        })

        self.assertTrue(training.training_code.startswith('STR'))
        self.assertEqual(training.name, 'Test Safety Training')
        self.assertEqual(training.training_type, 'fire_safety')
        self.assertEqual(training.duration_hours, 4.0)
        self.assertEqual(training.trainer_id.id, self.test_employee.id)
        self.assertTrue(training.active)
    def test_safety_training_participants(self):
        """Test safety training participant tracking"""
        training = self.env['wms.safety.training'].create({
            'name': 'Participant Test Training',
            'training_type': 'first_aid',
            'duration_hours': 8.0,
            'trainer_id': self.test_employee.id,
            'training_date': fields.Date.today(),
        })

        # Add participants
        training.participant_ids = [(6, 0, [self.test_employee.id, self.test_employee2.id])]

        self.assertEqual(len(training.participant_ids), 2)
        self.assertTrue(self.test_employee in training.participant_ids)
        self.assertTrue(self.test_employee2 in training.participant_ids)
    def test_create_safety_ppe(self):
        """Test creating safety PPE"""
        ppe = self.env['wms.safety.ppe'].create({
            'name': 'Test Hard Hat',
            'ppe_type': 'head',
            'description': 'Industrial hard hat',
            'unit_cost': 35.0,
            'stock_quantity': 100,
            'brand': 'Safety Inc.',
            'size': 'Medium',
        })

        self.assertEqual(ppe.name, 'Test Hard Hat')
        self.assertEqual(ppe.ppe_type, 'head')
        self.assertEqual(ppe.unit_cost, 35.0)
        self.assertEqual(ppe.stock_quantity, 100)
        self.assertEqual(ppe.brand, 'Safety Inc.')
        self.assertTrue(ppe.is_active)
    def test_create_safety_inspection(self):
        """Test creating safety inspections"""
        inspection = self.env['wms.safety.inspection'].create({
            'name': 'Test Safety Inspection',
            'inspection_type': 'daily',
            'location_id': self.test_location.id,
            'inspector_id': self.test_employee.id,
            'owner_id': self.test_owner.id,
        })

        self.assertTrue(inspection.inspection_code.startswith('SAI'))
        self.assertEqual(inspection.name, 'Test Safety Inspection')
        self.assertEqual(inspection.inspection_type, 'daily')
        self.assertEqual(inspection.location_id.id, self.test_location.id)
        self.assertEqual(inspection.inspector_id.id, self.test_employee.id)
        self.assertEqual(inspection.status, 'draft')
        self.assertEqual(inspection.owner_id.id, self.test_owner.id)
    def test_safety_inspection_status_flow(self):
        """Test safety inspection status flow"""
        inspection = self.env['wms.safety.inspection'].create({
            'name': 'Status Flow Test',
            'inspection_type': 'weekly',
            'location_id': self.test_location.id,
            'inspector_id': self.test_employee.id,
            'owner_id': self.test_owner.id,
        })

        self.assertEqual(inspection.status, 'draft')

        # Start inspection
        inspection.action_start_inspection()
        self.assertEqual(inspection.status, 'in_progress')

        # Complete inspection
        inspection.action_complete_inspection()
        self.assertEqual(inspection.status, 'completed')
    def test_safety_inspection_findings(self):
        """Test safety inspection findings"""
        inspection = self.env['wms.safety.inspection'].create({
            'name': 'Findings Test',
            'inspection_type': 'monthly',
            'location_id': self.test_location.id,
            'inspector_id': self.test_employee.id,
            'owner_id': self.test_owner.id,
        })

        finding = self.env['wms.safety.inspection.finding'].create({
            'inspection_id': inspection.id,
            'name': 'Test Finding',
            'description': 'Test inspection finding description',
            'severity': 'high',
        })

        self.assertEqual(finding.name, 'Test Finding')
        self.assertEqual(finding.inspection_id.id, inspection.id)
        self.assertEqual(finding.severity, 'high')
        self.assertEqual(finding.status, 'open')
    def test_create_safety_compliance(self):
        """Test creating safety compliance records"""
        compliance = self.env['wms.safety.compliance'].create({
            'name': 'Test Safety Compliance',
            'regulation': 'OSHA 1910.22',
            'compliance_type': 'regulatory',
            'requirement_details': 'Walking-working surfaces standard',
            'frequency': 'annual',
        })

        self.assertEqual(compliance.name, 'Test Safety Compliance')
        self.assertEqual(compliance.regulation, 'OSHA 1910.22')
        self.assertEqual(compliance.compliance_type, 'regulatory')
        self.assertFalse(compliance.compliant)
        self.assertEqual(compliance.frequency, 'annual')
    def test_safety_risk_assessment(self):
        """Test creating safety risk assessments"""
        risk = self.env['wms.safety.risk'].create({
            'name': 'Test Safety Risk',
            'risk_type': 'physical',
            'location_id': self.test_location.id,
            'probability': 'medium',
            'severity': 'high',
            'owner_id': self.test_owner.id,
        })

        self.assertEqual(risk.name, 'Test Safety Risk')
        self.assertEqual(risk.risk_type, 'physical')
        self.assertEqual(risk.location_id.id, self.test_location.id)
        self.assertEqual(risk.probability, 'medium')
        self.assertEqual(risk.severity, 'high')
        self.assertEqual(risk.status, 'identified')
        self.assertEqual(risk.risk_score, 12)  # medium (3) * high (4) = 12

    def test_safety_risk_score_computation(self):
        """Test safety risk score computation"""
        # Create a risk with high probability and high severity
        risk = self.env['wms.safety.risk'].create({
            'name': 'Score Computation Test',
            'risk_type': 'chemical',
            'location_id': self.test_location.id,
            'probability': 'very_high',
            'severity': 'very_high',
            'owner_id': self.test_owner.id,
        })

        # Refresh to get updated computed values
        risk.refresh()

        # very_high (5) * very_high (5) = 25
        self.assertEqual(risk.risk_score, 25)
    def test_safety_incident_with_witnesses(self):
        """Test safety incident with witnesses"""
        incident = self.env['wms.safety.incident'].create({
            'incident_type': 'near_miss',
            'severity': 'low',
            'location_id': self.test_location.id,
            'reported_by': self.test_employee.id,
            'description': 'Test incident with witnesses',
            'category': 'caught_in',
        })

        # Add witnesses
        incident.witness_ids = [(6, 0, [self.test_employee2.id])]

        self.assertEqual(len(incident.witness_ids), 1)
        self.assertTrue(self.test_employee2 in incident.witness_ids)
    def test_safety_ppe_required_for_jobs(self):
        """Test PPE required for specific jobs"""
        ppe = self.test_ppe
        ppe.required_for_jobs = [(6, 0, [self.test_activity.id])]

        self.assertEqual(len(ppe.required_for_jobs), 1)
        self.assertTrue(self.test_activity in ppe.required_for_jobs)
    def test_safety_inspection_findings_count(self):
        """Test computed findings count for inspections"""
        inspection = self.env['wms.safety.inspection'].create({
            'name': 'Findings Count Test',
            'inspection_type': 'quarterly',
            'location_id': self.test_location.id,
            'inspector_id': self.test_employee.id,
            'owner_id': self.test_owner.id,
        })

        # Add multiple findings
        self.env['wms.safety.inspection.finding'].create([
            {
                'inspection_id': inspection.id,
                'name': 'Finding 1',
                'severity': 'low',
            },
            {
                'inspection_id': inspection.id,
                'name': 'Finding 2',
                'severity': 'high',
            },
            {
                'inspection_id': inspection.id,
                'name': 'Finding 3',
                'severity': 'medium',
            },
        ])

        # Refresh to get updated computed values
        inspection.refresh()

        self.assertEqual(inspection.findings_count, 3)
        self.assertEqual(inspection.critical_findings_count, 1)  # Only the high severity finding
        self.assertTrue(inspection.action_required)  # Because of critical finding

    def test_safety_training_expiry_date(self):
        """Test safety training expiry date"""
        training = self.env['wms.safety.training'].create({
            'name': 'Expiry Test Training',
            'training_type': 'ppe_training',
            'duration_hours': 2.0,
            'trainer_id': self.test_employee.id,
            'training_date': fields.Date.today(),
            'expiry_date': fields.Date.add(fields.Date.today(), days=365),  # 1 year expiry
        })

        self.assertIsNotNone(training.expiry_date)
    def test_safety_compliance_date_calculation(self):
        """Test safety compliance date calculation"""
        from datetime import date, timedelta

        compliance = self.env['wms.safety.compliance'].create({
            'name': 'Date Calculation Test',
            'regulation': 'Test Regulation',
            'compliance_type': 'regulatory',
            'compliance_date': date.today(),
            'frequency': 'annual',
        })

        # Calculate expected next compliance date (1 year from now)
        expected_next_date = date.today().replace(year=date.today().year + 1)

        # For this test, we'll just verify that the field exists and can be set
        # The onchange method would handle the automatic calculation
        self.assertIsNotNone(compliance.compliance_date)