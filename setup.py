import json

print("Welcome to the Turtle Bot Setup Script!")
print("This is a bot for reminders for WaniKani. It allows hourly updates, checking progress and updates, and reporting on people's progress automatically.")
print("=======================================")

print("Please enter your discord bot token. You can find this on https://discord.com/developers/applications by clicking your application, navigating to the Bot tab on the left, and clicking \"Copy\" under the Token section. KEEP YOUR TOKEN PRIVATE - with this token, someone can do whatever they want with this bot. If Discord detects your token online it will automatically suspend your bot, but you must be careful with it.")
token = input("token> ")

print()
print("Please enter your own user ID. You can find this by right clicking yourself and clicking \"Copy ID\" if Developer Mode is enabled (under User Settings > Advanced). You don't need to keep this private; anyone can see it.")
while True:
  owner = input("uid> ")
  try:
    owner = int(owner)
  except:
    continue
  break

print("Generating config.json...")

config = {
  "discord-token": token,
  "owner": owner,
  "server-settings": {
    
  },
  "user-settings": {
    
  },
  "channels": [
  
  ]
}

print("Saving file...")

with open("config.json", "w") as f:
  json.dump(config, f)

print("Done!")