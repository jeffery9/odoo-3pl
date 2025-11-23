from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import math


class WmsPackingRule(models.Model):
    """
    Packing Rule Configuration
    Configure automatic packing suggestions and optimization rules
    """
    _name = 'wms.packing.rule'
    _description = 'WMS Packing Rule'
    _order = 'sequence, name'

    name = fields.Char('Rule Name', required=True)
    code = fields.Char('Rule Code', required=True, copy=False)
    active = fields.Boolean('Active', default=True)
    sequence = fields.Integer('Sequence', default=10)

    # Rule Type
    rule_type = fields.Selection([
        ('size_based', 'Size Optimization'),
        ('weight_based', 'Weight Optimization'),
        ('volume_based', 'Volume Optimization'),
        ('mixed', 'Mixed Optimization'),
        ('fixed', 'Fixed Packing'),
        ('dynamic', 'Dynamic Packing'),
    ], string='Rule Type', required=True, default='mixed')

    # Application Conditions
    warehouse_ids = fields.Many2many('stock.warehouse', string='Applicable Warehouses')
    product_category_ids = fields.Many2many('product.category', string='Applicable Product Categories')
    owner_ids = fields.Many2many('wms.owner', string='Applicable Owners')
    picking_type_ids = fields.Many2many('stock.picking.type', string='Applicable Operation Types')

    # Packing Constraints
    max_box_weight = fields.Float('Maximum Box Weight (kg)')
    max_box_volume = fields.Float('Maximum Box Volume (m³)')
    max_items_per_box = fields.Integer('Maximum Items per Box')
    max_boxes_per_order = fields.Integer('Maximum Boxes per Order')

    # Dimension Constraints
    max_length = fields.Float('Maximum Length (cm)')
    max_width = fields.Float('Maximum Width (cm)')
    max_height = fields.Float('Maximum Height (cm)')
    max_dimension_sum = fields.Float('Maximum Dimension Sum (cm)')  # length + width + height

    # Packing Strategy
    strategy = fields.Selection([
        ('first_fit', 'First Fit (FF)'),
        ('best_fit', 'Best Fit (BF)'),
        ('first_fit_decreasing', 'First Fit Decreasing (FFD)'),
        ('best_fit_decreasing', 'Best Fit Decreasing (BFD)'),
        ('next_fit', 'Next Fit (NF)'),
    ], string='Packing Algorithm', default='first_fit_decreasing')

    # Optimization Target
    optimization_target = fields.Selection([
        ('min_boxes', 'Minimize Box Count'),
        ('max_utilization', 'Maximize Utilization'),
        ('balanced', 'Balanced Optimization'),
    ], string='Optimization Target', default='min_boxes')

    # Special Rules
    separate_hazardous = fields.Boolean('Separate Hazardous Items', default=True)
    separate_fragile = fields.Boolean('Separate Fragile Items', default=True)
    max_fragile_per_box = fields.Integer('Maximum Fragile Items per Box')
    avoid_mixed_temperature = fields.Boolean('Avoid Mixed Temperature Zones')
    max_stack_height = fields.Integer('Maximum Stack Height (Layers)')

    # Volume Ratio Control
    min_volume_utilization = fields.Float('Minimum Volume Utilization (%)', default=70.0)
    max_volume_utilization = fields.Float('Maximum Volume Utilization (%)', default=95.0)

    # Box Type Configuration
    box_type_ids = fields.Many2many(
        'wms.packing.box.type',
        'wms_packing_rule_box_type_rel',
        'rule_id',
        'box_type_id',
        string='Applicable Box Types'
    )

    # Status and Statistics
    last_calculated = fields.Datetime('Last Calculation Time')
    success_rate = fields.Float('Success Rate (%)', readonly=True)
    avg_utilization = fields.Float('Average Utilization (%)', readonly=True)
    notes = fields.Text('Notes')

    @api.constrains('max_box_weight', 'max_box_volume', 'max_items_per_box')
    def _check_positive_constraints(self):
        for rule in self:
            if rule.max_box_weight < 0:
                raise ValidationError(_('最大箱重不能为负数。'))
            if rule.max_box_volume < 0:
                raise ValidationError(_('最大箱体积不能为负数。'))
            if rule.max_items_per_box < 0:
                raise ValidationError(_('每箱Maximum Items不能为负数。'))

    def suggest_packing(self, picking):
        """
        为拣货单建议装箱方案
        """
        if not self.active:
            return []

        # 获取拣货单中的商品信息
        items = self._get_picking_items(picking)

        # 根据规则类型计算装箱方案
        if self.rule_type == 'fixed':
            return self._calculate_fixed_packing(items)
        elif self.rule_type == 'dynamic':
            return self._calculate_dynamic_packing(items)
        else:
            return self._calculate_optimized_packing(items)

    def _get_picking_items(self, picking):
        """
        获取拣货单中的商品信息
        """
        items = []
        for move_line in picking.move_line_ids:
            if move_line.qty_done > 0:
                product = move_line.product_id
                items.append({
                    'product': product,
                    'quantity': move_line.qty_done,
                    'uom': move_line.product_uom_id,
                    'lot_ids': move_line.lot_ids,
                    'is_hazardous': product.is_hazardous or False,
                    'is_fragile': product.is_fragile or False,
                    'temperature_zone': product.temperature_zone or 'ambient',
                    'dimensions': {
                        'length': product.length or 0,
                        'width': product.width or 0,
                        'height': product.height or 0,
                        'volume': product.volume or 0,
                        'weight': product.weight or 0,
                    }
                })
        return items

    def _calculate_fixed_packing(self, items):
        """
        固定装箱计算
        """
        packing_plan = []
        for item in items:
            # 简化处理：每种商品单独一箱（或按固定数量装箱）
            remaining_qty = item['quantity']
            while remaining_qty > 0:
                # 确定每箱数量
                box_qty = min(remaining_qty, self.max_items_per_box or remaining_qty)
                packing_plan.append({
                    'items': [item['product'].name],
                    'quantity': box_qty,
                    'box_type': self._select_box_type(item)
                })
                remaining_qty -= box_qty
        return packing_plan

    def _calculate_dynamic_packing(self, items):
        """
        动态装箱计算
        """
        # 简化实现：按顺序装箱，优先填充利用空间
        boxes = []
        current_box = {
            'items': [],
            'weight': 0,
            'volume': 0,
            'quantity': 0,
            'box_type': None
        }

        for item in items:
            product = item['product']
            qty_remaining = item['quantity']

            while qty_remaining > 0:
                # 计算当前商品单件的重量和体积
                item_weight = item['dimensions']['weight']
                item_volume = item['dimensions']['volume']

                # 检查是否能放入当前箱子
                can_fit = self._can_item_fit_in_box(
                    current_box, item, qty_remaining
                )

                if can_fit:
                    # 添加到当前箱子
                    current_box['items'].append({
                        'product': product,
                        'quantity': 1
                    })
                    current_box['weight'] += item_weight
                    current_box['volume'] += item_volume
                    current_box['quantity'] += 1
                    qty_remaining -= 1
                else:
                    # 保存当前箱子，开始新箱子
                    if current_box['items']:
                        boxes.append(current_box)

                    # 创建新箱子
                    current_box = {
                        'items': [],
                        'weight': item_weight,
                        'volume': item_volume,
                        'quantity': 1,
                        'box_type': self._select_box_type(item)
                    }
                    current_box['items'].append({
                        'product': product,
                        'quantity': 1
                    })
                    qty_remaining -= 1

        # 添加最后一个箱子
        if current_box['items']:
            boxes.append(current_box)

        return boxes

    def _can_item_fit_in_box(self, box, item, item_qty):
        """
        检查商品是否能放入箱子
        """
        if self.max_box_weight and (box['weight'] + item['dimensions']['weight']) > self.max_box_weight:
            return False

        if self.max_box_volume and (box['volume'] + item['dimensions']['volume']) > self.max_box_volume:
            return False

        if self.max_items_per_box and (box['quantity'] + 1) > self.max_items_per_box:
            return False

        # 检查危险品约束
        if item['is_hazardous'] and self.separate_hazardous:
            # 如果箱内已有非危险品，则不能加入危险品
            existing_hazardous = any(
                existing_item['product'].is_hazardous for existing_item in box['items']
            )
            if box['items'] and not existing_hazardous:
                return False

        # 检查易碎品约束
        if item['is_fragile'] and self.separate_fragile:
            existing_fragile = any(
                existing_item['product'].is_fragile for existing_item in box['items']
            )
            if box['items'] and not existing_fragile:
                return False

        # 检查温区约束
        if self.avoid_mixed_temperature and box['items']:
            existing_temp_zone = box['items'][0]['product'].temperature_zone or 'ambient'
            if item['temperature_zone'] != existing_temp_zone:
                return False

        return True

    def _select_box_type(self, item):
        """
        选择适合的箱型
        """
        if self.box_type_ids:
            # 在配置的箱型中选择最合适的
            suitable_boxes = self.box_type_ids.filtered(
                lambda b: b.max_weight >= item['dimensions']['weight'] and
                         b.max_volume >= item['dimensions']['volume']
            )
            if suitable_boxes:
                # 返回容量最适中（不过大）的箱型
                box = min(suitable_boxes,
                         key=lambda b: max(b.max_weight - item['dimensions']['weight'], 0) +
                                     max(b.max_volume - item['dimensions']['volume'], 0))
                return box
        return None

    def _calculate_optimized_packing(self, items):
        """
        优化装箱计算（使用指定的装箱算法）
        """
        if self.strategy == 'first_fit':
            return self._first_fit_packing(items)
        elif self.strategy == 'best_fit':
            return self._best_fit_packing(items)
        elif self.strategy == 'first_fit_decreasing':
            return self._first_fit_decreasing_packing(items)
        elif self.strategy == 'best_fit_decreasing':
            return self._best_fit_decreasing_packing(items)
        else:
            return self._first_fit_packing(items)  # 默认使用首次适应

    def _first_fit_packing(self, items):
        """
        首次适应装箱算法
        """
        boxes = []

        for item in items:
            placed = False
            # 尝试放入现有箱子
            for box in boxes:
                if self._can_item_fit_in_box(box, item, item['quantity']):
                    # 将商品放入箱子（简化：逐个放入）
                    for _ in range(int(item['quantity'])):
                        box['items'].append({'product': item['product'], 'quantity': 1})
                        box['weight'] += item['dimensions']['weight']
                        box['volume'] += item['dimensions']['volume']
                        box['quantity'] += 1
                    placed = True
                    break

            if not placed:
                # 创建新箱子
                new_box = {
                    'items': [],
                    'weight': 0,
                    'volume': 0,
                    'quantity': 0,
                    'box_type': self._select_box_type(item)
                }
                for _ in range(int(item['quantity'])):
                    new_box['items'].append({'product': item['product'], 'quantity': 1})
                    new_box['weight'] += item['dimensions']['weight']
                    new_box['volume'] += item['dimensions']['volume']
                    new_box['quantity'] += 1
                boxes.append(new_box)

        return boxes

    def _first_fit_decreasing_packing(self, items):
        """
        首次适应递减装箱算法
        """
        # 按体积递减排列
        sorted_items = sorted(items, key=lambda x: x['dimensions']['volume'], reverse=True)
        return self._first_fit_packing(sorted_items)


