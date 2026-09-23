import asyncio
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, FollowEvent, LikeEvent, GiftEvent
import firebase_admin
from firebase_admin import db

app = FastAPI()

# Inicializa o Firebase Admin SDK
if not firebase_admin._apps:
    firebase_admin.initialize_app(options={
        'databaseURL': 'https://starcord-14470-default-rtdb.firebaseio.com'
    })

current_client = None
active_user = ""
curtidas_registradas = set()

def extrair_usuario(event):
    nome = getattr(event.user, 'unique_id', None) or getattr(event.user, 'nickname', None)
    avatar = None
    if hasattr(event.user, 'avatar_thumb') and hasattr(event.user.avatar_thumb, 'm_urls'):
        urls = event.user.avatar_thumb.m_urls
        if urls:
            avatar = urls[0]
    return nome, avatar

@app.get("/", response_class=HTMLResponse)
async def home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/connect")
async def connect_live(username: str):
    global current_client, active_user, curtidas_registradas
    
    clean_username = username.replace("@", "").strip()
    
    if current_client and current_client.connected:
        await current_client.disconnect()
        
    curtidas_registradas.clear()
    active_user = clean_username
    
    # Limpa eventos antigos no banco
    db.reference('eventos/').delete()

    current_client = TikTokLiveClient(unique_id=clean_username)

    @current_client.on(ConnectEvent)
    async def on_connect(event: ConnectEvent):
        print(f"✅ Conectado na live de @{clean_username}")

    @current_client.on(FollowEvent)
    async def on_follow(event: FollowEvent):
        nome, avatar = extrair_usuario(event)
        if nome:
            db.reference('eventos/').push({
                'tipo': 'follow',
                'nome': nome,
                'avatar': avatar
            })

    @current_client.on(LikeEvent)
    async def on_like(event: LikeEvent):
        nome, avatar = extrair_usuario(event)
        if nome and nome not in curtidas_registradas:
            curtidas_registradas.add(nome)
            db.reference('eventos/').push({
                'tipo': 'like',
                'nome': nome,
                'avatar': avatar
            })

    @current_client.on(GiftEvent)
    async def on_gift(event: GiftEvent):
        if event.gift.streakable and not event.gift.streaking:
            return
        nome, avatar = extrair_usuario(event)
        if nome:
            valor = event.gift.diamond_count * event.repeat_count
            db.reference('eventos/').push({
                'tipo': 'gift',
                'nome': nome,
                'avatar': avatar,
                'valor': valor,
                'presente': event.gift.name
            })

    asyncio.create_task(current_client.start())
    return {"status": "success", "username": clean_username}

@app.post("/api/disconnect")
async def disconnect_live():
    global current_client, active_user
    if current_client and current_client.connected:
        await current_client.disconnect()
    active_user = ""
    return {"status": "disconnected"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
