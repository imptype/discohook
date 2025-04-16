from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import sys
import json
import aiohttp

from . import __version__
from .errors import HTTPException
from .params import _SendingPayload, _EditingPayload

if TYPE_CHECKING:
    from .client import Client

async def json_or_text(response: aiohttp.ClientResponse) -> Union[Dict[str, Any], str]:
    if response.content_type == "application/json":
        return await response.json()
    else:
        return await response.text()

class HTTPClient:
    """Represents an HTTP client for Discord's API."""

    DISCORD_API_VERSION: int = 10

    def __init__(
        self, 
        *, 
        token: Optional[str] = None, 
        application_id: Optional[Union[int, str]] = None, 
        session: Optional[aiohttp.ClientSession] = None
    ):
        self.token = token
        self.application_id = application_id
        self.session = session
        
        user_agent = 'DiscordBot (https://github.com/jnsougata/discohook {0}) Python/{1[0]}.{1[1]} aiohttp/{2}'
        self.user_agent: str = user_agent.format(__version__, sys.version_info, aiohttp.__version__)

    async def request(
        self,
        method: str,
        path: str,
        *,
        payload: Union[_SendingPayload, _EditingPayload],
        authorize: bool = False,
        reason: Optional[str] = None,
        **params: Optional[Dict[str, Any]],
    ):
        headers = {"User-Agent": self.user_agent}
        if authorize:
            headers["Authorization"] = f"Bot {self.token}"
        if reason:
            headers["X-Audit-Log-Reason"] = reason
        data = payload.compile()
        if isinstance(data, str):
            headers["Content-Type"] = "application/json"
        else:
            for key, value in headers.items():
                data.headers.add(key, value)
            headers = data.headers
        if not self.session:
            self.session = aiohttp.ClientSession("https://discord.com")
        resp = await self.session.request(
            method,
            f"/api/v{self.DISCORD_API_VERSION}{path}",
            params=params,
            headers=headers,
            data=data,
        )
        if resp.status >= 400:
            raise HTTPException(resp, await json_or_text(resp))
        return resp

    # Interactions
    # https://discord.com/developers/docs/interactions/receiving-and-responding#interactions

    async def create_interaction_response(
        self, 
        interaction_id: str, 
        interaction_token: str, 
        payload: _SendingPayload,
        **params
    ):
        return await self.request(
            "POST",
            f"/interactions/{interaction_id}/{interaction_token}/callback",
            payload=payload,
            **params
        )

    # Message Resource
    # https://discord.com/developers/docs/resources/channel#channels-resource

    async def create_message(
        self, 
        channel_id: str,
        payload: _SendingPayload
    ):
        return await self.request(
            "POST", 
            f"/channels/{channel_id}/messages", 
            payload=payload,
            authorize=True
        )