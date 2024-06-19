
# Bao Bao Long

## Description

This is a Discord bot that allows users to play audio files in a voice channel. It supports playing audio files from YouTube and Spotify URLs, as well as user-uploaded audio files and some ficzurs.

## Installation

1. Clone this repository to your local machine.
2. Install the required Python packages by running `pip install -r requirements.txt` in your terminal.
3. Create a `.env` file in the root directory of the project, and add your Discord bot token, Spotify client ID, and Spotify client secret.

```env
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
TOKEN=your_discord_bot_token
```

4. Replace `your_spotify_client_id`, `your_spotify_client_secret`, and `your_discord_bot_token` with your actual Spotify client ID, Spotify client secret, and Discord bot token.

## Usage

1. Run the bot by executing `python main.py` in your terminal.

## Commands

1. `/toqueue`: Adds a song to the queue.
2. `/clearqueue`: Clears the song queue.
3. `/play`: Plays a song. If another song is currently playing, it will be stopped.
4. `/skip`: Stops the current song or skips to the next one.
5. `/disconnect`: Stops the song and disconnects the bot from the voice channel.
6. `/checkqueue`: Displays the number of songs in the queue.
7. `/help`: Displays all available commands and their descriptions.
8. `/trigger`: Mutes a user for a random time (indefinitely).
9. `/chat`: Chat with the bot.
10. `/add_playlist`: Adds a playlist to the queue.
11. `/showqueue`: Shows the song queue.
12. `/ficzur`: Ficzurin'.
13. `/play_my`: Plays a user's audio file. (Song needs to be send to bot in private message)

Remember to use these commands with the appropriate parameters where necessary.
