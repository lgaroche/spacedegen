import json
import os
from datetime import datetime

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from web3 import Web3
import redis
from redis.commands.json.path import Path
from jinja2 import Environment, PackageLoader, select_autoescape

from app.farcaster import FCPostData, user_info, validate
from app.game import Action, Direction, SpaceDegenGame

with open('app/erc20.json') as f:
    EIP20_ABI = json.load(f)
BASE_URL = os.environ.get("BASE_URL")

env = Environment(
    loader=PackageLoader("app"),
    autoescape=select_autoescape()
)
template = env.get_template("frame.html")

r = redis.Redis.from_url(os.environ.get("REDIS_URL"), decode_responses=True)

actions = [Action(**json.loads(a)) for a in r.lrange("actions", 0, -1)]
game = SpaceDegenGame(eval(os.environ.get("TREASURES", "[]")))
for action in actions:
    game.move(action)

print(f"Treasures left: {game.treasures}")
print(f"Winners: {[p.id for p, _, _ in game.winners]}")

def gif(direction: Direction):
    return f"{BASE_URL}/static/{direction.name}.gif"

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/user_info/{fid}")
def get_user_info(fid: str, no_cache: bool = False):
    cached = r.hgetall(f"fid:{fid}")
    if cached and not no_cache:
        return cached  
    info = user_info(fid)
    mapping = {
        "pfp": info.pfp,
        "name": info.name,
        "display_name": info.display_name,
        "primary_address": info.primary_address
    }
    r.hset(f"fid:{fid}", mapping=mapping)
    return mapping

def game_over():
    return template.render(
        animation=f"{BASE_URL}/static/gameover.gif", 
        link=("View scores", BASE_URL)
        )

def frame(direction: Direction, moves_left: int, lives: int):
    return template.render(animation=f"{BASE_URL}/static/animation/{direction.value:x}{lives:x}{moves_left:x}.gif", buttons=['<', '>'], url="/play")

@app.get("/", response_class=HTMLResponse)
async def root():
    players = []
    for p in game.state:
        user = get_user_info(p)
        players.append({
            "name": user['name'],
            "pfp": user['pfp'],
            "wins": game.state[p].wins,
            "lives": game.state[p].lives_left(),
            "moves": len([m for flat in game.state[p].moves for m in flat])
        })
    return template.render(
        animation=f"{BASE_URL}/static/intro.gif", 
        buttons=['Start'], 
        url="/start",
        players=players
        )

@app.post("/start", response_class=HTMLResponse)
async def start(data: FCPostData = Body(...)):
    v = validate(data.trustedData.messageBytes)
    if not v.valid:
        return HTTPException(status_code=400, detail="Invalid message")
    fid = v.message.data.fid
    user = get_user_info(fid)
    player = game.player(fid)

    if player.lives_left() == 0:
        return game_over()
    
    print(f"{datetime.now()} - {user['name']} is playing")
    return frame(player.direction, player.moves_left(), player.lives_left())


@app.post('/play', response_class=HTMLResponse)
async def root(data: FCPostData = Body(...)):
    server_time = datetime.now()
    r.rpush("raw", data.model_dump_json())
    v = validate(data.trustedData.messageBytes)
    if not v.valid:
        return HTTPException(status_code=400, detail="Invalid message")
    r.rpush("verified", v.model_dump_json())
    frame_action = v.message.data.frameActionBody
    fc_timestamp = v.message.data.timestamp
    fid = v.message.data.fid
    buttonIndex = frame_action.buttonIndex

    action = Action(fc_timestamp=fc_timestamp, server_timestamp=int(server_time.timestamp()), player_id=fid, steer=buttonIndex-1)
    r.rpush(f"actions", action.model_dump_json())
    r.rpush(f"actions:{fid}", json.dumps({'timestamp': str(server_time), 'steer': action.steer.name}))

    result = game.move(action)
    r.json().set(f"state:{fid}", obj=result.model_dump(), path=Path.root_path())

    if result.win:
        print(f"{datetime.now()} - {fid} won!")
        try:
            pay_reward(fid)
        except Exception as e:
            print(f"Error paying reward to {fid}: {e}")
        return template.render(animation=f"{BASE_URL}/static/found.gif", buttons=['Start again!'], url="/start")

    if result.last:
        if result.player.lives_left() > 0:
            print(f"{datetime.now()} - {fid} lost! {result.player.lives_left()} lives left.")
            return template.render(animation=f"{BASE_URL}/static/lost.gif", buttons=['Try again!'], url="/start")
        else:
            print(f"{datetime.now()} - {fid} lost! Game over.")
            return game_over()

    return frame(
        Direction(result.player.direction), 
        result.player.moves_left(),
        result.player.lives_left()
        )
    

def pay_reward(fid: int):
    info = get_user_info(fid)
    address = Web3.to_checksum_address(info['primary_address'])
    w3 = Web3(Web3.HTTPProvider('https://mainnet.base.org'))
    pk = os.environ.get('ETH_PRIVATE_KEY')
    acct = w3.eth.account.from_key(pk)
    degen = w3.eth.contract(address="0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed", abi=EIP20_ABI)
    nonce = w3.eth.get_transaction_count(acct.address)
    tx = degen.functions.transfer(address, int(20_000e18))
    tx = tx.build_transaction({
        'chainId': 8453,
        'gas': 70000,
        'maxFeePerGas': w3.to_wei('0.001', 'gwei'),
        'maxPriorityFeePerGas': w3.to_wei('0.001', 'gwei'),
        'nonce': nonce,
    })
    r.hset(f"tx:{fid}:{int(datetime.now().timestamp())}", mapping=tx)
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=pk)
    w3.eth.send_raw_transaction(signed_tx.rawTransaction) 
    return {"tx": signed_tx.rawTransaction.hex()} 