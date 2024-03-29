from odoo import fields, models, api


class Empleado(models.Model):
    _inherit = 'hr.employee'

    permisos_id = fields.One2many(comodel_name='racetime.permisos', inverse_name='empleado_id', string='Permisos',
                                  required=False)

    vacaciones_id = fields.One2many(comodel_name='racetime.vacaciones', inverse_name='empleado_id', string='Vacaciones',
                                    required=False)

    emp_code = fields.Integer(string='Código Empleado', required=False, help="Código de Biométrico")

    def actualizar_codigo_biotime(self):
        empleados = self.env['hr.employee'].search([('emp_code', '!=', 0)])
        for rec in empleados:
            marcaciones_en_bruto = self.env['racetime.detalle_marcacion'].search([('emp_code', '=', rec.emp_code)])

            marcaciones_en_bruto.update({
                'nombre_empleado': rec.name
            })
