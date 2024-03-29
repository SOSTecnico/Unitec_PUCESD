from urllib.request import urlopen

import pyodbc
import mysql.connector
import requests
import paramiko
import time

import json
from datetime import date
import ssl

from odoo import fields, models, api
from odoo.exceptions import ValidationError


class Carreras(models.Model):
    _name = 'estudiantes.carreras'
    _description = 'Carreras'

    name = fields.Char(string='Carrera', required=True)
    parent_id = fields.Many2one(comodel_name='estudiantes.carreras', string='Dependencia', required=False)


class Estudiantes(models.Model):
    _name = 'estudiantes.estudiantes'
    _description = 'Estudiante'
    _inherit = ['mail.thread']

    _sql_constraints = [
        ('correo', 'unique(correo)', 'Ya existe un estudiante ingresado con esa Correo!')
    ]

    pidm = fields.Char(
        string='PIDM',
        required=False)

    id_banner = fields.Char(
        string='ID BANNER',
        required=False)

    codigosap = fields.Char(
        string='CODSAP',
        required=False)

    puceclaim = fields.Char(
        string='PUCECLAIM',
        required=False)

    nombredeusuario = fields.Char(
        string='NOMBRE DE USUARIO',
        required=False)

    pin = fields.Char(
        string='COMTRASEÑA',
        required=False)

    name = fields.Char(compute='_compute_name', store=True, string="Nombre Completo")

    nombres = fields.Char(string='Nombres', required=True, tracking=True)
    apellidos = fields.Char(string='Apellidos', required=True, tracking=True)
    cedula = fields.Char(string='Cédula'
                         , tracking=True)
    correo = fields.Char(string='Correo', required=False, tracking=True)
    celular = fields.Char(string='Celular', required=False, tracking=True)
    carrera_id = fields.Many2one(comodel_name='estudiantes.carreras', string='Carrera', tracking=True,
                                 domain="[('parent_id','!=',False),('name','!=','MAESTRÍAS'),('name','!=','ESPECIALIDADES')]")
    active = fields.Boolean(string='Active', required=False, default=True)
    estado_portas = fields.Boolean(string='Estado Portas', required=False, default=True, tracking=True)

    @api.depends('nombres', 'apellidos')
    def _compute_name(self):
        for estudiante in self:
            estudiante.name = f"{estudiante.nombres} {estudiante.apellidos}"

    @api.onchange("estado_portas")
    def estado_estudiante(self):
        estado = 0 if self.estado_portas else 1

        sql = f"UPDATE mdl_pucesd_portas_2021_2021.mdl_user SET suspended = '{estado}' WHERE email = '{self.correo}';"
        self.conexionPortas(sql)

    def obtener_parametros_conexion_portas(self):

        configuracion = self.env['estudiantes.config'].sudo().search_read([('key', 'like', 'portas')],
                                                                          fields=['value'])
        portas_host, portas_port, portas_db_name, portas_db_user, portas_db_password = configuracion
        return portas_host["value"], portas_port["value"], portas_db_name["value"], portas_db_user["value"], \
        portas_db_password["value"]

    def conexionPortas(self, sql):
        try:
            config = self.obtener_parametros_conexion_portas()

            miConexion = mysql.connector.connect(host=config[0], user=config[3], passwd=config[4], db=config[2])
            result = miConexion.cursor()
            result.execute(sql)

            values = []

            for row in result:
                values.append(dict((column[0], row[index]) for index, column in enumerate(result.description)))

            miConexion.commit()
            miConexion.close()

            return values

        except Exception as ex:
            raise ValidationError(f"Ocurrió un error al conectarse a la Base de Datos: {ex}")

    def enviarCorreo(self):
        template = self.env.ref("estudiantes.notificacion_credenciales_portas_mt").id
        for rec in self:
            if rec.correo:
                self.env["mail.template"].sudo().browse(template).send_mail(rec.id, force_send=True)

    @api.model
    def sincronizar_estudiantes_Portas(self):
        try:
            values = []
            sql = """SELECT DISTINCT user.id as ID,user.USERNAME as USUARIO, user.SUSPENDED as ESTADO, user.firstname AS NOMBRES, user.lastname AS APELLIDOS, user.email AS CORREO, user.idnumber AS CEDULA, user.msn AS IDBANNER  
            FROM mdl_pucesd_portas_2021_2021.mdl_user as user 
            INNER JOIN mdl_pucesd_portas_2021_2021.mdl_role_assignments as rol ON (user.id = rol.userid) where rol.roleid='5';"""
            result_portas = self.conexionPortas(sql)
            correos = self.sudo().search([]).mapped('correo')

            for row in result_portas:
                if row['CORREO'] not in correos:
                    values.append({
                        'nombres': row['NOMBRES'],
                        'apellidos': row['APELLIDOS'],
                        'cedula': row['CEDULA'],
                        'correo': row['CORREO'],
                        'estado_portas': True if row['ESTADO'] == 0 else False

                    })
            self.create(values)
        except Exception as e:
            raise ValidationError(f"Ocurrió un error: {e}")

    def actualizarBanner(self):
        HOST='192.168.250.23'
        USER='Administrator'

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect('192.168.250.23',username='Administrator', password='As1redes')

        gmail="emvillareall@pucesd.edu.ec"
        pass_banner='123456789'

        std_in, std_out, std_err = client.exec_command(f"python change_password.py {gmail} {pass_banner}")
        time.sleep(1)
        resultado=std_out.read().decode()

        #print(resultado)



class Sincronizacion(models.TransientModel):
    _name = 'estudiantes.sincronizacion'
    _description = 'Sincronizacion'

    def sincronizar_portas(self):
        self.env["estudiantes.estudiantes"].sincronizar_estudiantes_Portas()
