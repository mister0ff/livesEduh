import asyncio
import os
import traceback
from collections import deque
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

# 👇 IMPORTA O CONFIGURADOR DO SIGN SERVER
from TikTokLive.client.web.web_settings import WebDefaults

# 👇 CONFIGURA SUA API KEY (antes de qualquer TikTokLiveClient)
WebDefaults.tiktok_sign_api_key = "6be8e64053613eb3178e840c53847fb33d4b29ece3ee5095448eb6e57964ab7d"

from TikTokLive import TikTokLiveClient
from TikTokLive.events import (
    ConnectEvent, DisconnectEvent, FollowEvent, LikeEvent, GiftEvent
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------
# Estado global (em memória — sem Firebase)
# ---------------------------------------------------------------
current_client: Optional[TikTokLiveClient] = None
current_task: Optional[asyncio.Task] = None
active_user: str = ""

eventos_feed: deque = deque(maxlen=200)
evento_id: int = 0
curtidas_registradas: set = set()


def extrair_usuario(event):
    user = getattr(event, "user", None)
    if not user:
        return None, None
    nome = getattr(user, "unique_id", None) or getattr(user, "nickname", None)
    avatar = None
    pic = getattr(user, "avatar_thumb", None)
    if pic is not None:
        urls = getattr(pic, "m_urls", None) or getattr(pic, "urls", None)
        if urls:
            avatar = urls[0]
    return nome, avatar


def push_evento(payload: dict):
    global evento_id
    evento_id += 1
    payload["_id"] = evento_id
    eventos_feed.append(payload)
    print(f"[EVENTO #{evento_id}] {payload.get('tipo')} - {payload.get('nome')}")


# ---------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/events")
async def get_events(since: int = Query(0)):
    novos = [ev for ev in eventos_feed if ev.get("_id", 0) > since]
    last_id = novos[-1]["_id"] if novos else since
    return {"eventos": novos, "last_id": last_id}


@app.get("/api/status")
async def get_status():
    conectado = bool(current_client and current_client.connected)
    return {"conectado": conectado, "user": active_user}


@app.post("/api/connect")
async def connect_live(username: str):
    global current_client, current_task, active_user, curtidas_registradas

    clean = username.replace("@", "").strip()
    if not clean:
        return {"status": "error", "message": "username vazio"}

    if current_client is not None:
        try:
            await current_client.disconnect()
        except Exception:
            pass
        current_client = None

    if current_task and not current_task.done():
        current_task.cancel()
        try:
            await current_task
        except Exception:
            pass

    curtidas_registradas.clear()
    eventos_feed.clear()
    active_user = clean

    client = TikTokLiveClient(unique_id=f"@{clean}")
    current_client = client

    @client.on(ConnectEvent)
    async def on_connect(event: ConnectEvent):
        print(f"✅ Conectado em @{clean}")
        push_evento({
            "tipo": "connect",
            "nome": "Sistema",
            "avatar": None,
        })

    @client.on(DisconnectEvent)
    async def on_disconnect(event: DisconnectEvent):
        print(f"⚠️ Desconectado de @{clean}")

    @client.on(FollowEvent)
    async def on_follow(event: FollowEvent):
        nome, avatar = extrair_usuario(event)
        if nome:
            push_evento({"tipo": "follow", "nome": nome, "avatar": avatar})

    @client.on(LikeEvent)
    async def on_like(event: LikeEvent):
        nome, avatar = extrair_usuario(event)
        if nome and nome not in curtidas_registradas:
            curtidas_registradas.add(nome)
            push_evento({"tipo": "like", "nome": nome, "avatar": avatar})

    @client.on(GiftEvent)
    async def on_gift(event: GiftEvent):
        gift = event.gift
        if getattr(gift, "streakable", False) and getattr(gift, "streaking", False):
            return
        nome, avatar = extrair_usuario(event)
        if not nome:
            return
        valor = (getattr(gift, "diamond_count", 0) or 0) * getattr(event, "repeat_count", 1)
        push_evento({
            "tipo": "gift",
            "nome": nome,
            "avatar": avatar,
            "valor": valor,
            "presente": getattr(gift, "name", "Presente"),
        })

    async def runner():
        try:
            await client.start()
        except Exception as e:
            print("❌ Erro no client TikTok:", e)
            traceback.print_exc()
            push_evento({
                "tipo": "erro",
                "nome": "Sistema",
                "avatar": None,
                "mensagem": str(e),
            })

    current_task = asyncio.create_task(runner())
    return {"status": "success", "username": clean}


@app.post("/api/disconnect")
async def disconnect_live():
    global current_client, current_task, active_user

    if current_client is not None:
        try:
            await current_client.disconnect()
        except Exception:
            pass
        current_client = None

    if current_task and not current_task.done():
        current_task.cancel()
        try:
            await current_task
        except Exception:
            pass

    active_user = ""
    return {"status": "disconnected"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
