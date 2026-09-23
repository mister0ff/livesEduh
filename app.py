import asyncio
import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from TikTokLive import TikTokLiveClient
from TikTokLive.events import LikeEvent, FollowEvent, GiftEvent, ConnectEvent
from TikTokLive.client.web.web_settings import WebDefaults

app = FastAPI()

# Configuração da API do EulerStream
API_KEY = "cd948ded95a99c618e759b77b97d3f22a2deddb40d02403b95417acd6bcb099d"
WEBHOOK_URL = "https://n8n.seusite.com/webhook/tiktok"  # Altere se necessário

WebDefaults.tiktok_sign_url = "https://host.eulerstream.com/web/fetch"
WebDefaults.tiktok_sign_api_key = API_KEY

# Variáveis globais
current_client = None
current_task = None
active_user = None

curtidas_registradas = set()
eventos_feed = []
event_counter = 0


def enviar_webhook(payload: dict):
    try:
        requests.post(WEBHOOK_URL, json=payload, timeout=5)
    except Exception as e:
        print(f"[WEBHOOK ERRO] {e}")


def registrar_evento(evento_dict: dict):
    global event_counter
    event_counter += 1
    evento_dict["id"] = event_counter
    eventos_feed.append(evento_dict)

    if len(eventos_feed) > 50:
        eventos_feed.pop(0)


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return HTMLResponse("<h2>Arquivo index.html não encontrado!</h2>", status_code=404)


@app.get("/api/events")
async def get_events(since: int = 0):
    novos = [e for e in eventos_feed if e["id"] > since]
    return {
        "status": "ok",
        "username": active_user,
        "last_id": event_counter,
        "eventos": novos
    }


@app.post("/api/connect")
async def connect_live(username: str):
    global current_client, current_task, active_user, curtidas_registradas

    clean = username.replace("@", "").strip()
    if not clean:
        raise HTTPException(status_code=400, detail="Username inválido")

    # Desconecta a live anterior se houver
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

    # Inicializa sem o parâmetro web_kwargs que causava o erro
    client = TikTokLiveClient(unique_id=f"@{clean}")
    current_client = client

    @client.on(ConnectEvent)
    async def on_connect(event: ConnectEvent):
        print(f"[CONECTADO] @{clean}")
        registrar_evento({
            "tipo": "connect",
            "nome": clean,
            "avatar": ""
        })

    @client.on(LikeEvent)
    async def on_like(event: LikeEvent):
        user_id = getattr(event.user, "unique_id", None) or getattr(event.user, "nickname", "desconhecido")
        avatar = getattr(event.user.avatar, "urls", [""])[0] if getattr(event.user, "avatar", None) else ""

        if user_id not in curtidas_registradas:
            curtidas_registradas.add(user_id)
            payload = {
                "tipo": "like",
                "nome": user_id,
                "avatar": avatar,
                "live": clean
            }
            registrar_evento(payload)
            enviar_webhook(payload)

    @client.on(FollowEvent)
    async def on_follow(event: FollowEvent):
        user_id = getattr(event.user, "unique_id", None) or getattr(event.user, "nickname", "desconhecido")
        avatar = getattr(event.user.avatar, "urls", [""])[0] if getattr(event.user, "avatar", None) else ""

        payload = {
            "tipo": "follow",
            "nome": user_id,
            "avatar": avatar,
            "live": clean
        }
        registrar_evento(payload)
        enviar_webhook(payload)

    @client.on(GiftEvent)
    async def on_gift(event: GiftEvent):
        if event.gift.streakable and event.gift.has_next_streak:
            return

        user_id = getattr(event.user, "unique_id", None) or getattr(event.user, "nickname", "desconhecido")
        avatar = getattr(event.user.avatar, "urls", [""])[0] if getattr(event.user, "avatar", None) else ""
        gift_name = getattr(event.gift, "name", "Presente")
        gift_repeat = getattr(event.gift, "repeat_count", 1)

        payload = {
            "tipo": "gift",
            "nome": user_id,
            "avatar": avatar,
            "presente": gift_name,
            "valor": gift_repeat,
            "live": clean
        }
        registrar_evento(payload)
        enviar_webhook(payload)

    async def runner():
        try:
            await client.start()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[ERRO CLIENTE] {e}")
            registrar_evento({
                "tipo": "erro",
                "nome": "Sistema",
                "mensagem": str(e)
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

    active_user = None
    return {"status": "disconnected"}

