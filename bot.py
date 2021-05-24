import asyncio, datetime, discord, json, re, requests, time

config = {}

def load():
  global config
  with open("config.json", "r") as f:
    config = json.load(f)

def save():
  with open("config.json", "w") as f:
    json.dump(config, f)

class TTBClient(discord.Client):
  def __init__(self):
    discord.Client.__init__(self, intents = discord.Intents.all())

  async def on_ready(self):
    print("Turtle Bot has started.")
  
  async def on_message(self, message):
    # TODO commands
    pass

async def reminder_cycle():
  while True:
    await asyncio.sleep(-time.time() % 3600)
    # TODO scheduled reminder
    await asyncio.sleep(10)

if __name__ == "__main__":
  load()

  client = TTBClient()
  
  asyncio.get_event_loop().run_until_complete(asyncio.gather(
    client.start(config["discord-token"]),
    reminder_cycle()
  ))