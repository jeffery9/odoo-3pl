from odoo.tests import TransactionCase
from odoo import fields


class TestWmsLaborManagement(TransactionCase):
    """Test cases for WMS Labor Management module"""

    def setUp(self):
        super().setUp()
        # Create test data
        self.test_owner = self.env['wms.owner'].create({
            'name': 'Test Labor Management Owner',
            'owner_code': 'TLMO',
            'is_warehouse_owner': True,
        })

        self.test_employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'work_email': 'test.employee@example.com',
        })

        self.test_department = self.env['hr.department'].create({
            'name': 'Test Department',
        })

        self.test_activity = self.env['wms.labor.activity'].create({
            'name': 'Test Picking Activity',
            'owner_code': 'TPA',
            'activity_type': 'picking',
            'standard_time': 30.0,  # 30 minutes
        })

        self.test_location = self.env['stock.location'].create({
            'name': 'Test Location',
            'usage': 'internal',
        })

        self.test_picking_type = self.env['stock.picking.type'].create({
            'name': 'Test Picking Type',
            'code': 'outgoing',
            'sequence_code': 'OUT',
            'default_location_src_id': self.test_location.id,
            'default_location_dest_id': self.test_location.id,
        })

        self.test_product = self.env['product.product'].create({
            'name': 'Test Product for Labor',
                        'categ_id': self.env.ref('product.product_category_all').id,
        })

        # Create a test picking
        self.test_picking = self.env['stock.picking'].create({
            'name': 'Test Picking for Labor',
            'picking_type_id': self.test_picking_type.id,
            'location_id': self.test_location.id,
            'location_dest_id': self.test_location.id,
            'owner_id': self.test_owner.id,
        })
    def test_create_labor_task(self):
        """Test creating a labor task"""
        labor_task = self.env['wms.labor.task'].create({
            'name': 'Test Labor Task',
            'activity_id': self.test_activity.id,
            'assigned_to': self.test_employee.id,
            'owner_id': self.test_owner.id,
            'planned_start_date': fields.Datetime.now(),
            'status': 'draft',
        })

        self.assertTrue(labor_task.task_code.startswith('LAB'))
        self.assertEqual(labor_task.name, 'Test Labor Task')
        self.assertEqual(labor_task.activity_id.id, self.test_activity.id)
        self.assertEqual(labor_task.assigned_to.id, self.test_employee.id)
        self.assertEqual(labor_task.status, 'draft')
    def test_labor_task_status_flow(self):
        """Test the status flow of labor tasks"""
        labor_task = self.env['wms.labor.task'].create({
            'name': 'Status Flow Test',
            'activity_id': self.test_activity.id,
            'assigned_to': self.test_employee.id,
            'owner_id': self.test_owner.id,
            'planned_start_date': fields.Datetime.now(),
            'status': 'draft',
        })

        self.assertEqual(labor_task.status, 'draft')

        # Start the task
        labor_task.action_start_task()
        self.assertEqual(labor_task.status, 'in_progress')
        self.assertIsNotNone(labor_task.actual_start_date)

        # Complete the task
        labor_task.action_complete_task()
        self.assertEqual(labor_task.status, 'completed')
        self.assertIsNotNone(labor_task.actual_end_date)

        # Reset to assigned
        labor_task.action_reset_to_assigned()
        self.assertEqual(labor_task.status, 'assigned')
        self.assertIsNone(labor_task.actual_start_date)
    def test_labor_task_duration_computation(self):
        """Test duration computation for labor tasks"""
        from datetime import datetime, timedelta

        start_time = datetime.now()
        end_time = start_time + timedelta(hours=2)

        labor_task = self.env['wms.labor.task'].create({
            'name': 'Duration Test',
            'activity_id': self.test_activity.id,
            'assigned_to': self.test_employee.id,
            'owner_id': self.test_owner.id,
            'planned_start_date': fields.Datetime.now(),
            'actual_start_date': start_time,
            'actual_end_date': end_time,
        })

        self.assertEqual(labor_task.duration, 2.0)  # 2 hours

    def test_labor_task_efficiency_computation(self):
        """Test efficiency computation for labor tasks"""
        # Create a task with a standard duration of 0.5 hours (30 minutes)
        labor_task = self.env['wms.labor.task'].create({
            'name': 'Efficiency Test',
            'activity_id': self.test_activity.id,  # Has 30 min standard time = 0.5 hours
            'assigned_to': self.test_employee.id,
            'owner_id': self.test_owner.id,
            'planned_start_date': fields.Datetime.now(),
            'actual_start_date': fields.Datetime.now(),
            'actual_end_date': fields.Datetime.add(fields.Datetime.now(), hours=1),  # 1 hour actual
        })

        # Refresh to get updated computed values
        labor_task.refresh()

        # Standard duration is 0.5 hours, actual is 1 hour
        # Efficiency = (standard / actual) * 100 = (0.5 / 1) * 100 = 50%
        self.assertEqual(labor_task.standard_duration, 0.5)  # 30 minutes = 0.5 hours
        self.assertEqual(labor_task.efficiency, 50.0)
    def test_labor_activity_creation(self):
        """Test creating labor activities"""
        labor_activity = self.env['wms.labor.activity'].create({
            'name': 'Test Labor Activity',
            'owner_code': 'TLA',
            'description': 'Test labor activity description',
            'activity_type': 'receiving',
            'standard_time': 45.0,  # 45 minutes
        })

        self.assertEqual(labor_activity.name, 'Test Labor Activity')
        self.assertEqual(labor_activity.owner_code, 'TLA')
        self.assertEqual(labor_activity.activity_type, 'receiving')
        self.assertEqual(labor_activity.standard_time, 45.0)
    def test_labor_schedule_creation(self):
        """Test creating labor schedules"""
        from datetime import datetime, timedelta

        start_time = datetime.now()
        end_time = start_time + timedelta(hours=8)

        labor_schedule = self.env['wms.labor.schedule'].create({
            'name': 'Test Labor Schedule',
            'employee_id': self.test_employee.id,
            'date_start': start_time,
            'date_end': end_time,
            'schedule_type': 'regular',
        })

        self.assertEqual(labor_schedule.name, 'Test Labor Schedule')
        self.assertEqual(labor_schedule.employee_id.id, self.test_employee.id)
        self.assertEqual(labor_schedule.schedule_type, 'regular')
        self.assertTrue(labor_schedule.is_active)
    def test_employee_skill_creation(self):
        """Test creating employee skills"""
        employee_skill = self.env['wms.employee.skill'].create({
            'employee_id': self.test_employee.id,
            'skill_id': self.test_activity.id,
            'proficiency_level': 'advanced',
            'certification_date': fields.Date.today(),
        })

        self.assertEqual(employee_skill.employee_id.id, self.test_employee.id)
        self.assertEqual(employee_skill.skill_id.id, self.test_activity.id)
        self.assertEqual(employee_skill.proficiency_level, 'advanced')
    def test_labor_performance_creation(self):
        """Test creating labor performance records"""
        labor_performance = self.env['wms.labor.performance'].create({
            'employee_id': self.test_employee.id,
            'activity_id': self.test_activity.id,
            'date_recorded': fields.Date.today(),
            'tasks_completed': 5,
            'hours_worked': 8.0,
            'efficiency_rate': 110.0,  # 110% efficiency
        })

        self.assertEqual(labor_performance.employee_id.id, self.test_employee.id)
        self.assertEqual(labor_performance.activity_id.id, self.test_activity.id)
        self.assertEqual(labor_performance.tasks_completed, 5)
        self.assertEqual(labor_performance.efficiency_rate, 110.0)
        # Productivity score = (efficiency * tasks) / 100 = (110 * 5) / 100 = 5.5
        self.assertEqual(labor_performance.productivity_score, 5.5)
    def test_labor_cost_creation(self):
        """Test creating labor cost records"""
        labor_cost = self.env['wms.labor.cost'].create({
            'employee_id': self.test_employee.id,
            'activity_id': self.test_activity.id,
            'date': fields.Date.today(),
            'hours_worked': 8.0,
            'hourly_rate': 25.0,
            'overtime_rate': 1.0,
        })

        self.assertEqual(labor_cost.employee_id.id, self.test_employee.id)
        self.assertEqual(labor_cost.activity_id.id, self.test_activity.id)
        self.assertEqual(labor_cost.hours_worked, 8.0)
        self.assertEqual(labor_cost.hourly_rate, 25.0)
        self.assertEqual(labor_cost.total_cost, 200.0)  # 8 * 25 * 1

    def test_labor_cost_with_overtime(self):
        """Test labor cost calculation with overtime"""
        labor_cost = self.env['wms.labor.cost'].create({
            'employee_id': self.test_employee.id,
            'activity_id': self.test_activity.id,
            'date': fields.Date.today(),
            'hours_worked': 2.0,
            'hourly_rate': 25.0,
            'overtime_rate': 1.5,  # 1.5x overtime rate
        })

        self.assertEqual(labor_cost.total_cost, 75.0)  # 2 * 25 * 1.5

    def test_labor_task_with_related_work(self):
        """Test labor task with related picking"""
        labor_task = self.env['wms.labor.task'].create({
            'name': 'Related Work Test',
            'activity_id': self.test_activity.id,
            'assigned_to': self.test_employee.id,
            'owner_id': self.test_owner.id,
            'picking_id': self.test_picking.id,
            'planned_start_date': fields.Datetime.now(),
        })

        self.assertEqual(labor_task.picking_id.id, self.test_picking.id)
        self.assertEqual(labor_task.owner_id.id, self.test_owner.id)
    def test_labor_task_priority_levels(self):
        """Test different priority levels for labor tasks"""
        priorities = [('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Urgent')]

        for priority_value, priority_name in priorities:
            labor_task = self.env['wms.labor.task'].create({
                'name': f'Test Priority {priority_name}',
                'activity_id': self.test_activity.id,
                'assigned_to': self.test_employee.id,
                'owner_id': self.test_owner.id,
                'priority': priority_value,
                'planned_start_date': fields.Datetime.now(),
            })

            self.assertEqual(labor_task.priority, priority_value)
    def test_labor_schedule_overlapping_constraint(self):
        """Test that overlapping schedules are prevented"""
        from datetime import datetime, timedelta

        start_time = datetime.now()
        end_time = start_time + timedelta(hours=8)

        # Create first schedule
        schedule1 = self.env['wms.labor.schedule'].create({
            'name': 'First Schedule',
            'employee_id': self.test_employee.id,
            'date_start': start_time,
            'date_end': end_time,
        })

        # Try to create overlapping schedule - should raise validation error
        with self.assertRaises(Exception):
            self.env['wms.labor.schedule'].create({
                'name': 'Overlapping Schedule',
                'employee_id': self.test_employee.id,
                'date_start': start_time + timedelta(hours=4),  # Overlaps with first schedule
                'date_end': end_time + timedelta(hours=4),
            })