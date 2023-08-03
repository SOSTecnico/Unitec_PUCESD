# -*- coding: utf-8 -*-
import random

from odoo.addons.portal.controllers.portal import CustomerPortal, pager
from odoo import http
from odoo.http import request

from datetime import datetime, timedelta
import itertools


class Racetime(http.Controller):
    @http.route('/solicitud-permiso', auth='user', website=True)
    def index(self, **kw):
        tipos_permiso = request.env["racetime.tipos_permiso"].search([])
        return request.render('racetime.solicitud_permiso_template', {
            'user': request.env.user,
            'tipos_permiso': tipos_permiso
        })

    @http.route('/agendar-permiso', auth='user', method='POST', website=True)
    def agendar_permiso(self, **data):
        jefe_inmediato = request.env["hr.employee"].sudo().search([("work_email", '=', data['email_jefe'])])

        aprobado_por = [(4, jefe_inmediato.id)] if jefe_inmediato else False

        res = request.env["racetime.permisos"].sudo().create({
            'estado': 'pendiente',
            'empleado_id': request.env.user.employee_id.id,
            'aprobado_por_id': aprobado_por,
            'desde_fecha': data['fecha_inicio'],
            'hasta_fecha': data['fecha_fin'],
            'desde_hora': self.string_to_time(data["hora_inicio"]),
            'hasta_hora': self.string_to_time(data["hora_fin"]),
            'tipo_permiso_id': int(data['tipo_permiso_id']),
            'todo_el_dia': True if 'todo_el_dia' in data else False,
            'descripcion': data['descripcion']
        })

        template_id = request.env.ref("racetime.solicitud_permiso_email_template").id
        request.env["mail.template"].browse(template_id).send_mail(res.id, force_send=True)

        return self.solicitud_registrada()

    def string_to_time(self, string_time):
        if not string_time:
            string_time = "00:00"
        h, m = string_time.split(":")
        return timedelta(hours=int(h), minutes=int(m)).total_seconds() / 60 / 60

    @http.route('/mis-permisos', auth='user', website=True)
    def lista_de_permisos(self):
        permisos = request.env["racetime.permisos"].sudo().search(
            [("empleado_id", "=", request.env.user.employee_id.id)], order="desde_fecha desc")

        return request.render("racetime.lista_permisos_template", {"permisos": permisos, 'page_name': 'mis-permisos'})

    @http.route("/solicitud-registrada", auth="user", website=True)
    def solicitud_registrada(self):
        return request.render("racetime.solicitud_permiso_registrada_template")

    # Marcaciones
    @http.route(['/mis-marcaciones', '/mis-marcaciones/page/<int:page>'], auth='user', website=True)
    def marcaciones(self, page=1, sortby='fecha', search='', search_in='all', **kw):
        obj_m = request.env["racetime.detalle_marcacion"].sudo()
        total = obj_m.search_count([("empleado_id", "=", request.env.user.employee_id.id)])

        page_detail = pager(url='/mis-marcaciones',
                            total=total,
                            page=page,
                            url_args={'sortby': sortby, 'search_in': search_in, 'search': search},
                            step=15)

        sorted_list = {
            'fecha': {
                'label': 'Fecha',
                'order': 'fecha_hora desc'
            },
        }

        search_list = {
            'all': {'label': 'Todo', 'input': 'all', 'domain': [("empleado_id", "=", request.env.user.employee_id.id)]},
            'fecha_hora': {'label': 'Fecha', 'input': 'fecha_hora',
                           'domain': [("empleado_id", "=", request.env.user.employee_id.id),
                                      ('fecha_hora', '>=', search), ('fecha_hora', '<=', search)]}
        }

        search_domain = search_list[search_in]['domain']

        # default_order_by = sorted_list[sortby]['order']

        marcaciones = obj_m.search(search_domain, order='fecha_hora desc', limit=15, offset=page_detail['offset'])

        marc = []

        for m in marcaciones:
            marc.append({
                'fecha': m.fecha_hora.strftime('%Y-%m-%d'),
                'hora': (m.fecha_hora - timedelta(hours=5)).strftime("%H:%M:%S")
            })

        values = {
            'marcaciones': marc,
            'page_name': 'mis-marcaciones',
            'pager': page_detail,
            'sortby': sortby,
            # 'searchbar_sortings': sorted_list,
            'search': search,
            'searchbar_inputs': search_list,
            'search_in': search_in
        }
        return request.render("racetime.lista_marcaciones_template", values)

    @http.route("/asistencia-virtual", auth="user", website=True, methods=['GET', 'POST'])
    def formulario_asistencia_virtual(self, **data):
        if data:
            print(data)
            hora_inicio = datetime.strptime(f"{data['fecha']} {data['hora_inicio']}", "%Y-%m-%d %H:%M")
            hora_fin = datetime.strptime(f"{data['fecha']} {data['hora_fin']}", "%Y-%m-%d %H:%M")
            request.env['racetime.asistencia_virtual'].sudo().create({
                'fecha': data['fecha'],
                'correo': data['email'],
                'nombres': data['nombres'],
                'apellidos': data['apellidos'],
                'actividad': data['tipo_actividad'],
                'programa': data['programa'],
                'carrera_id': data['carrera'],
                'asignatura_id': data['asignatura'],
                'nivel': data['nivel'],
                'paralelo': data['paralelo'],
                'inquietud': True if data['inquietud'] == 'on' else False,
                'problemas_tecnicos': True if data['problemas'] == 'on' else False,
                'problemas_tecnicos_desc': data['descripcion_problemas'],
                'espacios_dialogo': True if data['espacios_dialogo'] == 'on' else False,
                'motivacion_asignatura': True if data['motivacion'] == 'on' else False,
                'aportes_clase': data['aportes_clase'],
                'actividades_academicas': True if data['actividades'] == 'on' else False,
                'actividades_academicas_detalle': data['actividades_detalle'],
                # 'novedades_estudiantes': data['fecha'],
                # 'sugerencias': data['fecha'],
                'hora_inicio': hora_inicio,
                'hora_fin': hora_fin,
            })

            return request.render('racetime.portal_registro_asistencia_existoso')
        carreras = request.env['estudiantes.carreras'].sudo().search(
            [('parent_id', '!=', False), ('name', '!=', 'MAESTRÍAS'), ('name', '!=', 'ESPECIALIDADES')])

        asignaturas = request.env['racetime.asignaturas'].sudo().search([])

        return request.render("racetime.portal_formulario_asistencia_virtual", {
            'carreras': carreras,
            'asignaturas': asignaturas,
            'user': request.env.user
        })

        # API

    @http.route('/racetime/api/marcaciones', auth='user', type='json')
    def api_marcaciones(self, **data):
        fecha_inicio = data['dates']['startDate']
        fecha_fin = data['dates']['endDate']
        empleado_code = request.env.user.employee_id.emp_code
        sql = f"""select punch_time, emp_code, id 
                    from iclock_transaction 
                    where emp_code = {empleado_code}
                    AND (convert(DATE,punch_time,105) >= '{fecha_inicio}' and convert(DATE,punch_time,105) <= '{fecha_fin}')
                    ORDER BY punch_time DESC
                    """
        result = request.env['racetime.detalle_marcacion'].conexionBiotime(sql)

        key_func = lambda self: self['punch_time'].strftime('%Y-%m-%d')
        marcaciones_agrupadas = []
        for key, group in itertools.groupby(result, key_func):
            marcaciones_agrupadas.append({
                'fecha': key,
                'records': list(group)[::-1]
            })

        return marcaciones_agrupadas

    @http.route('/api/racetime/actualizar-marcacion', auth='user', type='json')
    def api_actualizar_marcacion(self, **data):
        id_marcacion = data['id_marcacion']
        fecha, hora = data['datetime'].split("T")

        fecha_hora = datetime.strptime(f"{fecha} {hora}", f"%Y-%m-%d %H:%M:%S")
        fecha_hora = fecha_hora + timedelta(seconds=random.randint(0, 59))

        sql = f"""UPDATE iclock_transaction SET punch_time = '{fecha_hora}' where id = {id_marcacion};"""

        request.env['racetime.detalle_marcacion'].execute_sql_server(sql)

        marcacion = request.env['racetime.detalle_marcacion'].search([('id_marcacion', '=', id_marcacion)])
        marcacion.update({
            'fecha_hora': fecha_hora + timedelta(hours=5)
        })

        return {
            'msg': 'Ok'
        }

    def _get_config_sql_server(self):
        return request.env['racetime.detalle_marcacion'].obtener_parametros_conexion_biotime()


class PermisosPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        user = request.env.user
        permisos = request.env['racetime.permisos'].sudo().search_count(
            [('empleado_id', '=', user.employee_id.id)])

        marcaciones = request.env['racetime.detalle_marcacion'].sudo().search_count(
            [('empleado_id', '=', user.employee_id.id)])

        values.update({
            'count_permisos': permisos,
            'count_marcaciones': marcaciones
        })

        return values
