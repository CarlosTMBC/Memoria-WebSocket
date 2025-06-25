import asyncio
import websockets
import json
import random
import os

clients = set()
player_sockets = {}
game_state = {
    "board": [],
    "revealed_temp": [],
    "matched": [],
    "matched_by": [],
    "turn": "A",
    "ready": False,
    "ready_players": set()
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
        "matched_by": game_state["matched_by"],
        "revealed_temp": game_state["revealed_temp"],
        "turn": game_state["turn"],
        "ready_players": list(game_state["ready_players"])
    })
    await asyncio.gather(*(ws.send(state_msg) for ws in clients))

async def handler(websocket):
    global clients, player_sockets, game_state
    clients.add(websocket)

    player = "A" if "A" not in player_sockets.values() else "B"
    player_sockets[websocket] = player
    await websocket.send(json.dumps({"type": "init", "symbol": player}))

    try:
        async for message in websocket:
            data = json.loads(message)

            if data["type"] == "ready":
                game_state["ready_players"].add(player)
                if len(game_state["ready_players"]) == 2 and not game_state["ready"]:
                    game_state["board"] = generate_board()
                    game_state["revealed_temp"] = [None] * 16
                    game_state["matched"] = [False] * 16
                    game_state["matched_by"] = [None] * 16
                    game_state["ready"] = True
                await notify_all()

            elif data["type"] == "reveal" and player == game_state["turn"] and game_state["ready"]:
                idx = data["index"]
                if idx < 0 or idx >= 16:
                    continue
                if game_state["revealed_temp"].count(None) < 14 or game_state["matched"][idx]:
                    continue

                game_state["revealed_temp"][idx] = game_state["board"][idx]
                await notify_all()

                revealed_indices = [i for i, val in enumerate(game_state["revealed_temp"]) if val is not None and not game_state["matched"][i]]

                if len(revealed_indices) == 2:
                    await asyncio.sleep(1)
                    i1, i2 = revealed_indices
                    if game_state["board"][i1] == game_state["board"][i2]:
                        game_state["matched"][i1] = True
                        game_state["matched"][i2] = True
                        game_state["matched_by"][i1] = player
                        game_state["matched_by"][i2] = player
                    else:
                        game_state["revealed_temp"][i1] = None
                        game_state["revealed_temp"][i2] = None
                        game_state["turn"] = "B" if game_state["turn"] == "A" else "A"
                    await notify_all()

    finally:
        clients.remove(websocket)
        del player_sockets[websocket]
        if not clients:
            game_state = {
                "board": [],
                "revealed_temp": [],
                "matched": [],
                "matched_by": [],
                "turn": "A",
                "ready": False,
                "ready_players": set()
            }

PORT = int(os.environ.get("PORT", 8000))
start_server = websockets.serve(handler, "0.0.0.0", PORT)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
