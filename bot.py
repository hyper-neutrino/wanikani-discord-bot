import asyncio, datetime, discord, json, re, requests, time

config = {}

def load():
  global config
  with open("../configurations/paimon.json", "r") as f:
    config = json.load(f)

def save():
  with open("../configurations/paimon.json", "w") as f:
    json.dump(config, f)

load()

class RSClient(discord.Client):
  def __init__(self):
    discord.Client.__init__(self, intents = discord.Intents.all())

  async def on_ready(self):
    print("Turtle Bot has started.")
  
  async def on_message(self, message):
    if message.content.startswith("banbyname") and message.author.id == config["owner"]:
      bl = []
      name = message.content[10:]
      await message.channel.send(f"Banning everyone named `{name}`...")
      for member in message.guild.members:
        if member.name == name:
          bl.append(member)
      c = ""
      for m in bl:
        if len(c + m.mention) > 2000:
          await message.channel.send(c)
          c = ""
        c += m.mention
      await message.channel.send(c)
      await message.channel.send("Confirm banning all of these users? (say `confirm`)")
      try:
        await client.wait_for("message", check = lambda m: m.channel == message.channel and m.content == "confirm" and m.author.id == config["owner"], timeout = 10)
        for x in bl:
          await x.ban()
      except:
        await message.channel.send("Timed out.")
        raise
    elif message.content.startswith("wk.apitoken"):
      if message.content == "wk.apitoken":
        if str(message.author.id) in config["wk-tokens"]:
          del config["wk-tokens"][str(message.author.id)]
          save()
          await message.channel.send(embed = discord.Embed(description = "I have removed your WaniKani API token from my records! It is still recommended that you invalidate your token regardless."))
          return
        else:
          await message.channel.send(embed = discord.Embed(description = "You don't have an API token to un-save!"))
          return
      match = re.match(r"wk\.apitoken\s+([A-Fa-f0-9\-]{8}-[A-Fa-f0-9\-]{4}-[A-Fa-f0-9\-]{4}-[A-Fa-f0-9\-]{4}-[A-Fa-f0-9\-]{12})", message.content)
      if match:
        config["wk-tokens"][str(message.author.id)] = match.group(1)
        save()
        await message.channel.send(embed = discord.Embed(description = f"I have saved your WaniKani API token: `{match.group(1)}`!"))
      else:
        await message.channel.send(embed = discord.Embed(description = "Error: API token is formatted incorrectly / missing; check to make sure you copy-pasted it correctly."))
    elif message.content == "wk.watch":
      if str(message.channel.id) in config["wk-channels"]:
        await message.channel.send(embed = discord.Embed(description = "I am already sending reminders to this channel!"))
      else:
        config["wk-channels"][str(message.channel.id)] = 0
        save()
        await message.channel.send(embed = discord.Embed(description = "I will start sending reminders to this channel!"))
        await remind(message.channel)
    elif message.content == "wk.unwatch":
      if str(message.channel.id) not in config["wk-channels"]:
        await message.channel.send(embed = discord.Embed(description = "I am not currently sending reminders to this channel!"))
      else:
        del config["wk-channels"][str(message.channel.id)]
        save()
        await message.channel.send(embed = discord.Embed(description = "I will no longer send reminders to this channel!"))
    elif message.content == "wk.update":
      await remind(message.channel, False, True)
    elif message.content.startswith("wk.tz"):
      match = re.match(r"wk\.tz\s+(-?\d+)")
      if match:
        config["tz"] = int(match.group(1))
        save()
        await message.channel.send(embed = discord.Embed(description = f"Set your timezone to {match.group(1)} (hours relative to UTC)!"))
      else:
        await message.channel.send(embed = discord.Embed(description = "Malformed command; please enter `wk.tz #` for some integer (hours relative to UTC)!"))
    elif message.content == "wk.ping":
      if message.author.id in config["noping"]:
        config["noping"].remove(message.author.id)
        save()
      await message.add_reaction("✅")
    elif message.content == "wk.noping":
      if message.author.id not in config["noping"]:
        config["noping"].append(message.author.id)
        save()
      await message.add_reaction("✅")
    elif message.content == "wk.help":
      await message.channel.send(embed = discord.Embed(
        title = "Command List",
        description = """```
wk.apitoken <token> - set your API token
wk.apitoken         - remove your API token
wk.watch            - start sending reports to this channel (and immediately send one)
wk.unwatch          - stop sending reports to this channel
wk.update           - immediately send a report to this channel (doesn't ping anyone)
wk.tz <number>      - set the timezone in hours relative to UTC
wk.ping             - enable pinging for you
wk.noping           - disable pinging for you
wk.help             - show this message
```"""
      ))
    elif message.content.startswith("wk.purge") and message.author.id in config["admins"]:
      uid = str(int(message.content.split()[1]))
      if uid in config["wk-tokens"]:
        del config["wk-tokens"][uid]
        save()
        await message.add_reaction("✅")
    elif message.content == "wk.kill":
      exit(0)

