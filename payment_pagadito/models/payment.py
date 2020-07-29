# coding: utf-8

from odoo import models, fields, api, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
import logging
import pytz
import dateutil.parser
from datetime import date
from datetime import datetime
from dateutil.parser import parse


_logger = logging.getLogger(__name__)

class AcquirerPagadito(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('pagadito', 'Pagadito')])
    pagadito_uid = fields.Char("Pagadito UID")
    pagadito_wsk = fields.Char("Pagadito WSK")

   # @api.multi
    def pagadito_get_form_action_url(self):
        return '/payment/pagadito/init'


   # @api.multi
    def pagadito_form_generate_values(self,values):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        pagadito_tx_values = dict(values)
        pagadito_tx_values.update({
            'cmd': '_xclick',
            #'business': self.pagadito_email_account,
            'uid': self.pagadito_uid,
            'wsk': self.pagadito_wsk,
            'item_name': '%s: %s' % (self.company_id.name,values['reference']),
            'item_number': values['reference'],
            'amount': values['amount'],
            'currency_code': values['currency'] and values['currency'].name or '',
            'address1': values.get('partner_address'),
            'city': values.get('partner_city'),
            'country': values.get('partner_country') and values.get('partner_country').code or '',
            'state': values.get('partner_state') and (
            values.get('partner_state').code or values.get('partner_state').name) or '',
            'email': values.get('partner_email'),
            'zip_code': values.get('partner_zip'),
            'first_name': values.get('partner_first_name'),
            'last_name': values.get('partner_last_name'),
            'return_url':values.get('return_url'),
            'reference': values.get('reference'),
            'environment': self.state

            #'pagadito_return': urls.url_join(base_url,PagaditoController._return_url),
            #'notify_url': urls.url_join(base_url,PagaditoController._notify_url),
            #'cancel_return': urls.url_join(base_url,PagaditoController._cancel_url),
            #'handling': '%.2f' % pagadito_tx_values.pop('fees',0.0) if self.fees_active else False,
            #'custom': json.dumps({'return_url': '%s' % pagadito_tx_values.pop('return_url')}) if pagadito_tx_values.get(
            #    'return_url') else False,
        })
        return pagadito_tx_values


class TxPagadito(models.Model):
    _inherit = 'payment.transaction'

    pagadito_txn_token = fields.Char('Pagadito token')


   # @api.multi
    def _pagadito_form_validate(self, data):
        status = data.get('status')
        res = {
            'acquirer_reference': data.get('reference'),
        }
        if status in ['COMPLETED', 'REGISTERED']:
            _logger.info('Validated Pagadito payment for tx %s: set as done' % (self.reference))
            try:
                # dateutil and pytz don't recognize abbreviations PDT/PST
                tzinfos = {
                    'PST': -8 * 3600,
                    'PDT': -7 * 3600,
                }
                #date = dateutil.parser.parse(data.get('date_trans'), tzinfos=tzinfos).astimezone(pytz.utc)
                date = fields.Datetime.now()
            except:
                date = fields.Datetime.now()
            res.update(date=date)
            self._set_transaction_done()
            return self.write(res)
        elif status in ['Pending', 'Expired']:
            _logger.info('Received notification for Paypal payment %s: set as pending' % (self.reference))
            res.update(state_message=data.get('pending_reason', ''))
            self._set_transaction_pending()
            return self.write(res)
        else:
            error = 'Received unrecognized status for Paypal payment %s: %s, set as error' % (self.reference, status)
            _logger.info(error)
            res.update(state_message=error)
            self._set_transaction_cancel()
            return self.write(res)

    @api.model
    def _pagadito_form_get_tx_from_data(self, data):
        if not data.get('token'):
            error_msg = _('Pagadito: received data with missing token')
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use txn_id ?
        txs = self.env['payment.transaction'].search([('pagadito_txn_token','=',data.get('token'))])
        if not txs or len(txs) > 1:
            error_msg = 'Pagadito: received data for reference %s' % (txs.reference)
            if not txs:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return txs[0]