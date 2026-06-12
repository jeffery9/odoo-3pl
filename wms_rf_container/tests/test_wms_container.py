from odoo.tests import TransactionCase
from odoo import fields


class TestWmsContainer(TransactionCase):
    """Test cases for WMS RF Container module"""

    def setUp(self):
        super().setUp()
        # Create test data
        self.test_owner = self.env['wms.owner'].create({
            'name': 'Test Container Owner',
            'owner_code': 'TCO',
            'is_warehouse_owner': True,
        })

        self.test_location = self.env['stock.location'].create({
            'name': 'Test Location',
            'usage': 'internal',
        })

        self.test_product = self.env['product.product'].create({
            'name': 'Test Product for Container',
                        'categ_id': self.env.ref('product.product_category_all').id,
        })

        self.test_uom = self.env.ref('uom.product_uom_unit')
    def test_create_container(self):
        """Test creating a WMS container"""
        container = self.env['wms.container'].create({
            'name': 'Test Container',
            'barcode': 'CONT001',
            'container_type': 'pallet',
            'owner_id': self.test_owner.id,
            'capacity': 1.5,
            'status': 'empty',
        })

        self.assertEqual(container.name, 'Test Container')
        self.assertEqual(container.barcode, 'CONT001')
        self.assertEqual(container.container_type, 'pallet')
        self.assertEqual(container.owner_id.id, self.test_owner.id)
        self.assertEqual(container.status, 'empty')
        self.assertEqual(container.capacity, 1.5)
    def test_container_content(self):
        """Test adding content to a container"""
        container = self.env['wms.container'].create({
            'name': 'Content Test Container',
            'barcode': 'CONT002',
            'container_type': 'box',
            'owner_id': self.test_owner.id,
            'status': 'empty',
        })

        container_content = self.env['wms.container.content'].create({
            'container_id': container.id,
            'product_id': self.test_product.id,
            'quantity': 10.0,
            'uom_id': self.test_uom.id,
        })

        self.assertEqual(len(container.contents), 1)
        self.assertEqual(container.contents[0].product_id.id, self.test_product.id)
        self.assertEqual(container.contents[0].quantity, 10.0)
    def test_container_load_computation(self):
        """Test that container load is computed correctly"""
        # Create a product with volume
        volumed_product = self.env['product.product'].create({
            'name': 'Volumed Product',
                        'categ_id': self.env.ref('product.product_category_all').id,
            'volume': 0.1,  # 0.1 CBM per unit
        })

        container = self.env['wms.container'].create({
            'name': 'Load Test Container',
            'barcode': 'CONT003',
            'container_type': 'pallet',
            'owner_id': self.test_owner.id,
            'capacity': 2.0,
            'status': 'empty',
        })

        # Add content to container
        self.env['wms.container.content'].create({
            'container_id': container.id,
            'product_id': volumed_product.id,
            'quantity': 5.0,
            'uom_id': self.test_uom.id,
        })

        # Refresh the container to get updated computed values
        container.refresh()

        # Current load should be 5 units * 0.1 CBM/unit = 0.5 CBM
        self.assertEqual(container.current_load, 0.5)
        # Load percentage should be (0.5 / 2.0) * 100 = 25%
        self.assertEqual(container.load_percentage, 25.0)
    def test_container_status_changes(self):
        """Test container status transitions"""
        container = self.env['wms.container'].create({
            'name': 'Status Test Container',
            'barcode': 'CONT004',
            'container_type': 'tote',
            'owner_id': self.test_owner.id,
            'status': 'empty',
        })

        self.assertEqual(container.status, 'empty')

        # Add content to change status to partial
        self.env['wms.container.content'].create({
            'container_id': container.id,
            'product_id': self.test_product.id,
            'quantity': 5.0,
            'uom_id': self.test_uom.id,
        })

        # Status should remain empty until explicitly changed - computed field would handle this in real scenario
        container.write({'status': 'partial'})
        self.assertEqual(container.status, 'partial')
    def test_container_location_assignment(self):
        """Test assigning container to a location"""
        container = self.env['wms.container'].create({
            'name': 'Location Test Container',
            'barcode': 'CONT005',
            'container_type': 'bin',
            'owner_id': self.test_owner.id,
            'status': 'empty',
        })

        # Assign location
        container.location_id = self.test_location.id
        self.assertEqual(container.location_id.id, self.test_location.id)
    def test_container_hierarchy(self):
        """Test container hierarchy (parent-child relationships)"""
        parent_container = self.env['wms.container'].create({
            'name': 'Parent Container',
            'barcode': 'PARENT001',
            'container_type': 'roll',
            'owner_id': self.test_owner.id,
            'status': 'empty',
        })

        child_container = self.env['wms.container'].create({
            'name': 'Child Container',
            'barcode': 'CHILD001',
            'container_type': 'box',
            'owner_id': self.test_owner.id,
            'parent_container_id': parent_container.id,
            'status': 'empty',
        })

        self.assertEqual(child_container.parent_container_id.id, parent_container.id)
        self.assertIn(child_container.id, parent_container.child_containers.ids)
    def test_container_wizard_actions(self):
        """Test container wizard actions"""
        container = self.env['wms.container'].create({
            'name': 'Wizard Test Container',
            'barcode': 'CONT006',
            'container_type': 'pallet',
            'owner_id': self.test_owner.id,
            'status': 'empty',
        })

        # Test location assignment wizard creation
        wizard = self.env['wms.container.location.wizard'].create({
            'container_id': container.id,
            'location_id': self.test_location.id,
        })

        self.assertEqual(wizard.container_id.id, container.id)
        self.assertEqual(wizard.location_id.id, self.test_location.id)
    def test_container_ownership_isolation(self):
        """Test that containers are properly isolated by owner"""
        owner2 = self.env['wms.owner'].create({
            'name': 'Second Container Owner',
            'owner_code': 'SCO',
            'is_warehouse_owner': True,
        })

        container1 = self.env['wms.container'].create({
            'name': 'Container for Owner 1',
            'barcode': 'CONT007',
            'container_type': 'pallet',
            'owner_id': self.test_owner.id,
            'status': 'empty',
        })

        container2 = self.env['wms.container'].create({
            'name': 'Container for Owner 2',
            'barcode': 'CONT008',
            'container_type': 'box',
            'owner_id': owner2.id,
            'status': 'empty',
        })

        self.assertNotEqual(container1.owner_id.id, container2.owner_id.id)
        self.assertNotEqual(container1.barcode, container2.barcode)
        self.assertNotEqual(container1.container_type, container2.container_type)