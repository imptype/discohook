import json
import mimetypes
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional, Tuple, Union, TYPE_CHECKING

import aiohttp

from .embed import Embed
from .file import File
from .models import AllowedMentions, MessageReference
from .view import View

if TYPE_CHECKING:
    from .poll import Poll

MISSING = Any

class _SendingPayload:
    def __init__(
        self,
        *,
        content: Optional[str] = None,
        embed: Optional[Embed] = None,
        embeds: Optional[List[Embed]] = None,
        view: Optional[View] = None,
        tts: Optional[bool] = False,
        file: Optional[File] = None,
        files: Optional[List[File]] = None,
        ephemeral: Optional[bool] = False,
        allowed_mentions: Optional[AllowedMentions] = None,
        message_reference: Optional[MessageReference] = None,
        sticker_ids: Optional[List[str]] = None,
        suppress_embeds: Optional[bool] = False,
        supress_notifications: Optional[bool] = False,
        poll: Optional["Poll"] = None,
        payload_type: Optional[Enum] = None,
        **kwargs
    ):
        self.content = content
        self.embed = embed
        self.embeds = embeds
        self.view = view
        self.tts = tts
        self.file = file
        self.files = files
        self.ephemeral = ephemeral
        self.allowed_mentions = allowed_mentions
        self.message_reference = message_reference
        self.sticker_ids = sticker_ids
        self.suppress_embeds = suppress_embeds
        self.supress_notifications = supress_notifications
        self.poll = poll
        self.payload_type = payload_type
        self.kwargs = kwargs

    def _merge_fields(self):
        if not self.files or self.files is MISSING:
            self.files = []
        if not self.embeds or self.embeds is MISSING:
            self.embeds = []
        if self.file and self.file is not MISSING:
            self.files.append(self.file)
        if self.embed and self.embed is not MISSING:
            self.embeds.append(self.embed)
        for embed in self.embeds:
            self.files.extend(embed.attachments)

    def _handle_params(self) -> Dict[str, Any]:
        self._merge_fields()
        payload = {}
        flag_value = 0
        if self.ephemeral:
            flag_value |= 1 << 6
        if self.suppress_embeds:
            flag_value |= 1 << 2
        if self.supress_notifications:
            flag_value |= 1 << 12
        if self.content:
            payload["content"] = str(self.content)
        if self.tts:
            payload["tts"] = True
        if self.embeds:
            payload["embeds"] = [embed.to_dict() for embed in self.embeds]
        if self.view:
            payload["components"] = self.view.components
        if self.allowed_mentions:
            payload["allowed_mentions"] = self.allowed_mentions.to_dict()
        if self.message_reference:
            payload["message_reference"] = self.message_reference.to_dict()
        if self.sticker_ids:
            payload["sticker_ids"] = self.sticker_ids
        if self.files:
            payload["attachments"] = [
                {
                    "id": i,
                    "filename": file.name,
                    "ephemeral": file.spoiler,
                    "description": file.description,
                }
                for i, file in enumerate(self.files)
            ]
        if flag_value:
            payload["flags"] = flag_value
        if self.poll:
            payload["poll"] = self.poll.to_dict()
        return payload

    def compile(self) -> Union[str, aiohttp.MultipartWriter]:
        data = self._handle_params()
        data.update(**self.kwargs)

        if self.payload_type is not None:
            data = {"data": data, "type": int(self.payload_type.value)}

        if self.files:
            form = aiohttp.MultipartWriter("form-data")
            form.append(
                json.dumps(data),
                headers={
                    "Content-Disposition": 'form-data; name="payload_json"',
                    "Content-Type": "application/json",
                },
            )
            for i, file in enumerate(self.files):
                mime, _ = mimetypes.guess_type(file.name)
                form.append(
                    file.content,
                    headers={
                        "Content-Disposition": f'form-data; name="files[{i}]"; filename="{file.name}"',
                        "Content-Type": mime or "application/octet-stream",
                    },
                )
            return form

        return json.dumps(data)

class _EditingPayload(_SendingPayload):
    def __init__(
        self,
        *,
        content: Optional[str] = MISSING,
        embed: Optional[Embed] = MISSING,
        embeds: Optional[List[Embed]] = MISSING,
        view: Optional[View] = MISSING,
        tts: Optional[bool] = MISSING,
        file: Optional[File] = MISSING,
        files: Optional[List[File]] = MISSING,
        suppress_embeds: Optional[bool] = MISSING,
        payload_type: Optional[Enum] = None,
        **kwargs
    ):
        super().__init__(
            content=content,
            embed=embed,
            embeds=embeds,
            view=view,
            tts=tts,
            file=file,
            files=files,
            suppress_embeds=suppress_embeds,
            payload_type=payload_type,
            **kwargs
        )

    def _handle_params(self) -> Dict[str, Any]:
        self._merge_fields()
        payload = {}
        if self.embed is None or self.embeds is None:
            payload["embeds"] = []
        if self.view is None:
            payload["components"] = []
        if self.file is None or self.files is None:
            payload["attachments"] = []

        if self.content is not MISSING:
            payload["content"] = str(self.content)
        if self.tts is not MISSING:
            payload["tts"] = self.tts
        if self.embeds:
            payload["embeds"] = [embed.to_dict() for embed in self.embeds]
        if self.view is not MISSING:
            payload["components"] = self.view.components if self.view else []
        if self.files:
            payload["attachments"] = [
                {
                    "id": i,
                    "filename": file.name,
                    "ephemeral": file.spoiler,
                    "description": file.description,
                }
                for i, file in enumerate(self.files)
            ]
        if self.suppress_embeds is not MISSING:
            payload["flags"] = 1 << 2

        return payload