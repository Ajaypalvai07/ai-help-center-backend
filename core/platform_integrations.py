from typing import Dict, Any, Optional, List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import pymsteams
import requests
from .config import settings
import logging

class PlatformIntegrations:
    def __init__(self):
        # Initialize platform clients
        self.slack = WebClient(token=settings.SLACK_BOT_TOKEN) if settings.SLACK_BOT_TOKEN else None
        self.teams = pymsteams.connectorcard(settings.TEAMS_WEBHOOK_URL) if settings.TEAMS_WEBHOOK_URL else None
        self.whatsapp_token = settings.WHATSAPP_API_KEY
        self.whatsapp_url = "https://graph.facebook.com/v17.0"

    async def send_message(
        self,
        platform: str,
        channel_id: str,
        message: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send message to specified platform"""
        try:
            if platform == "slack":
                return await self._send_slack_message(channel_id, message, attachments)
            elif platform == "teams":
                return await self._send_teams_message(channel_id, message, attachments)
            elif platform == "whatsapp":
                return await self._send_whatsapp_message(channel_id, message, attachments)
            else:
                raise ValueError(f"Unsupported platform: {platform}")
        except Exception as e:
            logging.error(f"Error sending message to {platform}: {e}")
            raise

    async def _send_slack_message(
        self,
        channel_id: str,
        message: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send message to Slack channel"""
        try:
            response = await self.slack.chat_postMessage(
                channel=channel_id,
                text=message,
                attachments=attachments
            )
            return {
                "platform": "slack",
                "success": True,
                "message_id": response["ts"],
                "channel_id": channel_id
            }
        except SlackApiError as e:
            logging.error(f"Slack API error: {e}")
            raise

    async def _send_teams_message(
        self,
        channel_id: str,
        message: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send message to Microsoft Teams channel"""
        try:
            self.teams.text(message)
            if attachments:
                for attachment in attachments:
                    self.teams.addLinkCard(attachment.get("title", ""), attachment.get("url", ""))
            self.teams.send()
            return {
                "platform": "teams",
                "success": True,
                "message_id": None,  # Teams webhook doesn't return message ID
                "channel_id": channel_id
            }
        except Exception as e:
            logging.error(f"Teams API error: {e}")
            raise

    async def _send_whatsapp_message(
        self,
        phone_number: str,
        message: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Send message via WhatsApp"""
        try:
            headers = {
                "Authorization": f"Bearer {self.whatsapp_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {"body": message}
            }
            
            if attachments:
                # Handle attachments if needed
                pass
            
            response = requests.post(
                f"{self.whatsapp_url}/messages",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            result = response.json()
            
            return {
                "platform": "whatsapp",
                "success": True,
                "message_id": result.get("messages", [{}])[0].get("id"),
                "recipient": phone_number
            }
        except Exception as e:
            logging.error(f"WhatsApp API error: {e}")
            raise

platform_integrations = PlatformIntegrations()