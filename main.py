import asyncio
import websockets
import json
import random
import os

clients = set()
game_state = {
    "board": [],
    "revealed": [],
    "turn": "A",
    "players": {}
}

def generate_board():
    pairs = list(range(1, 9)) * 2
    random.shuffle(pairs)
    return pairs

async def notify_state():
    if clients:
        message = json.dumps({
            "type": "state",
            "board": game_state["board"],
            "revealed": game_state["revealed"],
            "turn": game_state["turn"]
        })
        await asyncio.gather(*[client.send(message) for client in clients])

async def handler(websocket):
    global clients, game_state
    clients.add(websocket)
    player_id = "A" if "A" not in game_state["players"].values() else "B"
    game_state["players"][websocket] = player_id

    if len(game_state["players"]) == 2 and not game_state["board"]:
        game_state["board"] = generate_board()
        game_state["revealed"] = [None] * 16

    await websocket.send(json.dumps({"type": "init", "symbol": player_id}))
    await notify_state()

    try:
        async for message in websocket:
            data = json.loads(message)
            if data["type"] == "reveal":
                idx = data["index"]
                if game_state["revealed"][idx] is None:
                    game_state["revealed"][idx] = game_state["board"][idx]
                    await notify_state()
                    await asyncio.sleep(1)

                    revealed_indices = [i for i, val in enumerate(game_state["revealed"]) if val is not None]
                    if len(revealed_indices) % 2 == 0:
                        last_two = revealed_indices[-2:]
                        if game_state["revealed"][last_two[0]] != game_state["revealed"][last_two[1]]:
                            for i in last_two:
                                game_state["revealed"][i] = None
                            game_state["turn"] = "A" if game_state["turn"] == "B" else "B"
                    await notify_state()

    except websockets.exceptions.ConnectionClosed:
        print("Cliente desconectado")
    finally:
        clients.remove(websocket)
        if websocket in game_state["players"]:
            del game_state["players"][websocket]

async def main():
    port = int(os.environ.get("PORT", 10000))
    async with websockets.serve(handler, "", port):
        print(f"Servidor corriendo en el puerto {port}")
        await asyncio.Future()  # Ejecuta indefinidamente

if __name__ == "__main__":
    asyncio.run(main())
