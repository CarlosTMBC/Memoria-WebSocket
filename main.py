import asyncio
import websockets
import json
import random
import os

clients = set()
player_sockets = {}
ready_players = set()
puntos = {"A": 0, "B": 0}

game_state = {
    "board": [],
    "revealed_temp": [],
    "matched": [False] * 16,
    "match_owner": [None] * 16,
    "turn": "A",
    "ready": False
}

ICONS = ['🍎', '🍌', '🍇', '🍓', '🍉', '🍍', '🥝', '🍒']

def generate_board():
    items = ICONS * 2
    random.shuffle(items)
    return items

async def notify_all():
    state_msg = json.dumps({
        "type": "state",
        "board": game_state["board"],
        "matched": game_state["matched"],
        "revealed_temp": game_state["revealed_temp"],
        "turn": game_state["turn"],
        "match_owner": game_state["match_owner"],
        "puntos": puntos
    })
    await asyncio.gather(*(ws.send(state_msg) for ws in clients))

async def handler(websocket):
    global game_state

    try:
        clients.add(websocket)
        player = "A" if "A" not in player_sockets.values() else "B"
        player_sockets[websocket] = player
        await websocket.send(json.dumps({"type": "init", "symbol": player}))

        async for message in websocket:
            data = json.loads(message)

            if data["type"] == "ready":
                ready_players.add(player)
                if len(ready_players) == 2 and not game_state["ready"]:
                    game_state["board"] = generate_board()
                    game_state["revealed_temp"] = [None] * 16
                    game_state["matched"] = [False] * 16
                    game_state["match_owner"] = [None] * 16
                    game_state["ready"] = True
                    game_state["turn"] = "A"
                    await notify_all()

            elif data["type"] == "reset":
                if len(player_sockets) == 2:
                    game_state["board"] = generate_board()
                    game_state["revealed_temp"] = [None] * 16
                    game_state["matched"] = [False] * 16
                    game_state["match_owner"] = [None] * 16
                    game_state["turn"] = "A"
                    game_state["ready"] = True
                    await notify_all()

            elif data["type"] == "reveal" and player == game_state["turn"] and game_state["ready"]:
                idx = data["index"]
                if (
                    idx < 0 or idx >= 16 or
                    game_state["matched"][idx] or
                    game_state["revealed_temp"][idx] is not None
                ):
                    continue

                revealed_indices = [
                    i for i, val in enumerate(game_state["revealed_temp"])
                    if val is not None and not game_state["matched"][i]
                ]
                if len(revealed_indices) >= 2:
                    continue

                game_state["revealed_temp"][idx] = game_state["board"][idx]
                await notify_all()

                revealed_indices = [
                    i for i, val in enumerate(game_state["revealed_temp"])
                    if val is not None and not game_state["matched"][i]
                ]
                if len(revealed_indices) == 2:
                    await asyncio.sleep(1.0)
                    i1, i2 = revealed_indices
                    if game_state["board"][i1] == game_state["board"][i2]:
                        game_state["matched"][i1] = True
                        game_state["matched"][i2] = True
                        game_state["match_owner"][i1] = player
                        game_state["match_owner"][i2] = player
                        puntos[player] += 1
                    else:
                        game_state["revealed_temp"][i1] = None
                        game_state["revealed_temp"][i2] = None
                        game_state["turn"] = "B" if game_state["turn"] == "A" else "A"
                    await notify_all()

    except websockets.exceptions.ConnectionClosed:
        print(f"🔌 Cliente desconectado: {player}")

    finally:
        clients.discard(websocket)
        if websocket in player_sockets:
            jugador = player_sockets[websocket]
            del player_sockets[websocket]
            ready_players.discard(jugador)

        if not clients:
            # Reiniciar el juego si todos se van
            game_state.update({
                "board": [],
                "revealed_temp": [],
                "matched": [False] * 16,
                "match_owner": [None] * 16,
                "turn": "A",
                "ready": False
            })
            puntos["A"] = 0
            puntos["B"] = 0
            ready_players.clear()

# 🔥 Iniciar el servidor WebSocket
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    start_server = websockets.serve(handler, "0.0.0.0", port)
    asyncio.get_event_loop().run_until_complete(start_server)
    print(f"🟢 Servidor WebSocket activo en el puerto {port}")
    asyncio.get_event_loop().run_forever()
