from django.shortcuts import render

import asyncio
from threading import Thread

from urllib.parse import urljoin
import json
import requests

from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

from typing import List, Dict

from .models import DialogueModel, DialogueNatCSModel, DialogueTweetSummModel, DialogueTeacherStudentChatroomModel
from me_project.web_utils.utils import *


class DialogueDocConsumer(AsyncWebsocketConsumer):
    WELCOME_MESSAGE = 'Hello, how may I assist you?'

    model = DialogueModel

    template_name = 'message.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #
        self.doc: Optional[str] = None
        self.utterances: List[Dict] = list()
        #
        self.document_id: Optional[str] = None
        self.room_group_name: Optional[str] = None
        self.chat_id: Optional[str] = None

    @sync_to_async
    def _load_doc(self):
        self.doc = self.model.objects.get(pk=self.dialogue_id).to_doc()

    async def _send_welcome_message(self):
        welcome_message = {
            'speaker': 'assistant',
            'text': self.WELCOME_MESSAGE
        }
        self.utterances.append(welcome_message)

        await self.channel_layer.group_send(
            self.room_group_name, welcome_message | {'type': 'chat_message'}
        )

    async def connect(self):
        # Get connection metadata
        self.dialogue_id = self.scope['url_route']['kwargs']['dialogue_id']
        self.room_group_name = f'{self.scope["session"].session_key}-{self.model.DATA_SET_ID}-{self.dialogue_id}'
        # Load document text
        await self._load_doc()
        # Complete setup
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        # Send welcome message
        Thread(target=asyncio.run, args=(self._send_welcome_message(),)).start()

    async def disconnect(self, close_code):
        # Discard connection
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = {
            'speaker': text_data_json['speaker'],
            'text': text_data_json['text']
        }
        self.utterances.append(message)
        # Process message if valid
        if len(message['text']) > 0:  # TODO find better solution for initial empty message issue
            # Send message to chat
            await self.channel_layer.group_send(
                self.room_group_name, message | {'type': 'chat_message'}
            )
            # Generate chatbot response
            Thread(target=asyncio.run, args=(self._respond(),)).start()

    async def _respond(self):
        # Generate response
        params = {
            'document': self.doc,
            'utterances': self.utterances,
            'corpus': self.model.DATA_SET_ID
        }
        http_response = requests.post(
            urljoin(GENERATOR_SERVICE_URL, INFO_EXTRACTION_PATH), data=json.dumps({'params': params})
        )
        response = {'speaker': 'assistant', 'text': 'ERROR'}
        if http_response.status_code == 200:
            response = http_response.json()['response']
        self.utterances.append(response)
        # Send message to chat
        await self.channel_layer.group_send(
            self.room_group_name, response | {'type': 'chat_message'}
        )

    async def chat_message(self, event):
        data = {
            'html_response': render(
                None,
                self.template_name,
                context={'utterance': {'speaker': event['speaker'], 'text': event['text']}}
            ).content.decode('utf-8'),
            'is_user': event['speaker'] == 'user'
        }
        await self.send(text_data=json.dumps(data))


class DialogueNatCSDocConsumer(DialogueDocConsumer):
    model = DialogueNatCSModel


class DialogueTweetSummDocConsumer(DialogueDocConsumer):
    model = DialogueTweetSummModel


class DialogueTeacherStudentChatroomDocConsumer(DialogueDocConsumer):
    model = DialogueTeacherStudentChatroomModel
