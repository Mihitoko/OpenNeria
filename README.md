# Neria Bot
Neria is a discord bot that is here to help you organize your lost ark raids and schedules with your guild.

## How to get Neria running
### Install
 - Clone the repository
 - Create a virtual and activate the virtual venv (platform specific)
 - Run `pip install -r requirements.txt`

### Setup
 - Run `python3 `
 - Copy all `.dist.json` files without the dist part so the bot recognises them
 - Add your bot token to `secrets.json`
 - Run the docker container with `docker compose up -d`

### Run the bot
 - Linux/Mac
   - Just run `make`
 - Windows
   - Run `py -3 -m langpy compile`
   - Run `py -3 runner.py`

### Note
The project was originally created as a private project for me to learn more about programming. <br>
I don't really have the time to add anything to add anything to it anymore, so I decided to open source it <br>
Contributions and suggestions are always welcome.