def htt(h):
  if h == 0:
    return "12 AM"
  if h < 12:
    return f"{h} AM"
  if h == 12:
    return "12 PM"
  return f"{h - 12} PM"

def pluralize(n, x):
  return f"{x} {n}{'s' * (x != 1)}"

class Snowflake:
  def __init__(self, id):
    self.id = id

async def remind(channel, toping = True, force = False):
  hour = datetime.datetime.now().hour
  if not force:
    if hour == 2:
      await channel.send(embed = discord.Embed(description = "(Bot is going to sleep after this update. See you at 8 AM!)"))
    elif hour == 8:
      await channel.send(embed = discord.Embed(description = "（おはようございます！）"))
    elif 3 <= hour <= 7:
      return
  else:
    if 2 <= hour <= 8:
      await channel.send(embed = discord.Embed(description = "(Bot is currently asleep, but I will force an update message anyway.)"))
  members = sorted([(member.id, config["wk-tokens"][str(member.id)]) for member in channel.members if str(member.id) in config["wk-tokens"]])
  if not members:
    return
  next_assn = []
  pings = []
  failed = []
  for member, token in members:
    response = requests.get("https://api.wanikani.com/v2/assignments?in_review", headers = {"Authorization": "Bearer " + token})
    ping = 0
    fail = False
    nxtt = 0
    nxtc = 0
    if response.status_code == 200:
      try:
        for assn in response.json()["data"]:
          ts = datetime.datetime.fromisoformat(assn["data"]["available_at"][:-1]).timestamp() + config['tz'] * 3600
          if ts <= time.time():
            ping += 1
          else:
            if nxtt == 0 or nxtt > ts:
              nxtt = ts
              nxtc = 1
            elif nxtt == ts:
              nxtc += 1
      except:
        raise
        fail = True
    else:
      fail = True
    if ping:
      pings.append((member, ping))
    if fail:
      failed.append(member)
    if nxtt:
      next_assn.append((member, nxtt, nxtc))
  if not pings:
    async for M in channel.history(limit = 1):
      if M.id == config["mine"].get(str(channel.id)):
        return
  msg = await channel.send(", ".join(f"<@{x}> ({y})" for x, y in pings) + ": you have reviews to complete right now." if pings else "", embed = discord.Embed(
    title = "Upcoming Reviews",
    description = "\n".join(f"<@{x}> - {htt(datetime.datetime.fromtimestamp(ts).hour)} (in {pluralize('hour', int((ts - time.time()) / 3600 + 0.5))}) ({pluralize('review', c)})" for x, ts, c in next_assn) or "(there is nothing to see here...)"
  ), allowed_mentions = discord.AllowedMentions(users = [Snowflake(x) for x, y in pings if x not in config["noping"]]) if toping else discord.AllowedMentions.none())
  if failed:
    msg = await channel.send(", ".join(f"<@{x}>" for x in failed) + ": fetching your data failed. Please make sure your token is valid. If you have checked that, please contact an administrator.")
  config["mine"][str(channel.id)] = msg.id
  save()

async def reminder_cycle():
  while True:
    await asyncio.sleep(-time.time() % 3600)
    for chid in config["wk-channels"]:
      try:
        channel = client.get_channel(int(chid))
      except:
        print("Failed to get channel:", chid)
      await remind(channel)
    await asyncio.sleep(10)

client = RSClient()

asyncio.get_event_loop().run_until_complete(asyncio.gather(
  client.start(config["discord-token"]),
  reminder_cycle()
))