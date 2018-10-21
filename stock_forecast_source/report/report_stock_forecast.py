# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools


class ReportStockForecat(models.Model):
    _name = 'report.stock.forecast'
    _description = 'Enhanced Stock Forecast'
    _auto = False

    date = fields.Date(string='Date')
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', related='product_id.product_tmpl_id', readonly=True)
    quantity = fields.Float(readonly=True)
    incoming_quantity = fields.Float(readonly=True)
    outgoing_quantity = fields.Float(readonly=True)
    location_id = fields.Many2one('stock.location', string='Location', readonly=True)
    categ_id = fields.Many2one('product.category', string='Category', readonly=True)
    source = fields.Char(string='Source', readonly=True)
    cumulative_quantity = fields.Float(string='Cumulative Quantity', readonly=True)

    # Borrowed sql from v8 stok_forecast_report module.
    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'report_stock_forecast')
        self._cr.execute("""CREATE or REPLACE VIEW report_stock_forecast AS (SELECT
            MIN(FINAL.id) AS id,
            FINAL.product_id AS product_id,
            FINAL.date AS date,
            sum(sum(FINAL.product_qty) + sum(FINAL.in_quantity) - SUM(FINAL.out_quantity)) OVER (PARTITION BY FINAL.product_id ORDER BY FINAL.date) AS cumulative_quantity,
            -- -- Alternative incoming quantity includes on hand adjustments.
            --sum(in_quantity) + sum(FINAL.product_qty) AS incoming_quantity,
            sum(FINAL.product_qty) AS quantity,
            sum(in_quantity) AS incoming_quantity,
            sum(out_quantity) AS outgoing_quantity,
            FINAL.location_id,
            categ.id AS categ_id,
            coalesce(po.name, raw_production.name, proc_group.name, move.name, 'On Hand Adjustments') as source
            FROM
            (SELECT
            MIN(id) AS id,
            MAIN.product_id AS product_id,
            MAIN.product_tmpl_id as product_tmpl_id,
            MAIN.location_id AS location_id,
            MAIN.date AS date,
            sum(MAIN.product_qty) AS product_qty,
            sum(MAIN.in_quantity) AS in_quantity,
            sum(MAIN.out_quantity) AS out_quantity
            FROM
            (SELECT
                MIN(sq.id) AS id,
                sq.product_id,
                product_product.product_tmpl_id,
                date_trunc(
                'day',
                to_date(to_char(CURRENT_DATE, 'YYYY/MM/DD'),
                'YYYY/MM/DD')) AS date,
                SUM(sq.qty) AS product_qty,
                0 AS in_quantity,
                0 AS out_quantity,
                sq.location_id
                FROM
                stock_quant AS sq
                LEFT JOIN
                product_product ON product_product.id = sq.product_id
                LEFT JOIN
                stock_location location_id ON sq.location_id = location_id.id
                WHERE
                location_id.usage = 'internal'
                GROUP BY date, sq.product_id, sq.location_id,
                     product_product.product_tmpl_id
                UNION ALL
                SELECT
                MIN(-sm.id) AS id,
                sm.product_id,
                product_product.product_tmpl_id,
                date_trunc(
                'day',
                to_date(to_char(sm.date_expected, 'YYYY/MM/DD'),
                'YYYY/MM/DD'))
                AS date,
                0 AS product_qty,
                SUM(sm.product_qty) AS in_quantity,
                0 AS out_quantity,
                dest_location.id AS location_id
                FROM
                   stock_move AS sm
                LEFT JOIN
                   product_product ON product_product.id = sm.product_id
                LEFT JOIN
                stock_location dest_location
                ON sm.location_dest_id = dest_location.id
                LEFT JOIN
                stock_location source_location
                ON sm.location_id = source_location.id
                WHERE
                sm.state IN ('confirmed','assigned','waiting') AND
                source_location.usage != 'internal' AND
                dest_location.usage = 'internal'
                GROUP BY sm.date_expected, sm.product_id, dest_location.id,
                     product_product.product_tmpl_id
                UNION ALL
                SELECT
                MIN(-sm.id) AS id,
                sm.product_id,
                product_product.product_tmpl_id,
                date_trunc(
                    'day',
                    to_date(to_char(sm.date_expected, 'YYYY/MM/DD'),
                    'YYYY/MM/DD'))
                AS date,
                0 AS product_qty,
                0 AS in_quantity,
                SUM(sm.product_qty) AS out_quantity,
                source_location.id AS location_id
                FROM
                   stock_move AS sm
                LEFT JOIN
                   product_product ON product_product.id = sm.product_id
                LEFT JOIN
                   stock_location source_location
                   ON sm.location_id = source_location.id
                LEFT JOIN
                   stock_location dest_location
                   ON sm.location_dest_id = dest_location.id
                WHERE
                sm.state IN ('confirmed','assigned','waiting') AND
                source_location.usage = 'internal' AND
                dest_location.usage != 'internal'
                GROUP BY sm.date_expected, sm.product_id, source_location.id,
                     product_product.product_tmpl_id)
             AS MAIN	     
            GROUP BY MAIN.product_id, MAIN.date, MAIN.location_id, MAIN.product_tmpl_id
            ) AS FINAL
        JOIN product_template tmpl ON FINAL.product_tmpl_id = tmpl.id
        JOIN product_category categ ON tmpl.categ_id = categ.id
        LEFT JOIN stock_move move ON move.id = FINAL.id * -1 AND FINAL.id < 0
        LEFT JOIN
           purchase_order_line po_line
           ON move.purchase_line_id = po_line.id
        LEFT JOIN
           purchase_order po
           ON po_line.order_id = po.id
        LEFT JOIN
           mrp_production raw_production
           ON move.raw_material_production_id = raw_production.id
        LEFT JOIN
           procurement_order proc
           ON move.procurement_id = proc.id
        LEFT JOIN
           procurement_group proc_group
           ON proc.group_id = proc_group.id
          
        GROUP BY FINAL.product_id, FINAL.date, FINAL.location_id, categ.id, proc_group.name, proc.id, po.name, raw_production.name, move.name, move.id
        ORDER BY FINAL.date)""")
