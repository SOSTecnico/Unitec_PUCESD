from datetime import datetime, timedelta

from psycopg2 import Error

from odoo import fields, models, api
import pyodbc

from odoo.exceptions import ValidationError


class DetalleMarcacion(models.Model):
    _name = 'racetime.detalle_marcacion'
    _description = 'Detalle Marcacion'

    name = fields.Char()
    id_marcacion = fields.Integer(string='ID Marcación', required=False)
    fecha_hora = fields.Datetime(string='Fecha y Hora', required=False)
    emp_code = fields.Integer(string='Código Empleado', required=False)
    empleado_id = fields.Many2one(comodel_name='hr.employee', string='Empleado', required=False,
                                  compute='_establecer_empleado', store=True)

    nombre_empleado = fields.Char(string='Nombre Empleado', required=False)

    @api.depends('emp_code')
    def _establecer_empleado(self):
        empleados = self.env['hr.employee'].search([])
        for rec in self:
            empleado = empleados.filtered_domain([('emp_code', '=', rec.emp_code)])
            rec.empleado_id = empleado
            rec.nombre_empleado = empleado.name

    @api.model
    def obtener_marcaciones(self, sql=False):
        try:
            empleados = self.env['hr.employee'].sudo().search([('emp_code', '!=', 0)])
            if not sql:
                self.unlink()
                sql = """SELECT * from iclock_transaction it;"""

            result = self.conexionBiotime(sql)

            marcaciones = self.sudo().search([]).mapped('id_marcacion')

            values = []

            for row in result:
                if row['id'] not in marcaciones:
                    empleado = empleados.filtered_domain([('emp_code', '=', row['emp_code'])])
                    values.append({
                        'fecha_hora': row['punch_time'] + timedelta(hours=5),
                        'id_marcacion': row['id'],
                        'emp_code': row['emp_code'],
                        'nombre_empleado': empleado.name
                    })
            self.create(values)
            print("ObteniendoMarcaciones")
        except Exception as e:
            raise ValidationError(f"Ocurrió un error: {e}")

    @api.model
    def obtener_marcaciones_diarias(self):
        # Para pruebas
        # fecha = '2023-01-13'
        # query = f"""select * from iclock_transaction where convert(DATE,punch_time,105) = '{fecha}'"""
        query = f"""select * from iclock_transaction where convert(DATE,punch_time,105) = '{datetime.now().strftime('%Y-%m-%d')}'"""
        self.obtener_marcaciones(sql=query)

    def obtener_parametros_conexion_biotime(self):

        configuracion = self.env['racetime.config'].sudo().search_read([('key', 'like', 'biotime')],
                                                                       fields=['key', 'value'])
        config = {}
        for c in configuracion:
            if c['key'] == 'biotime_host':
                config['host'] = c['value']
            if c['key'] == 'biotime_port':
                config['port'] = c['value']
            if c['key'] == 'biotime_db_name':
                config['db_name'] = c['value']
            if c['key'] == 'biotime_db_user':
                config['db_user'] = c['value']
            if c['key'] == 'biotime_db_password':
                config['db_password'] = c['value']
        return config

    def conexionBiotime(self, sql):
        try:
            config = self.obtener_parametros_conexion_biotime()
            conexion = pyodbc.connect(
                'DRIVER={ODBC Driver 17 for SQL server}; SERVER=' + config['host'] +
                ',' + config['port'] +
                ';DATABASE=' + config['db_name'] +
                ';UID=' + config['db_user'] +
                ';PWD=' + config['db_password'])

            cursor = conexion.cursor()
            cursor.execute(sql)
            result = []
            for row in cursor:
                result.append(dict((column[0], row[index]) for index, column in enumerate(cursor.description)))

            conexion.commit()
            cursor.close()
            conexion.close()
            return result

        except Error as ex:
            raise ValidationError(f"Ocurrió un error al conectarse a la Base de Datos: {ex}")

    def execute_sql_server(self, sql):
        try:
            config = self.obtener_parametros_conexion_biotime()
            conexion = pyodbc.connect(
                'DRIVER={ODBC Driver 17 for SQL server}; SERVER=' + config['host'] +
                ',' + config['port'] +
                ';DATABASE=' + config['db_name'] +
                ';UID=' + config['db_user'] +
                ';PWD=' + config['db_password'])

            cursor = conexion.cursor()
            cursor.execute(sql)

            conexion.commit()
            cursor.close()
            conexion.close()

        except Error as ex:
            raise ValidationError(f"Ocurrió un error al conectarse a la Base de Datos: {ex}")


# clase para obtener listado de marcaciones de empleados.
class ObtenerMarcaciones(models.TransientModel):
    _name = 'racetime.obtener_marcacion'
    _description = 'Obtener Marcaciones'

    name = fields.Char()

    # campos solicitados para generar el listado.
    empleados_id = fields.Many2many(comodel_name='hr.employee', string='Empleados', required=True)
    fecha_inicio = fields.Datetime(string='Fecha Inicial', required=True)
    fecha_final = fields.Datetime(string='Fecha Final', required=False)


    # función para hacer una consulta a la base de datos, para generar listado de marcaciones.
    def generar_listado(self):
        # cambio de zona horario de los campos, a la zona actual que se esta.
        self.fecha_inicio = self.fecha_inicio + timedelta(hours=-5)
        self.fecha_final = self.fecha_final + timedelta(hours=-5)

        ids = str(self.empleados_id.mapped('emp_code')).replace('[', '').replace(']', '')


        # consulta a la base de datos, de los tiempos de marcaciones e ids de empleados.
        query = f"""select * from iclock_transaction
                    where punch_time 
                    between '{self.fecha_inicio.strftime("%Y-%m-%d %H:%M:%S")}'
                    and '{self.fecha_final.strftime("%Y-%m-%d %H:%M:%S")}' and emp_code in ({ids})"""
        result = self.env["racetime.detalle_marcacion"].obtener_marcaciones(sql=query)
