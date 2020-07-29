# -*- coding: utf-8 -*-
from urllib.parse import urlparse
import werkzeug

from odoo import http,SUPERUSER_ID
from odoo.http import request
import logging
from ..clases import Pagadito

_logger = logging.getLogger(__name__)


class PagaditoController(http.Controller):
    _init_url = '/payment/pagadito/init'
    _result_url = '/payment/pagadito/result'
    _end_url = '/payment/pagadito/end'
    _confirmation = '/shop/pagadito/confirmation'
    _error = '/shop/pagadito/cancelar'

    configuration = None
    webpay = None

    # Llamada a pagina init (Permite inicializar una transaccion en Webpay)
    @http.route([
        _init_url
    ],type='http',auth='none',methods=['POST'],csrf=False)
    def pagadito_form_feedback(self,**post):

        uid = "dab5804129692ffb0d5969b6aaf1867d"
        wsk = "dc3a65b4566b98f86129745dba34e664"
        tx_ids_list = [tx for tx in request.session.get("__payment_tx_ids__",[])]
        tx = request.env['payment.transaction'].sudo().search([('id','in',tx_ids_list)])
        acquirer = tx.mapped('acquirer_id')
        if acquirer.pagadito_uid:
            uid = acquirer.pagadito_uid
        if acquirer.pagadito_wsk:
            wsk = acquirer.pagadito_wsk

        pagadito = Pagadito.Pagadito(uid,wsk)
        if post.get("environment") and post.get("environment") == 'test':
            pagadito.mode_sandbox_on()
        reference = post.get('reference')
        # if reference:
        #    tx = request.env['payment.transaction'].search([('reference', '=', reference)])

        baseurl = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        mensaje_error = ""

        if (pagadito.connect()):
            tx.pagadito_txn_token = pagadito.get_rs_value()

            for so in tx.sale_order_ids:
                pagadito.add_detail(1,so.name,so.amount_total,baseurl + "/my/orders/" + str(so.id))

            if not pagadito.exec_trans(post.get('reference')):
                err_code = pagadito.get_rs_code()

                if err_code == "PG2001":
                    # Incomplete data
                    tx.sudo()._set_transaction_error("No estan completados todos los datos.")

                elif err_code == "PG3002":
                    # Error
                    tx.sudo()._set_transaction_error("Hubo un error desconocido")

                elif err_code == "PG3003":
                    # Unregistered transaction
                    tx.sudo()._set_transaction_error("Esta transaccion no esta registrada")

                elif err_code == "PG3004":
                    # Match error
                    tx.sudo()._set_transaction_error("No podemos calzar esta transaccion")

                elif err_code == "PG3005":
                    # Disabled connection
                    tx.sudo()._set_transaction_error("Conexion deshabilitada")

        else:
            err_code = pagadito.get_rs_code()

            if err_code == "PG3001":
                # Incomplete data
                tx.sudo()._set_transaction_error("No estan completados todos los datos.")

            elif err_code == "PG3002":
                # Error
                tx.sudo()._set_transaction_error("Hubo un error desconocido")

            elif err_code == "PG3003":
                # Unregistered transaction
                tx.sudo()._set_transaction_error("Esta transaccion no esta registrada")

            elif err_code == "PG3004":
                # Match error
                tx.sudo()._set_transaction_error("No podemos calzar esta transaccion")

            elif err_code == "PG3005":
                # Disabled connection
                tx.sudo()._set_transaction_error("Conexion deshabilitada")

            elif err_code == "PG3006":
                # Exceeded
                tx.sudo()._set_transaction_error("Limite excedido")
        return werkzeug.utils.redirect(pagadito.get_rs_value())
        #return werkzeug.utils.redirect('/payment/process')

    # Llamada a pagina result (Obtiene el detalle de la transacción)
    @http.route([
        _result_url
    ],type='http',auth='none',methods=['GET'],csrf=False)
    def pagadito_result_feedback(self,**vals):

        acquirer = request.env["payment.acquirer"].sudo().search([('provider','=','pagadito')])

        uid = "dab5804129692ffb0d5969b6aaf1867d"
        wsk = "dc3a65b4566b98f86129745dba34e664"
        a = ""
        res=False

        if acquirer.pagadito_uid:
            uid = acquirer.pagadito_uid
        if acquirer.pagadito_wsk:
            wsk = acquirer.pagadito_wsk

        tx = request.env['payment.transaction'].search([('pagadito_txn_token','=',vals.get('token'))])

        pagadito = Pagadito.Pagadito(uid,wsk)
        if acquirer.state == 'test':
            pagadito.mode_sandbox_on()

        if pagadito.connect():

            if pagadito.get_status(vals.get('token')):

                val = pagadito.get_rs_value()

                status = val['status']
                vals.update(val)
                if status == "COMPLETED":
                    # tratamiento para una compra exitosa
                    res = tx.sudo().form_feedback(vals,'pagadito')

                elif status == "REGISTERED":
                    # tratamiento para una copra en proceso
                    res = tx.sudo().form_feedback(vals,'pagadito')

                elif status == "VERIFYING":
                    """La transacción ha sido procesada en Pagadito, pero ha quedado en verificación.
                         * En este punto el cobro ha quedado en validación administrativa.
                         * Posteriormente, la transacción puede marcarse como válida o denegada;
                         * por lo que se debe monitorear mediante esta función hasta que su estado cambie a COMPLETED o REVOKED."""

                    tx.sudo()._set_transaction_error(
                        "La transacción ha sido procesada en Pagadito, pero ha quedado en verificación.")


                elif status == "REVOKED":
                    """La transacción en estado VERIFYING ha sido denegada por Pagadito.
                         * En este punto el cobro ya ha sido cancelado."""
                    tx.sudo()._set_transaction_error("la transaccion ha sido denegada por Pagadito")

                elif status == "FAILED":
                    """Tratamiento para una transacción fallida."""
                    tx.sudo()._set_transaction_error("Transaccion fallida")

                else:
                    """Por ser un ejemplo, se muestra un mensaje
                         * de error fijo."""
                    tx.sudo()._set_transaction_error("Hubo un error desconocido")
            else:
                """* En caso de fallar la petición, verificamos el error devuelto.
                * Debido a que la API nos puede devolver diversos mensajes de
                * respuesta, validamos el tipo de mensaje que nos devuelve."""
                code = pagadito.get_rs_code()
                if code == "PG2001":
                    # Incomplete data
                    tx.sudo()._set_transaction_error("Informacion incompleta")
                elif code == "PG3002":
                    # Error
                    tx.sudo()._set_transaction_error("Hubo un error desconocido")
                elif code == "PG3003":
                    # Unregistered transaction
                    tx.sudo()._set_transaction_error("Transaccion no registrada")


        else:
            """* En caso de fallar la conexión, verificamos el error devuelto.
            * Debido a que la API nos puede devolver diversos mensajes de
            * respuesta, validamos el tipo de mensaje que nos devuelve.
            """
            code = pagadito.get_rs_code()
            if code == "PG2001":
                # Incomplete data
                tx.sudo()._set_transaction_error("Informacion incompleta")

            elif code == "PG3001":
                # Problem connection
                tx.sudo()._set_transaction_error("Problemas de conexion")

            elif code == "PG3002":
                # Error
                tx.sudo()._set_transaction_error("Error desconocido")

            elif code == "PG3003":
                # Unregistered transaction
                tx.sudo()._set_transaction_error("transaccion no registrada")

            elif code == "PG3005":
                # Disabled connection
                tx.sudo()._set_transaction_error("Problemas de conexion")
            elif code == "PG3006":
                # Exceeded
                tx.sudo()._set_transaction_error("Limite exedido")

            else:
                """/*
                 * Aqui se muestra el código y mensaje de la respuesta del WSPG
                 */
                $msgPrincipal = "Respuesta de Pagadito API";
                $msgSecundario = "
                        COD: " . $Pagadito->get_rs_code() . "<br />
                        MSG: " . $Pagadito->get_rs_message() . "<br /><br />";"""
                tx.sudo()._set_transaction_error("Hubo un error desconocido en la transaccion")

        return werkzeug.utils.redirect('/payment/process')

    @http.route([
        _end_url
    ],type='http',auth='none',methods=['POST'],csrf=False)
    def pagadito_end_feedback(self,**post):
        pass

    @http.route([
        _confirmation
    ],type='http',auth="public",csrf=False,website=True)
    def payment_confirmation(self,**post):
        pass

    @http.route([
        _error
    ],type='http',auth='public',csrf=False,website=True)
    def payment_error(self,**post):
        pass
