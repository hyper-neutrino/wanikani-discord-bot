import asyncio, datetime, discord, json, re, requests, time, traceback

config = {}

def load():
  global config
  with open("config.json", "r") as f:
    config = json.load(f)

def save():
  with open("config.json", "w") as f:
    json.dump(config, f)

def server_settings(gid):
  gid = str(gid)
  if gid not in config["server-settings"]:
    config["server-settings"][gid] = {}
  settings = config["server-settings"][gid]
  if "prefix" not in settings:
    settings["prefix"] = "wk."
  save()
  return settings

def member_settings(mid):
  mid = str(mid)
  if mid not in config["user-settings"]:
    config["user-settings"][mid] = {}
  settings = config["user-settings"][mid]
  if "timezone" not in settings:
    settings["timezone"] = None
  if "hours" not in settings:
    settings["hours"] = list(range(24))
  if "ping" not in settings:
    settings["ping"] = []
  if "pause" not in settings:
    settings["pause"] = False
  if "token" not in settings:
    settings["token"] = ""
  save()
  return settings

def fmt_message(key, val):
  if key == "msg-review-reminder":
    return f"embed header for review reminders is `{val}`"
  elif key == "msg-review-upcoming":
    return f"embed header for upcoming reviews is `{val}`"
  elif key == "msg-lesson-available":
    return f"embed header for available lessons is `{val}`"
  elif key == "msg-failed-fetch":
    return f"message for failed API calls is (`@user - `) `{val}`"
  elif key == "msg-review-stalker":
    return f"message for stalking reviews is (`@user`) `{val}`"
  elif key == "msg-lesson-stalker":
    return f"message for stalking lessons is (`@user`) `{val}`"
  else:
    raise RuntimeError(f"Unknown format message key: {key}")

def is_owner(user):
  return user.id == config["owner"]

def is_admin(member):
  return member.guild_permissions.administrator

async def send_embed(channel, message):
  return await channel.send(embed = discord.Embed(description = message))

