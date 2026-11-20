from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, FileResponse
from django.shortcuts import render

from channels.generic.websocket import AsyncWebsocketConsumer
import json
import socket

def connect(request):
    return render(request, "client.html")

def lobby(request):
    if not settings.IP:
        # get own IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        # doesn't even have to be reachable
        s.connect(('213.61.198.13', 1))  # RLI
        ip = s.getsockname()[0]
        s.close()
    else:
        ip = settings.IP
    return render(request, 'lobby.html', {'ip': ip, 'port': settings.PORT})

def watch(request):
    return render(request, "santa.html")


players = dict()  # ip -> position [-1, 1]

class Consumer(AsyncWebsocketConsumer):

    async def connect(self):
        # join room group
        self.is_santa = "santa" in self.scope["path"]
        if self.is_santa:
            await self.channel_layer.group_add("santa", self.channel_name)
        else:
            players[self] = False
            await self.channel_layer.group_add("players", self.channel_name)
            # player joined: send message to santa
            await self.channel_layer.group_send("santa", {"type": "msg", "message": {
                "players": len(players),
                "position": sum(players.values()) / len(players),
            }})
        await self.accept()

    async def disconnect(self, close_code):
        # leave room group
        if self.is_santa:
            await self.channel_layer.group_discard('santa', self.channel_name)
        else:
            players.pop(self, None)
            await self.channel_layer.group_discard('players', self.channel_name)
            await self.channel_layer.group_send("santa", {"type": "msg", "message": {
                "players": len(players),
                "position": sum(players.values()) / max(len(players), 1),
            }})

    async def receive(self, text_data):
        # receive message from websocket
        players[self] = json.loads(text_data)["pos"]
        await self.channel_layer.group_send("santa", {"type": "msg", "message": {
            "players": len(players),
            "position": sum(players.values()) / len(players),
        }})

    async def msg(self, message):
        await self.send(text_data=json.dumps(message["message"]))

def serve_xml_level(request):
    file_path = Path(settings.ROOT_DIR) / "santa/static/Level1.svg"
    return FileResponse(open(file_path, 'rb'), content_type='application/xml')


def single_play(request):
    return render(request, "single_play.html")
