import json
import logging
from odoo import http
from odoo.http import request
from werkzeug.wrappers import Response
import hashlib
import xml.etree.ElementTree as ET

_logger = logging.getLogger(__name__)


class WeChatController(http.Controller):
    @http.route('/wms/wechat/webhook', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def wechat_webhook(self, **kwargs):
        """
        Handle incoming webhook requests from WeChat
        This endpoint receives messages and events from WeChat Mini Program
        """
        if request.httprequest.method == 'GET':
            # This is for WeChat server verification during setup
            return self._verify_wechat_server(**kwargs)
        elif request.httprequest.method == 'POST':
            # Process incoming message from WeChat
            return self._handle_incoming_message()

    def _verify_wechat_server(self, signature, timestamp, nonce, echostr, **kwargs):
        """
        Verify the WeChat server during initial setup
        """
        # Get the first configured WeChat app to get the token
        wechat_app = request.env['wms.wechat.app'].sudo().search([('active', '=', True)], limit=1)
        if not wechat_app:
            return Response(response="No active WeChat app configured", status=400)

        # Use app_id as the token for verification (in real implementation,
        # you would use a separate token specifically for verification)
        # This is a simplified approach - for production, use a dedicated token
        token = wechat_app.app_id[:15]  # Just use first 15 chars as a simple token

        sorted_params = sorted([token, timestamp, nonce])
        verification_string = ''.join(sorted_params)

        # Create SHA1 hash
        sha1 = hashlib.sha1()
        sha1.update(verification_string.encode('utf-8'))
        hash_signature = sha1.hexdigest()

        # Verify signature matches
        if hash_signature == signature:
            return Response(response=echostr, status=200)
        else:
            _logger.warning(f"WeChat verification failed. Expected: {hash_signature}, Got: {signature}")
            return Response(response="Verification failed", status=403)

    def _handle_incoming_message(self):
        """
        Handle incoming message from WeChat
        """
        # Parse XML data from the request body
        xml_data = request.httprequest.get_data()
        if not xml_data:
            return Response(response="No data received", status=400)

        try:
            root = ET.fromstring(xml_data.decode('utf-8'))
            message_data = {}
            for child in root:
                message_data[child.tag] = child.text

            # Log the received message
            _logger.info(f"Received WeChat message: {message_data}")

            # Find the WeChat app based on ToUserName (should match our AppID)
            to_user_name = message_data.get('ToUserName', '')
            wechat_app = request.env['wms.wechat.app'].sudo().search([('app_id', '=', to_user_name)], limit=1)

            if not wechat_app:
                # If we can't find the app by ToUserName, use any active app as fallback
                wechat_app = request.env['wms.wechat.app'].sudo().search([('active', '=', True)], limit=1)

            if wechat_app:
                # Process the incoming message
                wechat_message_model = request.env['wms.wechat.message'].sudo()

                # Create and process the incoming message
                result = wechat_message_model.process_incoming_message(message_data)

                # Return success response to WeChat server
                response_xml = """<xml>
                    <ToUserName><![CDATA[{}]]></ToUserName>
                    <FromUserName><![CDATA[{}]]></FromUserName>
                    <CreateTime>{}</CreateTime>
                    <MsgType><![CDATA[text]]></MsgType>
                    <Content><![CDATA[Received]]></Content>
                </xml>""".format(
                    message_data.get('FromUserName', ''),
                    message_data.get('ToUserName', ''),
                    int(request.httprequest.environ.get('REQUEST_TIME', 0))
                )

                return Response(response=response_xml, mimetype='application/xml')
            else:
                _logger.error("No WeChat app found for processing message")
                return Response(response="No configured WeChat app found", status=400)

        except ET.ParseError as e:
            _logger.error(f"Failed to parse XML from WeChat: {str(e)}")
            return Response(response="Invalid XML format", status=400)
        except Exception as e:
            _logger.error(f"Error processing WeChat message: {str(e)}")
            return Response(response="Internal server error", status=500)

    @http.route('/wms/wechat/receive_message', type='json', auth='user', methods=['POST'])
    def receive_manual_message(self, **kwargs):
        """
        Manually trigger message processing for testing purposes
        """
        message_data = kwargs.get('message_data')
        if not message_data:
            return {'error': 'No message data provided'}

        # Find an active WeChat app
        wechat_app = request.env['wms.wechat.app'].search([('active', '=', True)], limit=1)
        if not wechat_app:
            return {'error': 'No active WeChat app configured'}

        # Process the message
        wechat_message_model = request.env['wms.wechat.message'].sudo()
        result = wechat_message_model.process_incoming_message(message_data)

        return {'status': 'success', 'message_id': result.id if result else None}