class TTBClient(discord.Client):
  def __init__(self):
    discord.Client.__init__(self, intents = discord.Intents.all())

  async def on_ready(self):
    print("Turtle Bot has started.")
  
  async def on_message(self, message):
    if message.author.id == client.user.id: return
    ss = server_settings(message.guild.id) if message.guild else None
    ms = member_settings(message.author.id)
    prefix = ss["prefix"]
    async def reply(msg): return await send_embed(message.channel, msg)
    async def ensure_admin():
      if not is_admin(message.author):
        await reply("This command is limited to server administrators.")
        return True
    if client.user in message.mentions:
      await reply(f"My prefix in this server is `{prefix}` - use `{prefix}help` for a list of commands.")
    elif message.content == "wk.shutdown":
      if is_owner(message.author):
        await reply("Shutting down immediately.")
        raise SystemExit
      else:
        await reply("This command is limited to the bot owner.")
    elif message.content.startswith("wk.default-tz"):
      if is_owner(message.author):
        try:
          tz = int(message.content.split(" ")[1])
          if tz < -12 or tz > 14: raise RuntimeError
          config["default-tz"] = tz
          await reply("Set the default tiemzone for this bot.")
        except:
          await reply("Please enter an integer between -12 and 14.")
      else:
        await reply("This command is limited to the bot owner.")
    elif message.content.startswith(prefix + "prefix"):
      if await ensure_admin(): return
      arguments = message.content.split()
      if len(arguments) == 1:
        np = "wk."
      else:
        np = arguments[1]
      ss["prefix"] = np
      save()
      await reply(f"My prefix in this server is now `{np}`")
    elif message.content.startswith(prefix + "timezone") or message.content.startswith(prefix + "tz"):
      msg = lambda tz: f"(it is currently `{datetime.datetime.now(datetime.timezone(datetime.timedelta(hours = tz))).strftime('%H:%M:%S')}`)."
      tz = (message.content.split(" ", 1)[1:] or [""])[0]
      if tz == "":
        tz = ms["timezone"]
        if tz is None:
          tz = config["default-tz"]
        await reply("Your timezone is `UTC" + "+" * (tz >= 0) + str(tz).zfill(2) + ":00` " + msg(tz))
      elif tz == "-":
        ms["timezone"] = None
        save()
        await reply("Your timezone has been unset and you are now using the default timezone of `UTC" + "+" * (config["default-tz"] >= 0) + str(config["default-tz"]).zfill(2) + ":00` " + msg(config["default-tz"]))
      else:
        try:
          tz = int(tz)
          if tz < -12 or tz > 14: raise RuntimeError
          ms["timezone"] = int(tz)
          save()
          await reply("Your timezone has been updated to `UTC" + "+" * (tz >= 0) + str(tz).zfill(2) + ":00` " + msg(tz))
        except:
          await reply("Please enter an integer between -12 and 14.")
    elif message.content == prefix + "watch":
      if await ensure_admin(): return
      if message.channel.id in config["channels"]:
        await reply("This channel is already receiving hourly reports.")
      else:
        config["channels"].append(message.channel.id)
        save()
        await reply("I will now send hourly reports to this channel (also, immediately sending one now).")
        await update(message.channel, True)
    elif message.content == prefix + "unwatch":
      if await ensure_admin(): return
      if message.channel.id in config["channels"]:
        config["channels"].remove(message.channel.id)
        save()
        await reply("I will no longer send hourly reports to this channel.")
      else:
        await reply("I am not currently sending hourly reports to this channel.")
    elif message.content.startswith(prefix + "include") or message.content.startswith(prefix + "exclude"):
      cmd = message.content[len(prefix):][:7]
      if len(message.content.split(" ")) == 1 or not re.match(r"\d+(-\d+)?", message.content.split(" ")[1]):
        await reply(f"Syntax: `{prefix}{cmd} #` or `{prefix}{cmd} #-#`")
      else:
        x = list(map(int, message.content.split(" ")[1].split("-")))
        if any(k < 0 or k > 23 for k in x):
          await reply("Please enter hours between 0 and 23.")
        else:
          hours = x if len(x) == 1 else list(range(x[0], x[1] + 1)) if x[1] >= x[0] else list(range(x[0], 24)) + list(range(x[1] + 1))
          if cmd == "include":
            for h in hours:
              if h not in ms["hours"]:
                ms["hours"].append(h)
          else:
            for h in hours:
              if h in ms["hours"]:
                ms["hours"].remove(h)
          save()
          await reply("Updated your reminder hours:\n\n```00 01 02 03 04 05 06 07 08 09 10 11\n%s\n12 13 14 15 16 17 18 19 20 21 22 23\n%s\n```" % tuple("  ".join("*" if h in ms["hours"] else " " for h in  x) for x in [range(12), range(12, 24)]))
    elif message.content.startswith(prefix + "hours"):
      await reply("Your current reminder hours are:\n\n```00 01 02 03 04 05 06 07 08 09 10 11\n%s\n12 13 14 15 16 17 18 19 20 21 22 23\n%s\n```" % tuple("  ".join("*" if h in ms["hours"] else " " for h in  x) for x in [range(12), range(12, 24)]))
    elif message.content == prefix + "ping":
      if message.channel.id not in ms["ping"]:
        ms["ping"].append(message.channel.id)
        save()
      await reply("I will now ping you when I post hourly reports to this channel.")
    elif message.content == prefix + "noping":
      if message.channel.id in ms["ping"]:
        ms["ping"].remove(message.channel.id)
        save()
      await reply("I will no longer ping you when I post hourly reports to this channel.")
    elif message.content.startswith(prefix + "token"):
      if len(message.content.split(" ")) == 1 or not re.match("", message.content.split(" ")[1]):
        await reply(f"Syntax: `{prefix}token xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`")
      else:
        ms["token"] = message.content.split(" ")[1]
        save()
        try:
          await message.delete()
        except:
          pass
        await (await reply(f"Saved your API token. It is good practice to use a different token for every application. Use `{prefix}purgetoken` to remove your token.")).delete(delay = 6)
    elif message.content.startswith(prefix + "purgetoken"):
      ms["token"] = ""
      save()
      await reply("Purged your API token. It is still recommended to expire your token if you do not trust this application.")
    elif message.content == prefix + "pause":
      ms["pause"] = True
      save()
      await reply("Paused notifications for you in all places.")
    elif message.content == prefix + "resume":
      ms["pause"] = False
      save()
      await reply("Resumed your notifications.")
    elif message.content == prefix + "update":
      await update(message.channel, True)
    elif message.content == prefix + "help":
      await message.channel.send(embed = discord.Embed().add_field(inline = False, name = "Administrator Commands", value = """```
$prefix          - change my prefix in this server
$watch           - post hourly updates in this channel
$unwatch         - stop updates in this channel
```""".replace("$", prefix)).add_field(inline = False, name = "User Commands", value = """```
$timezone        - set your timezone
$tz              - ^
$include x | x-y - include hours for pinging you
$exclude x | x-y - exclude hours for pinging you
$hours           - check hours for which I will ping you
$ping            - ping you in this channel
$noping          - stop pinging you in this channel
$token           - set your API token
$purgetoken      - remove your API token
$pause           - pause your notification pings GLOBALLY
$resume          - resume your notification pings
$update          - send an update (no pings)
$help            - display this message
```""".replace("$", prefix)))

