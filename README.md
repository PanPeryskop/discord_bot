# Discord Bot

## Table of Contents

- [Description](#description)
- [Features](#features)
- [Installation](#installation)
- [Commands](#commands)


## Description

**Bao Bao Long** is a Discord bot that lets users play music in voice channels without any trouble. The bot can stream music from [YouTube](https://youtube.com) and [Spotify](https://spotify.com), [SoundCoud]('https://soundcloud.com') , play audio files uploaded by users, and has other interactive features.

## Features

- **Music Playback**: Play music from YouTube and Spotify links.
- **Queue Management**: Add songs to a queue, view the current queue, and clear it.
- **Random Playback**: Play random songs.
- **Playlist Support**: Add entire playlists to the queue. (Spotify)
- **User Audio Files**: Play audio files that users upload via private messages.
- **Administrative Controls**: Manage the bot using specific commands. (Deleting provided number os messages from voice channel and downloading all attachments from channel)
- **Talk With Bot**: You can talk with KNUR!

## Installation

1. **Clone the Repository:**
    ```bash
    git clone https://github.com/PanPeryskop/discord_bot
    cd discord_bot
    ```

2. **Create a Virtual Environment (Optional but Recommended):**
    ```bash
    python -m venv .venv
    .venv\Scripts\activate 
    ```

3. **Install Required Python Packages:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Set Up Environment Variables:**
    - Create a ```.env``` file in the root directory of the project.
    - Add the following variables:
        ```env
        SPOTIPY_CLIENT_ID=your_spotify_client_id
        SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
        TOKEN=your_discord_bot_token
        GOOGLE_API_KEY=your_google_api_key
        ```
    - **SPOTIPY_CLIENT_ID**: Your Spotify Client ID.
    - **SPOTIPY_CLIENT_SECRET**: Your Spotify Client Secret.
    - **TOKEN**: Your Discord Bot Token.
    - **GOOGLE_API_KEY**: Your Google API Key for generative services.

5. **Run the Bot:**
    ```bash
    python main.py
    ```

6. Ensure all dependencies listed in [requirements.txt](https://github.com/PanPeryskop/discord_bot/blob/main/requirements.txt) are installed. If you introduce new features or dependencies, update this file accordingly:
```bash
pip install -r requirements.txt
```

## Commands

1. **/toqueue**: Add a song to the queue.
2. **/clearqueue**: Clear the song queue.
3. **/play**: Play a song from a URL.
4. **/skip**: Skip the current song.
5. **/disconnect**: Stop the song and disconnect from the voice channel.
6. **/checkqueue**: Check the number of songs in the queue.
7. **/showqueue**: Show the list of songs in the queue.
8. **/chat**: Chat with the bot.
9. **/add_playlist**: Add a Spotify playlist to the queue.
10. **/ficzur**: Play two songs simultaneously.
11. **/play_my**: Play a user's uploaded audio file.
12. **/play_random**: Play randomly generated songs.
13. **/stop_random**: Stop random music playback.
14. **/theme**: Play a theme from a predefined list.
15. **/stop_theme**: Stop the current theme and clear the theme queue.
16. **/stop**: Stop all music playback.
17. **/download_channel**: Download all attachments from the channel.
18. **/delete_messages**: Delete a specified number of messages from the channel.