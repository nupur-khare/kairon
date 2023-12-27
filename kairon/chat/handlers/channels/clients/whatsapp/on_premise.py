import logging
from typing import Text, Dict

from kairon.chat.handlers.channels.clients.whatsapp.cloud import WhatsappCloud
from kairon.exceptions import AppException
from kairon.shared.rest_client import AioRestClient
from kairon.shared.utils import Utility

logger = logging.getLogger(__name__)

DEFAULT_API_VERSION = 13.0


class WhatsappOnPremise(WhatsappCloud):

    def __init__(self, access_token, **kwargs):
        """
            @required:
                access_token
            @optional:
                session
                api_version
                app_secret
        """
        super().__init__(access_token, **kwargs)
        self.access_token = access_token
        self.client = AioRestClient(False)

    async def send_action(self, payload, timeout=None, **kwargs):
        """
            @required:
                payload: message request payload
            @optional:
                timeout: request timeout
            @outputs: response json
        """
        is_streaming_resp = kwargs.get("stream", False)
        url = '{app}/messages'.format(app=self.app)
        resp = await self.client.request("POST", url, headers=self.auth_args, request_body=payload, timeout=timeout,
                                              return_json=False, is_streaming_resp=is_streaming_resp, max_retries=3)
        logger.debug(resp)
        return resp

    async def get_attachment(self, media_id, timeout=None):
        """
            @required:
                media_id: audio/video/image/document id
            @optional:
                timeout: request timeout
            @outputs: response json
        """
        url = '{app}/media/{media_id}'.format(app=self.app, media_id=media_id)
        resp = await self.client.request("GET", url, headers=self.auth_args, timeout=timeout,
                                              return_json=False, max_retries=3)
        logger.debug(resp)
        return resp

    async def mark_as_read(self, msg_id, timeout=None):
        payload = {
            "status": "read"
        }
        url = '{app}/messages/{message_id}'.format(app=self.app, message_id=msg_id)
        resp = await self.client.request("PUT", url, headers=self.auth_args, request_body=payload, timeout=timeout,
                                              return_json=False, max_retries=3)
        logger.debug(resp)
        return resp

    async def send_template_message(self, name: Text, to_phone_number, language_code: Text = "en", components: Dict = None, namespace: Text = None):
        if Utility.check_empty_string(namespace):
            raise AppException("namespace is required to send messages using on-premises api!")

        payload = {
            "namespace": namespace,
            "language": {
                "policy": "deterministic",
                "code": language_code
            },
            "name": name
        }
        if components:
            payload.update({"components": components})
        return await self.send(payload, to_phone_number, messaging_type="template")