async def update(channel, manual = False):
  now = datetime.datetime.utcnow().timestamp()
  review_now = []
  lesson_now = []
  review_fcs = []
  pings = []
  for member in channel.members:
    ms = member_settings(member.id)
    td = datetime.timedelta(hours = ms["timezone"] if ms["timezone"] is not None else config["default-tz"])
    if ms["token"]:
      res = requests.get("https://api.wanikani.com/v2/summary", headers = {
        "Authorization": f"Bearer {ms['token']}"
      })
      if res.status_code != 200:
        if member.dm_channel is None:
          await member.create_dm()
        ms["token"] = ""
        save()
        await member.dm_channel.send("Fetching your WaniKani data failed. I have removed your token for now. Please make sure your token is valid and that you did not expire it, and re-enter a token (it can be the same one as before). If this issue persists, please contact HyperNeutrino#9467.")
      else:
        data = res.json()["data"]
        lesson_count = sum(len(block["subject_ids"]) for block in data["lessons"])
        review_timer = datetime.datetime.fromisoformat(data["next_reviews_at"][:-1]).timestamp() if data["next_reviews_at"] else 0
        review_count = 0
        review_frcst = 0
        for block in data["reviews"]:
          timestamp = datetime.datetime.fromisoformat(block["available_at"][:-1]).timestamp()
          if timestamp <= now:
            review_count += len(block["subject_ids"])
          elif timestamp == review_timer:
            review_frcst += len(block["subject_ids"])
        if not manual and not ms["pause"] and channel.id in ms["ping"] and (lesson_count + review_count > 0) and (datetime.datetime.utcnow() + td).hour in ms["hours"]:
          pings.append(member)
        if review_count:
          review_now.append(f"{member.mention} - {review_count}")
        if lesson_count:
          lesson_now.append(f"{member.mention} - {lesson_count}")
        if review_frcst:
          dh, dm = divmod(int((review_timer - now) // 60 + 0.5), 60)
          review_fcs.append(f"{member.mention} - {review_frcst} at {(datetime.datetime.fromtimestamp(review_timer) + td).strftime('%H:%M')} (in {dh:0>2}:{dm:0>2})")
  if not manual and review_now + lesson_now + review_fcs == []:
    return
  embed = discord.Embed(title = "Manual Report" if manual else "Hourly Report")
  anystuff = False
  if review_now:
    embed.add_field(name = "Available Reviews", value = "\n".join(review_now), inline = False)
    anystuff = True
  if lesson_now:
    embed.add_field(name = "Available Lessons", value = "\n".join(lesson_now), inline = False)
    anystuff = True
  if review_fcs:
    embed.add_field(name = "Upcoming Reviews", value = "\n".join(review_fcs), inline = False)
    anystuff = True
  if not anystuff:
    embed.add_field(name = "Nothing to see here...", value = "There are no members in this channel who have any lessons or reviews available or reviews in the next 24 hours.")
  await channel.send(" ".join(member.mention for member in pings), embed = embed)

async def reminder_cycle():
  while True:
    await asyncio.sleep(-time.time() % 3600)
    for cid in config["channels"]:
      try:
        await update(client.get_channel(cid))
      except:
        s = f"ERROR UPDATING CHANNEL {cid}"
        print(s)
        print("v" * len(s))
        traceback.print_exc()
        print("^" * len(s))
    await asyncio.sleep(10)

if __name__ == "__main__":
  load()

  client = TTBClient()
  
  asyncio.get_event_loop().run_until_complete(asyncio.gather(
    client.start(config["discord-token"]),
    reminder_cycle()
  ))