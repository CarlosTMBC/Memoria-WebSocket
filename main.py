import asyncio
import websockets
import json
import random
import os

clients = set()
player_sockets = {}
ICONS = ['🍎', '🍌', '🍇', '🍓', '🍉', '🍍', '🥝', '🍒']

# Estado global del juego
game_state = {
    "board": [],
    "revealed_temp": [None] * 16,
    "matched": [False] * 16,
    "turn": "A",
    "ready": False
}

def generate_board():
    items = ICONS * 2
    random.shuffle(items)
    return items

async def notify_all():
    message = json.dumps({
        "type": "state",
        "board": game_state["board"],
        "revealed_temp": game_state["revealed_temp"],
        "matched": game_state["matched"],
        "turn": game_state["turn"]
    })
    await asyncio.gather(*[ws.send(message) for ws in clients])

async def handler(websocket):
    global clients, player_sockets, game_state
    clients.add(websocket)

    # Asignar jugador A o B
    player = "A" if "A" not in player_sockets.values() else "B"
    player_sockets[websocket] = player

    await websocket.send(json.dumps({"type": "init", "symbol": player}))

    # Iniciar el juego solo si hay 2 jugadores conectados
    if len(player_sockets) == 2 and not game_state["ready"]:
        game_state["board"] = generate_board()
        game_state["revealed_temp"] = [None] * 16
        game_state["matched"] = [False] * 16
        game_state["turn"] = "A"
        game_state["ready"] = True
        await notify_all()

    try:
        async for message in websocket:
            data = json.loads(message)

            if data["type"] == "reveal" and player == game_state["turn"]:
                idx = data["index"]

                if (
                    idx < 0 or idx >= 16 or
                    game_state["matched"][idx] or
                    game_state["revealed_temp"][idx] is not None
                ):
                    continue

                # Revelar carta
                game_state["revealed_temp"][idx] = game_state["board"][idx]
                await notify_all()

                revealed = [i for i, val in enumerate(game_state["revealed_temp"]) if val and not game_state["matched"][i]]

                if len(revealed) == 2:
                    await asyncio.sleep(1.2)
                    i1, i2 = revealed

                    if game_state["board"][i1] == game_state["board"][i2]:
                        game_state["matched"][i1] = True
                        game_state["matched"][i2] = True
                    else:
                        game_state["revealed_temp"][i1] = None
                        game_state["revealed_temp"][i2] = None
                        game_state["turn"] = "B" if game_state["turn"] == "A" else "A"

                    await notify_all()

    except Exception as e:
        print(f"[Error] {e}")

    finally:
        clients.remove(websocket)
        if websocket in player_sockets:
            del player_sockets[websocket]

        if not clients:
            # Reiniciar el juego si todos se desconectan
            game_state = {
                "board": [],
                "revealed_temp": [None] * 16,
                "matched": [False] * 16,
                "turn": "A",
                "ready": False
            }

# Servidor WebSocket usando el puerto que Render proporciona
PORT = int(os.environ.get("PORT", 8000))
start_server = websockets.serve(handler, "0.0.0.0", PORT)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
