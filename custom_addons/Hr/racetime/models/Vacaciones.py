from odoo import fields, models, api


class Vacaciones(models.Model):
    _name = 'racetime.vacaciones'
    _description = 'Vacaciones'
    _rec_name = 'empleado_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(related='empleado_id.name')
    empleado_id = fields.Many2one(comodel_name='hr.employee', string='Empleado', required=True)
    desde = fields.Date(string='Desde', required=True, tracking=True)
    hasta = fields.Date(string='Hasta', required=True, tracking=True)
    observacion = fields.Text(string="Observación", required=False, tracking=True)


