# Space Degen V1

A simple game. Steer right or left to turn your spaceship. Find treasures hidden at special coordinates. 
Note: the hats are decoration only, don't get too tempted. 

## Docker compose installation

### Generate the animation gifs
For better response times, all animations including remaining moves and lives are pre-generated from the template gifs. Run the following command once to generate the files:
```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install pillow==10.2.0
python3 generate.py
```

### Environment variables
Create a `.env` file:
```
ETH_PRIVATE_KEY=<reward private key>
HUBBLE_URL=http://<hubble-host>:2281/v1
BASE_URL=<frame-url>
REDIS_URL=redis://redis:6379/0
TREASURES="[(<x>, <y>),...]"
```
Note: `TREASURES` is a Python array containing coordinate tuples.

```bash
docker build -t spacedegen .
docker-compose up -d
```

