# -*- coding: utf-8 -*-
"""
 * Es la API para conectarse con Pagadito y realizar cobros de forma segura.
 *
 * LICENCIA: Éste código fuente es de uso libre. Su comercialización no está
 * permitida. Toda publicación o mención del mismo, debe ser referenciada a
 * su autor original Pagadito.com.
 *
 * @author      Pagadito.com <soporte@pagadito.com>
 * @copyright   Copyright (c) 2017, Pagadito.com
 * @version     PHP 1.5.1
 * @link        https://dev.pagadito.com/index.php?mod=docs&hac=apipg#php
"""
import json
import pycurl

from phpserialize import unserialize
from io import BytesIO
import urllib.parse
import xml.etree.ElementTree as ET
import werkzeug
from werkzeug import urls


class Pagadito:
    def __init__(self,uid,wsk):

        # Atributos
        self.format_return = ""
        self.allow_pending_payments = ""
        self.sandbox_mode = True
        self.uid = ""
        self.wsk = ""
        self.apipg = ""
        self.apipgsandbox = ""
        self.formatreturn = ""
        self.response = ""
        self.sandboxmode = ""
        self.opconnectkey = ""
        self.opexectranskey = ""
        self.opgetstatuskey = ""
        self.opgetexchangeratekey = ""
        self.details = []
        self.customparams = ""
        self.currency = ""
        self.allowpendingpayments = ""

        """ ** Constructor de la clase,el cual inicializa los valores por defecto.
                :param: uid El identificador del Pagadito Comercio.
                :param: wsk La clave de acceso.
                """
        self.uid = uid
        self.wsk = wsk
        self.__config()

    # ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** *Funciones Públicas
    def connect(self):
        """Conecta con Pagadito y autentica al Pagadito Comercio.
        :return bool
        """
        params = {
            'operation': self.op_connect_key,
            'uid': self.uid,
            'wsk': self.wsk,
            'format_return': self.format_return
        }
        self.response = self.__call(params)
        if self.get_rs_code() == "PG1001":
            return True

        else:
            return False

    def exec_trans(self,ern):
        """Solicita el registro de la transacción yredirecciona a la pantalla de cobros
        de Pagadito.En caso de error devuelve false.
        :param ern External Reference Number.Es un número único y obligatorio que 
        identifica una transacción,provisto por el Pagadito Comercio y se utiliza
        para rastrear las transacciones realizadas por éste. 
        :return bool 
        """
        if self.get_rs_code() == "PG1001":
            params = {
                'operation': self.op_exec_trans_key,
                'token': self.get_rs_value(),
                'ern': ern,
                'amount': self.__calc_amount(),
                'details': json.dumps(self.details),
                'custom_params': json.dumps(self.custom_params),
                'currency': self.currency,
                'format_return': self.format_return,
                'allow_pending_payments': self.allow_pending_payments
            }
            self.response = self.__call(params)
            if (self.get_rs_code() == "PG1002"):
                return True

            else:
                return False

        else:
            return False

    def get_status(self,token_trans):
        """ ***Solicita el estado de una transacción en base a su token.
            * :param string token_trans El identificador de la conexión a consultar.
            * :return bool
            * /"""
        if (self.get_rs_code() == "PG1001"):
            params = {
                'operation': self.op_get_status_key,
                'token': self.get_rs_value(),
                'token_trans': token_trans,
                'format_return': self.format_return,
            }
            self.response = self.__call(params)
            if self.get_rs_code() == "PG1003":
                return True

            else:
                return False

        else:
            return False

    def get_exchange_rate_gtq(self):
        """/ ***Devuelve la tasa de cambio del quetzal.
            * :return float
            * /
        """
        return self.__get_exchange_rate("GTQ")

    def get_exchange_rate_hnl(self):
        """/ ***Devuelve la tasa de cambio del lempira.
        * :return float
        * /"""

        return self.__get_exchange_rate("HNL")

    def get_exchange_rate_nio(self):
        """Devuelve la tasa de cambio del córdoba.
        * :return: float
        * """
        return self.__get_exchange_rate("NIO")

    def get_exchange_rate_crc(self):
        """Devuelve la tasa de cambio del colón costarricense.
        :return: Float
        """
        return self.__get_exchange_rate("CRC")

    def get_exchange_rate_pab(self):
        """Devuelve la tasa de cambio del balboa.
        :return float
        """

        return self.__get_exchange_rate("PAB")

    def get_exchange_rate_dop(self):
        """Devuelve la tasa de cambio del peso dominicano.

        :return float
        """
        return self.__get_exchange_rate("DOP")

    def add_detail(self,quantity,description,price,url_product=""):
        """Agrega un detalle a la orden de cobro, previo a su ejecución.
            :param quantity Define la cantidad del producto.
            :param description Define la descripción del producto.
            :param price Define el precio del producto en términos de dólares americanos(USD).
            :param url_product Define la url de referencia del producto.
        """
        self.details.append({
            "quantity": quantity,
            "description": description,
            "price": price,
            "url_product": url_product,
        })

    def set_custom_param(self,code,value):
        """/ ***Establece el valor que tomará el parámetro personalizado especificado
        * en la orden de cobro, previo a su ejecución.
        * :param code :type string Código del parámetro a enviar.
        * :param value :type string Define el valor que se asignará al parámetro.
        * / """
        self.custom_params[code] = value

    def enable_pending_payments(self):
        """Habilita la recepción de pagos preautorizados para la orden de cobro.
        """
        self.allow_pending_payments = "true"

    def get_rs_code(self):
        """Devuelve el código de la respuesta.
        :return :type string
        """
        return self.__return_attr_response("code")

    def get_rs_message(self):
        """
        Devuelve el mensaje de la respuesta.
        :return :type string"""

        return self.__return_attr_response("message")

    def get_rs_value(self):
        """Devuelve el valor de la respuesta.
        :return :type object
        """
        return self.__return_attr_response("value")

    def get_rs_datetime(self):
        """Devuelve la fecha y hora de la respuesta. 
        * :return :type string
        """
        return self.__return_attr_response("datetime")

    def get_rs_status(self):
        """/ **
        *Devuelve el estado de la transacción consultada,después de un get_status().
        * :return :type string
        * /"""
        return self.__return_attr_value("status")

    def get_rs_reference(self):
        """Devuelve la referencia de la transacción consultada,después de un get_status().
        :return :type string
        """
        return self.__return_attr_value("reference")

    def get_rs_date_trans(self):
        """Devuelve la fecha y hora de la transacción consultada,después de un get_status(). 
        :return :type string
        """
        return self.__return_attr_value("date_trans")

    # ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** *Funciones Públicas auxiliares

    def mode_sandbox_on(self):
        """Habilita el modo de pruebas SandBox.
        """
        self.sandbox_mode = True

    def change_format_json(self):
        """Cambia el formato de retorno a JSON."""
        self.format_return = "json"

    def change_format_xml(self):
        """Cambia el formato de retorno a XML."""
        self.format_return = "xml"

    def change_format_php(self):
        """Cambia el formato de retorno a PHP."""
        self.format_return = "php"

    def change_currency_usd(self):
        """Cambia la moneda a dólares americanos."""
        self.currency = "USD"

    def change_currency_gtq(self):
        """Cambia la moneda a quetzales."""
        self.currency = "GTQ"

    def change_currency_hnl(self):
        """Cambia la moneda a lempiras."""
        self.currency = "HNL"

    def change_currency_nio(self):
        """Cambia la moneda a córdobas."""
        self.currency = "NIO"

    def change_currency_crc(self):
        """Cambia la moneda a colones costarricenses."""
        self.currency = "CRC"

    def change_currency_pab(self):
        """Cambia la moneda a balboas."""
        self.currency = "PAB"

    def change_currency_dop(self):
        """Cambia la moneda a pesos dominicanos."""
        self.currency = "DOP"

    # ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** ** *Funciones Privadas

    def __config(self):
        """Establece los valores por defecto."""
        self.apipg = "https://comercios.pagadito.com/apipg/charges.php"
        self.apipg_sandbox = "https://sandbox.pagadito.com/comercios/apipg/charges.php"
        # Cambie self.format_return para definir el formato de respuesta que desee utilizar: json,php o xml
        self.format_return = "json"
        self.sandbox_mode = False
        self.op_connect_key = "f3f191ce3326905ff4403bb05b0de150"
        self.op_exec_trans_key = "41216f8caf94aaa598db137e36d4673e"
        self.op_get_status_key = "0b50820c65b0de71ce78f6221a5cf876"
        self.op_get_exchange_rate_key = "da6b597cfcd0daf129287758b3c73b76"
        self.details = []
        self.custom_params = []
        self.currency = "USD"
        self.allow_pending_payments = "false"

    def __return_attr_response(self,attr):
        """Devuelve el valor del atributo solicitado.
        :param attr Nombre del atributo de la respuesta.
        :return :type string
        """
        if isinstance(self.response, dict) and attr in self.response:
            return self.response[attr]
        else:
            return None

    def __return_attr_value(self, attr):
        """

        :type attr: str
        """
        if self.__return_attr_response:
            if self.format_return == "json":
                if isinstance(self.response, object) and attr in self.response:
                    return self.response[attr]
                else:
                    return None

            elif self.format_return == "php":
                if isinstance(self.response["value"], list) and attr in self.response:
                    return self.response[attr]

                else:
                    return None

            elif self.format_return == "xml":
                if isinstance(self.response, object) and attr in self.response:
                    return self.response[attr]
                else:
                    return None
        else:
            return None

    def __call(self, params):
        """/ ***Ejecuta una llamada a Pagadito y devuelve la respuesta.
            * :type params: str Variables y sus valores a enviarse en la llamada.
            * :return :type string
            
        """
        try:
            buffer = BytesIO()
            c = pycurl.Curl()
            if (self.sandbox_mode):
                c.setopt(c.URL,self.apipg_sandbox)
            else:
                c.setopt(c.URL,self.apipg)

            c.setopt(c.WRITEFUNCTION, buffer.write)
            c.setopt(pycurl.HEADER,0)
            #c.setopt(pycurl.RETURNTRANSFER,1)
            c.setopt(pycurl.POSTFIELDS,self.__format_post_vars(params))
            c.perform()
            c.close()

            response = buffer.getvalue().decode('UTF-8')
            return self.__decode_response(response)

        except Exception as e:
            return e

    def __format_post_vars(self, vars):
        """
        :type vars: object
        """
        formatted_vars = ""
        for key,value in vars.items():
            if type(value) == str:
                value = value.encode()
            else:
                value = str(value).encode()
            formatted_vars += key + '=' + urllib.parse.quote_plus(value) + '&'

        formatted_vars = formatted_vars.rstrip('&')
        return formatted_vars

    def __decode_response(self, response):
        """Devuelve un objeto con los datos de la respuesta de Pagadito.
        :param  response Cadena contenedora de la estructura a ser decodificada.
        :return :type object
        """
        if self.format_return == "php":
            return unserialize(response)
        elif self.format_return == "xml":
            return ET.fromstring(response)
        elif self.format_return == "json":
            return json.loads(response)
        else:
            return json.loads(response)

    def __calc_amount(self):
        """Devuelve la sumatoria de los productos entre cantidad y precio de todos
        los detalles de la transacción.
        :return float
        """
        amount = 0
        for detail in self.details:
            amount += detail["quantity"] * detail["price"]
            return amount

    def __get_exchange_rate(self, currency):
        """Devuelve la tasa de cambio de la moneda determinada.
        :param currency string Es la moneda de la cual se obtendrá su tasa de cambio.
        :return float
        """
        if ["PG1001", "PG1004"] in self.get_rs_code():
            params = dict(operation=self.op_get_exchange_rate_key,
                          token=self.get_rs_value(),
                          currency=currency,
                          format_return=self.format_return)

            previous_response = self.response
            self.response = self.__call(params)
            if self.get_rs_code() == "PG1004":
                exchage_rate = self.get_rs_value()
                self.response = previous_response
                return exchage_rate

            else:
                return 0

        else:
            return 0