class WmsPackingBoxType(models.Model):
    """
    装箱类型配置 - Box Type Configuration
    """
    _name = 'wms.packing.box.type'
    _description = 'WMS Packing Box Type'
    _order = 'name'

    name = fields.Char('箱型名称', required=True)
    code = fields.Char('箱型编码', required=True, copy=False)
    description = fields.Text('描述')
    active = fields.Boolean('启用', default=True)

    # 尺寸规格 Dimension Specifications
    length = fields.Float('长度(cm)', required=True)
    width = fields.Float('宽度(cm)', required=True)
    height = fields.Float('高度(cm)', required=True)

    # 容量限制 Capacity Limits
    max_weight = fields.Float('Maximum Weight (kg)', required=True)
    max_volume = fields.Float('Maximum Volume (m³)', required=True)
    max_items = fields.Integer('Maximum Items')

    # 物理特性 Physical Properties
    tare_weight = fields.Float('箱体重量(kg)', default=0.0)
    material = fields.Selection([
        ('cardboard', '纸箱'),
        ('plastic', '塑料箱'),
        ('wood', '木箱'),
        ('metal', '铁箱'),
        ('other', '其他'),
    ], string='材质', default='cardboard')

    # 适用场景 Application Scenarios
    is_thermal = fields.Boolean('保温箱', default=False)
    temperature_range = fields.Char('温区范围')
    is_reinforced = fields.Boolean('加强箱', default=False)
    max_drop_height = fields.Float('Maximum Drop Height (m)')

    # 成本信息 Cost Information
    cost = fields.Float('成本', digits='Product Price')
    rental_cost_per_day = fields.Float('日租金', digits='Product Price')

    owner_id = fields.Many2one('wms.owner', '货主', help='专属货主，留空为通用箱型')

    @api.constrains('length', 'width', 'height', 'max_weight', 'max_volume')
    def _check_positive_dimensions(self):
        for box_type in self:
            if any(dim <= 0 for dim in [box_type.length, box_type.width, box_type.height]):
                raise ValidationError(_('箱型尺寸必须大于0。'))
            if box_type.max_weight <= 0:
                raise ValidationError(_('最大承重必须大于0。'))
            if box_type.max_volume <= 0:
                raise ValidationError(_('最大容积必须大于0。'))

    @api.onchange('length', 'width', 'height')
    def _onchange_dimensions(self):
        """
        根据尺寸计算体积
        """
        for box_type in self:
            if box_type.length and box_type.width and box_type.height:
                box_type.max_volume = (box_type.length * box_type.width * box_type.height) / 1000000  # 转换为立方米


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # 添加装箱相关字段
    packing_rule_id = fields.Many2one('wms.packing.rule', '装箱规则',
                                     help='用于此拣货单的装箱规则')
    suggested_boxes_count = fields.Integer('建议箱数', readonly=True,
                                          help='根据装箱规则计算的建议箱数')
    packing_efficiency = fields.Float('装箱效率(%)', readonly=True,
                                     help='实际装箱效率')
    packing_instructions = fields.Text('装箱说明', readonly=True,
                                      help='系统生成的装箱说明')