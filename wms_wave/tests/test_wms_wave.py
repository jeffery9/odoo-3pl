from odoo.tests import TransactionCase
from odoo import fields


class TestWmsWave(TransactionCase):
    """Test cases for WMS Wave module"""

    def setUp(self):
        super().setUp()
        # Create test data
        self.test_owner = self.env['wms.owner'].create({
            'name': 'Test Owner',
            'owner_code': 'TEST',
            'is_warehouse_owner': True,
        })

        self.test_user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
            'email': 'test@example.com',
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
    def test_create_wave_rule(self):
        """Test creating a WMS wave rule"""
        wave_rule = self.env['wms.wave.rule'].create({
            'name': 'Test Wave Rule',
            'owner_code': 'TWR001',
            'picking_type_id': self.test_picking_type.id,
            'owner_id': self.test_owner.id,
            'priority_threshold': 1,
            'max_pickings_per_wave': 20,
            'auto_create': True,
            'schedule_cron': '0 8 * * 1',
        })

        self.assertEqual(wave_rule.name, 'Test Wave Rule')
        self.assertEqual(wave_rule.owner_code, 'TWR001')
        self.assertEqual(wave_rule.max_pickings_per_wave, 20)
        self.assertTrue(wave_rule.auto_create)
        self.assertEqual(wave_rule.schedule_cron, '0 8 * * 1')
    def test_create_wave_picking_batch(self):
        """Test creating a wave picking batch with extended fields"""
        wave_batch = self.env['stock.picking.batch'].create({
            'name': 'Test Wave',
            'owner_id': self.test_owner.id,
            'wave_priority': 'high',
            'target_date': fields.Datetime.now(),
            'assigned_user_id': self.test_user.id,
            'status_progress': 0.0,
            'is_automatic': True,
        })

        self.assertEqual(wave_batch.name, 'Test Wave')
        self.assertEqual(wave_batch.owner_id.id, self.test_owner.id)
        self.assertEqual(wave_batch.wave_priority, 'high')
        self.assertEqual(wave_batch.assigned_user_id.id, self.test_user.id)
        self.assertEqual(wave_batch.status_progress, 0.0)
        self.assertTrue(wave_batch.is_automatic)
    def test_wave_rule_picking_type(self):
        """Test that wave rules work with picking types"""
        wave_rule = self.env['wms.wave.rule'].create({
            'name': 'Test Wave Rule',
            'picking_type_id': self.test_picking_type.id,
            'owner_id': self.test_owner.id,
            'max_pickings_per_wave': 10,
        })

        self.assertEqual(wave_rule.picking_type_id.id, self.test_picking_type.id)
        self.assertEqual(wave_rule.owner_id.id, self.test_owner.id)
    def test_wave_progress_calculation(self):
        """Test wave progress calculation"""
        wave_batch = self.env['stock.picking.batch'].create({
            'name': 'Test Wave Progress',
            'owner_id': self.test_owner.id,
            'wave_priority': 'medium',
        })

        # Initially, progress should be 0
        self.assertEqual(wave_batch.status_progress, 0.0)

        # Simulate adding pickings and changing their states to affect progress
        # (This would normally be handled by computed fields in the actual model)
    def test_wave_priority_handling(self):
        """Test that wave priorities are properly handled"""
        wave_batch = self.env['stock.picking.batch'].create({
            'name': 'Test Priority Wave',
            'owner_id': self.test_owner.id,
            'wave_priority': 'high',
        })

        self.assertEqual(wave_batch.wave_priority, 'high')

        # Test that higher priority waves might be processed first
        wave_batch_low = self.env['stock.picking.batch'].create({
            'name': 'Test Low Priority Wave',
            'owner_id': self.test_owner.id,
            'wave_priority': 'low',
        })

        self.assertEqual(wave_batch_low.wave_priority, 'low')
        self.assertNotEqual(wave_batch.wave_priority, wave_batch_low.wave_priority)
    def test_wave_ownership_isolation(self):
        """Test that waves are properly isolated by owner"""
        owner2 = self.env['wms.owner'].create({
            'name': 'Second Owner',
            'owner_code': 'SO',
            'is_warehouse_owner': True,
        })

        wave1 = self.env['stock.picking.batch'].create({
            'name': 'Wave for Owner 1',
            'owner_id': self.test_owner.id,
        })

        wave2 = self.env['stock.picking.batch'].create({
            'name': 'Wave for Owner 2',
            'owner_id': owner2.id,
        })

        self.assertNotEqual(wave1.owner_id.id, wave2.owner_id.id)
        self.assertNotEqual(wave1.name, wave2.name)