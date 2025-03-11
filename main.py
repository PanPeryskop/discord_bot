import os
import logging
from discord import app_commands, FFmpegPCMAudio
import discord
import asyncio
import random
import requests
from youtubesearchpython import VideosSearch
import yt_dlp as youtube_dl
import librosa
import soundfile as sf
import numpy as np
from dotenv import load_dotenv
import spotipy
from spotipy import SpotifyOAuth
from urllib.parse import quote
import google.generativeai as genai
from datetime import datetime
from genres import Genres
import aiohttp
import re
from datetime import datetime
from audio_gen import AudioGenerator

# logging.disable(logging.ERROR)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
TOKEN = os.getenv('TOKEN')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

conversation_memory = {}

client_id = SPOTIPY_CLIENT_ID
client_secret = SPOTIPY_CLIENT_SECRET
redirect_uri = 'http://localhost:3000/'

scope = 'playlist-read-private user-modify-playback-state playlist-modify-public playlist-modify-private user-top-read'
auth_manager = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope=scope
)
sp = spotipy.Spotify(auth_manager=auth_manager)

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

class ServerState:
    def __init__(self):
        self.song_queue = []
        self.theme_queue = []
        self.is_theme_playing = False
        self.is_random_playing = False
        self.voice_client = None
        self.last_audio_file = None

server_states = {}

def get_server_state(guild_id):
    if guild_id not in server_states:
        server_states[guild_id] = ServerState()
    return server_states[guild_id]

generator = AudioGenerator()

async def guild_only(interaction: discord.Interaction) -> bool:
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used in servers!", ephemeral=True)
        return False
    return True

@tree.command(name='talk_with_knur', description='Chat with Knur🐗!')
async def talk_with_knur(interaction: discord.Interaction, message: str):
    user_id = str(interaction.user.id)
    try:
        await interaction.response.defer()

        if user_id not in conversation_memory:
            conversation_memory[user_id] = model.start_chat(history=[])
            conversation_memory[user_id].send_message(
                "You are a mighty wild boar named Knur. You speak in a bold, powerful way. "
                "Your music taste is eclectic, you enjoy a wide range of genres."
                "You often use phrases like 'OINK!', 'GRUNT!', when speaking polish you use 'Chrum!' 'RAAAAUUUUR!'. "
                "You're proud, strong and sometimes sarcastic. Keep responses under 2000 characters."
                "You're extremely offensive and will not hesitate to insult anyone. "
                "You love recommending music."
                "If chat is in polish speak in polish, if in english speak in english. If in polish speak 'CHRUM!' instead of 'GRUNT!'"
            )

        response = conversation_memory[user_id].send_message(message)
        formatted_response = f"🐗 {response.text}"

        if len(formatted_response) > 2000:
            parts = [formatted_response[i:i+1999] for i in range(0, len(formatted_response), 1999)]
            for part in parts:
                await interaction.followup.send(part)
        else:
            await interaction.followup.send(formatted_response)

    except Exception as e:
        logger.error(f"Error in talk_with_knur: {e}")
        await interaction.followup.send("🐗 *GRUNT* Something went wrong...")

def download_audio(url, filename):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'audios/{filename}.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        logger.error(f"Error downloading audio: {e}")

def spot_to_yt(url):
    try:
        if url.startswith('https://open.spotify.com/track/'):
            track_id = url.split('/')[-1].split('?')[0] if '?' in url else url.split('/')[-1]
            track_info = sp.track(track_id)
            track_name = track_info['name']
            artist_name = track_info['artists'][0]['name']
            search_query = f"{track_name} {artist_name}"
            print(f'Searching for: {search_query}')

            encoded_query = quote(search_query)
            search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
            response = requests.get(search_url)

            video_id = None
            if "watch?v=" in response.text:
                start_idx = response.text.index("watch?v=") + 8
                video_id = response.text[start_idx:start_idx+11]

            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}"
            else:
                try:
                    videos_search = VideosSearch(search_query, limit=1)
                    results = videos_search.result()
                    if results and 'result' in results and results['result']:
                        return results['result'][0]['link']
                except:
                    logger.error("Both search methods failed")
                    return None
    except Exception as e:
        logger.error(f"Error converting Spotify to YouTube: {e}")
    return None

@tree.command(name='add_playlist', description='To add a Spotify playlist to the queue')
async def add_playlist(interaction: discord.Interaction, url: str):
    if not await guild_only(interaction):
        return
    await interaction.response.send_message('Processing your request...')
    await _add_playlist(interaction, url)

async def _add_playlist(interaction: discord.Interaction, url: str):
    state = get_server_state(interaction.guild.id)
    song_queue = state.song_queue
    try:
        if url.startswith('https://open.spotify.com/playlist/'):
            playlist_id = url.split('/')[-1].split('?')[0] if '?' in url else url.split('/')[-1]
            results = sp.playlist_tracks(playlist_id)
            for item in results['items']:
                song = item['track']
                song_url = 'https://open.spotify.com/track/' + song['id']
                song_queue.append(song_url)
            await interaction.followup.send('Songs from playlist added to queue.')

            guild = interaction.guild
            voice_channel = guild.voice_client
            if not voice_channel or not voice_channel.is_playing():
                await _play_next(interaction, has_deferred=True)
        else:
            await interaction.followup.send('Invalid URL. Please provide a valid Spotify playlist URL.')
    except Exception as e:
        logger.error(f"Error adding playlist: {e}")
        await interaction.followup.send('An error occurred while processing your request.')

@tree.command(name='toqueue', description='To add song to queue')
async def toqueue(interaction: discord.Interaction, url: str):
    if not await guild_only(interaction):
        return
    state = get_server_state(interaction.guild.id)
    state.song_queue.append(url)
    logger.info(f"Song added to queue: {url}")
    await interaction.response.send_message('Song added to queue.')

@tree.command(name='clearqueue', description='To clear the song queue')
async def clearqueue(interaction: discord.Interaction):
    if not await guild_only(interaction):
        return
    state = get_server_state(interaction.guild.id)
    state.song_queue.clear()
    await interaction.response.send_message('Song queue cleared.')

async def _play_next(interaction: discord.Interaction, has_deferred: bool = True) -> None:
    state = get_server_state(interaction.guild.id)
    song_queue = state.song_queue
    if song_queue:
        url = song_queue.pop(0)
        await _play(interaction, url, has_deferred=has_deferred)

async def _play(interaction: discord.Interaction, url: str, has_deferred: bool = False) -> None:
    if not await guild_only(interaction):
        return

    state = get_server_state(interaction.guild.id)
    song_queue = state.song_queue

    if not has_deferred:
        await interaction.response.defer()

    guild = interaction.guild
    member = guild.get_member(interaction.user.id)
    channel = member.voice.channel

    if guild.voice_client is None:
        voice_channel = await channel.connect()
        state.voice_client = voice_channel
    else:
        voice_channel = guild.voice_client
        state.voice_client = voice_channel
        if voice_channel.is_playing():
            song_queue.append(url)
            await interaction.followup.send('Song added to queue.')
            return

    try:
        if 'playlist' in url:
            await _add_playlist(interaction, url)
            return

        if url.startswith(('https://www.youtube.com/watch?v=', 'https://youtu.be/', 'https://soundcloud.com/')):
            download_audio(url, 'temp_audio')
            audio_file = 'audios/temp_audio.mp3'
            song_name = get_song_name(url)
            voice_channel.play(
                discord.FFmpegPCMAudio(audio_file),
                after=lambda e: client.loop.create_task(_play_next(interaction, True))
            )
            voice_channel.source = discord.PCMVolumeTransformer(voice_channel.source, 0.5)
            await interaction.followup.send(f'Playing: {song_name}')

        elif url.startswith('https://open.spotify.com/track/'):
            yt_url = spot_to_yt(url)
            if yt_url:
                download_audio(yt_url, 'temp_audio')
                audio_file = 'audios/temp_audio.mp3'
                song_name = get_song_name(yt_url)
                voice_channel.play(
                    discord.FFmpegPCMAudio(audio_file),
                    after=lambda e: client.loop.create_task(_play_next(interaction, True))
                )
                voice_channel.source = discord.PCMVolumeTransformer(voice_channel.source, 0.5)
                await interaction.followup.send(f'Playing: {song_name}')
            else:
                await interaction.followup.send('Could not find the song on YouTube.')

        elif url.startswith('https://open.spotify.com/playlist/'):
            playlist_id = url.split('/')[-1].split('?')[0] if '?' in url else url.split('/')[-1]
            results = sp.playlist_tracks(playlist_id)
            for item in results['items']:
                song = item['track']
                song_queue.append('https://open.spotify.com/track/' + song['id'])
            current_song = song_queue.pop(0)
            await _play(interaction, current_song, has_deferred=True)
        else:
            await interaction.followup.send('Invalid URL. Please provide a valid track URL.')

    except Exception as e:
        logger.error(f"Error playing song: {e}")
        await interaction.followup.send('An error occurred while processing your request.')

def get_song_name(url):
    if 'youtube' in url or 'youtu.be' in url:
        video_info = VideosSearch(url, limit=1).result()
        return video_info['result'][0]['title']
    elif 'spotify' in url:
        track_id = url.split('/')[-1].split('?')[0] if '?' in url else url.split('/')[-1]
        track_info = sp.track(track_id)
        return f"{track_info['name']} by {track_info['artists'][0]['name']}"
    return 'Unknown'

play_next = tree.command(name='play_next', description='To play next song')(_play_next)
play = tree.command(name='play', description='To play song')(_play)

@tree.command(name='skip', description='To skip song')
async def skip(interaction: discord.Interaction):
    if not await guild_only(interaction):
        return
    guild = interaction.guild
    voice_client = discord.utils.get(client.voice_clients, guild=interaction.guild)
    if voice_client is None:
        await interaction.response.send_message("The bot is not connected to a voice channel.")
    elif not voice_client.is_playing():
        await interaction.response.send_message("The bot is not playing anything at the moment.")
    else:
        voice_client.stop()
        await interaction.response.send_message("Stopped the song.")

@tree.command(name='disconnect', description='To stop song and disconnect from voice channel')
async def disconnect(interaction: discord.Interaction):
    if not await guild_only(interaction):
        return
    state = get_server_state(interaction.guild.id)
    state.song_queue.clear()

    guild = interaction.guild
    if guild.voice_client:
        await interaction.response.send_message('Disconnecting from voice channel.')
        await guild.voice_client.disconnect()
    else:
        await interaction.response.send_message('Not connected to any voice channel.')

@tree.command(name='checkqueue', description='To check the song queue')
async def check_queue(interaction: discord.Interaction):
    if not await guild_only(interaction):
        return
    state = get_server_state(interaction.guild.id)
    if not state.song_queue:
        await interaction.response.send_message('The song queue is empty.')
    else:
        await interaction.response.send_message(f'The song queue has {len(state.song_queue)} songs.')

@tree.command(name='showqueue', description='To show the song queue')
async def show_queue(interaction: discord.Interaction):
    if not await guild_only(interaction):
        return
    state = get_server_state(interaction.guild.id)
    if not state.song_queue:
        await interaction.response.send_message('The song queue is empty.')
    else:
        await interaction.response.send_message('Song queue:')
        for i in range(0, len(state.song_queue), 30):
            message = ''
            for j, song in enumerate(state.song_queue[i:i + 30], start=i + 1):
                message += f'{j}. {song}\n'
            await interaction.followup.send(message)

@tree.command(name='ficzur', description='Ficzuring')
async def ficzur(interaction: discord.Interaction, url1: str, url2: str):
    if not await guild_only(interaction):
        return

    await interaction.response.send_message('Ficzurin\'...')
    guild = interaction.guild
    member = guild.get_member(interaction.user.id)
    channel = member.voice.channel

    if guild.voice_client is None:
        voice_channel = await channel.connect()
        get_server_state(guild.id).voice_client = voice_channel
    else:
        voice_channel = guild.voice_client
        get_server_state(guild.id).voice_client = voice_channel
        if voice_channel.is_playing():
            voice_channel.stop()

    try:
        if not (url1.startswith(('https://www.youtube.com/watch?v=', 'https://open.spotify.com/track/', 'https://soundcloud.com/')) and
                url2.startswith(('https://www.youtube.com/watch?v=', 'https://open.spotify.com/track/', 'https://soundcloud.com/'))):
            await interaction.edit_original_response(content='Invalid URL. Please provide a valid YouTube, SoundCloud, or Spotify track URL.')
            return

        if url1.startswith('https://open.spotify.com/track/'):
            url1 = spot_to_yt(url1)
        if url2.startswith('https://open.spotify.com/track/'):
            url2 = spot_to_yt(url2)

        download_audio(url1, 'temp_audio1')
        download_audio(url2, 'temp_audio2')

        y1, sr1 = librosa.load('audios/temp_audio1.mp3')
        y2, sr2 = librosa.load('audios/temp_audio2.mp3')

        if sr1 != sr2:
            raise ValueError("The two audio files have different sample rates!")

        if len(y1) < len(y2):
            y1 = np.tile(y1, int(np.ceil(len(y2) / len(y1))))
        elif len(y2) < len(y1):
            y2 = np.tile(y2, int(np.ceil(len(y1) / len(y2))))

        y1 = y1[:len(y2)]
        y2 = y2[:len(y1)]

        combined = np.vstack((y1, y2))
        sf.write('audios/ficzur.wav', combined.T, sr1)

        voice_channel.play(discord.FFmpegPCMAudio('audios/ficzur.wav'), after=lambda e: client.loop.create_task(_play_next(interaction)))
        voice_channel.source = discord.PCMVolumeTransformer(voice_channel.source)
        voice_channel.source.volume = 0.5

        await interaction.edit_original_response(content='Playing your song now.')

        while voice_channel.is_playing():
            await asyncio.sleep(1)

        os.remove('audios/temp_audio1.mp3')
        os.remove('audios/temp_audio2.mp3')
        os.remove('audios/ficzur.wav')
    except Exception as e:
        logger.error(f"Error in ficzur: {e}")
        await interaction.edit_original_response(content='An error occurred while processing your request.')


@client.event
async def on_message(message):

    if message.author.bot:
        return

    keywords = ["knur", "knurze"]
    user_id = str(message.author.id)

    if any(keyword in message.content.lower() for keyword in keywords) and message.guild:
        await message.add_reaction('🐗')
        if user_id not in conversation_memory:
            conversation_memory[user_id] = model.start_chat(history=[])
            conversation_memory[user_id].send_message(
                "You are a mighty wild boar named Knur. You speak in a bold, powerful way. "
                "Your music taste is eclectic, you enjoy a wide range of genres."
                "You often use phrases like 'OINK!', 'GRUNT!', when speaking polish you use 'Chrum!' 'RAAAAUUUUR!'. "
                "You're proud, strong and sometimes sarcastic. Keep responses under 2000 characters."
                "You're extremely offensive and will not hesitate to insult anyone. "
                "You love recommending music."
                "If chat is in polish speak in polish, if in english speak in english. If in polish speak 'CHRUM!' instead of 'GRUNT!'"
            )

        response = conversation_memory[user_id].send_message(message.content)
        formatted_response = f"🐗 {response.text}"

        if len(formatted_response) > 2000:
            parts = [formatted_response[i:i + 1999] for i in range(0, len(formatted_response), 1999)]
            for part in parts:
                await message.channel.send(part)
            return
        else:
            await message.channel.send(formatted_response)
            return


    if message.attachments:
        os.makedirs("./songs", exist_ok=True)
        for attachment in message.attachments:
            if attachment.filename.endswith(('.mp3', '.wav')):
                print('Audio file found')
                if attachment.size > 25 * 1024 * 1024:
                    await message.channel.send("File too large! Maximum size is 25MB.")
                    continue
                try:
                    file_path = f"./songs/{attachment.filename}"
                    await attachment.save(file_path)
                    if user_id not in server_states:
                        server_states[user_id] = ServerState()
                    server_states[user_id].last_audio_file = file_path

                    await message.add_reaction('🐗')
                    boar_messages = [
                        f"🐗 Knur has captured **{attachment.filename}**",
                        f"🐗 Knur's mighty ears detected new sound: **{attachment.filename}**!",
                        f"🐗 The Beast has added **{attachment.filename}** to his collection!",
                        f"🐗 Knur has detected new banger: **{attachment.filename}**!"
                    ]
                    await message.channel.send(random.choice(boar_messages))
                    logger.info(f"Saved audio file: {file_path}")
                    break
                except Exception as e:
                    logger.error(f"Failed to save audio file: {e}")
                    await message.channel.send("Failed to save audio file!")
                    await message.add_reaction('❌')

@tree.command(name='play_my', description='Play a user\'s audio file')
async def play_my(interaction: discord.Interaction):
    if not await guild_only(interaction):
        return

    user_id = interaction.user.id
    if user_id not in server_states or not server_states[user_id].last_audio_file:
        await interaction.response.send_message('No audio file found.')
        return

    state = get_server_state(interaction.guild.id)
    guild = interaction.guild
    member = guild.get_member(interaction.user.id)
    channel = member.voice.channel

    if guild.voice_client is None:
        voice_channel = await channel.connect()
        state.voice_client = voice_channel
    else:
        voice_channel = guild.voice_client
        state.voice_client = voice_channel
        if voice_channel.is_playing():
            voice_channel.stop()

    audio_file = server_states[user_id].last_audio_file
    voice_channel.play(discord.FFmpegPCMAudio(audio_file), after=lambda e: client.loop.create_task(_play_next(interaction)))
    voice_channel.source = discord.PCMVolumeTransformer(voice_channel.source)
    voice_channel.source.volume = 0.5
    await interaction.response.send_message('Playing your audio file now.')

@tree.command(name='theme', description='Play a theme from a predefined list')
@app_commands.choices(theme=[
    app_commands.Choice(name='fent', value='fent'),
    app_commands.Choice(name='miodowanie', value='miodowanie'),
    app_commands.Choice(name='speegarage', value='speegarage'),
    app_commands.Choice(name='sebol', value='sebol'),
    app_commands.Choice(name='yabujin', value='yabujin'),
])
async def theme(interaction: discord.Interaction, theme: app_commands.Choice[str]):
    if not await guild_only(interaction):
        return

    state = get_server_state(interaction.guild.id)
    if state.is_theme_playing:
        await interaction.response.send_message('A theme is already playing.')
        return

    state.is_theme_playing = True
    theme_folder = {
        'fent': 'C:/Users/stgad/Music/Fent',
        'miodowanie': 'C:/Users/stgad/Music/Poldon Crusin',
        'speegarage': 'C:/Users/stgad/Music/Speedgarae',
        'sebol': 'C:/Users/stgad/Music/sebol',
        'yabujin': 'C:/Users/stgad/Music/yabujin'
    }
    folder = theme_folder[theme.value]
    songs = [os.path.join(folder, file) for file in os.listdir(folder) if file.endswith('.mp3')]
    random.shuffle(songs)
    state.theme_queue.extend(songs)
    await interaction.response.send_message(f'Added {theme.value} theme songs to the queue.')
    await play_next_theme_song(interaction)

async def play_next_theme_song(interaction):
    state = get_server_state(interaction.guild.id)
    theme_queue = state.theme_queue

    if theme_queue:
        song = theme_queue.pop(0)
        guild = interaction.guild
        member = guild.get_member(interaction.user.id)
        channel = member.voice.channel

        if guild.voice_client is None:
            voice_channel = await channel.connect()
            state.voice_client = voice_channel
            intro_path = {
                1: "C:/Users/stgad/Music/Knur intro/intro 1.mp3",
                2: "C:/Users/stgad/Music/Knur intro/intro 2.mp3",
                3: "C:/Users/stgad/Music/Knur intro/intro 3.mp3"
            }
            if random.random() < 0.33:
                voice_channel.play(discord.FFmpegPCMAudio(intro_path[1]), after=lambda e: client.loop.create_task(play_next_theme_song(interaction)))
            elif random.random() < 0.66:
                voice_channel.play(discord.FFmpegPCMAudio(intro_path[2]), after=lambda e: client.loop.create_task(play_next_theme_song(interaction)))
            else:
                voice_channel.play(discord.FFmpegPCMAudio(intro_path[3]), after=lambda e: client.loop.create_task(play_next_theme_song(interaction)))
        else:
            voice_channel = guild.voice_client
            state.voice_client = voice_channel
            if voice_channel.is_playing():
                voice_channel.stop()

        voice_channel.play(discord.FFmpegPCMAudio(song), after=lambda e: client.loop.create_task(play_next_theme_song(interaction)))
        voice_channel.source = discord.PCMVolumeTransformer(voice_channel.source)
        voice_channel.source.volume = 0.5
    else:
        state.is_theme_playing = False

@tree.command(name='stop_theme', description='Stop the current theme and clear the theme queue')
async def stop_theme(interaction: discord.Interaction):
    if not await guild_only(interaction):
        return
    state = get_server_state(interaction.guild.id)
    guild = interaction.guild
    voice_client = discord.utils.get(client.voice_clients, guild=interaction.guild)

    state.theme_queue.clear()
    if voice_client and voice_client.is_playing():
        voice_client.stop()
    state.is_theme_playing = False
    await interaction.response.send_message('Stopped the theme and cleared the theme queue.')

@tree.command(name='stop', description='Stop all')
async def stop(interaction: discord.Interaction):
    if not await guild_only(interaction):
        return
    state = get_server_state(interaction.guild.id)
    guild = interaction.guild
    voice_client = discord.utils.get(client.voice_clients, guild=interaction.guild)

    if voice_client and voice_client.is_playing():
        voice_client.stop()
    state.song_queue.clear()
    await interaction.response.send_message('Stopped all.')

@client.event
async def on_ready():
    for guild in client.guilds:
        logger.info(f'{client.user} has connected to {guild.name}!')
        await tree.sync()
    logger.info("Ready!")

@tree.command(name='play_random', description='Play randomly generated songs')
async def play_random(interaction: discord.Interaction):
    if not await guild_only(interaction):
        return

    state = get_server_state(interaction.guild.id)
    if state.is_random_playing:
        await interaction.response.send_message('Random music is already playing.')
        return

    state.is_random_playing = True
    await play_next_random(interaction)
    await interaction.response.send_message('Starting random music playback.')

async def play_next_random(interaction):
    state = get_server_state(interaction.guild.id)
    if not state.is_random_playing:
        return

    try:
        genres = Genres(sp)
        track_url = genres.get_song()
        if track_url:
            guild = interaction.guild
            track_url = track_url.replace('spotify:track:', 'https://open.spotify.com/track/')
            yt_url = spot_to_yt(track_url)
            if yt_url:
                download_audio(yt_url, 'temp_audio')
                audio_file = 'audios/temp_audio.mp3'
                song_name = get_song_name(yt_url)

                if guild.voice_client is None:
                    member = guild.get_member(interaction.user.id)
                    channel = member.voice.channel
                    voice_client = await channel.connect()
                    state.voice_client = voice_client
                else:
                    voice_client = guild.voice_client
                    state.voice_client = voice_client
                    if voice_client.is_playing():
                        voice_client.stop()

                voice_client.play(
                    discord.FFmpegPCMAudio(audio_file),
                    after=lambda e: asyncio.run_coroutine_threadsafe(play_next_random(interaction), client.loop)
                )
                voice_client.source = discord.PCMVolumeTransformer(voice_client.source, 0.5)

                try:
                    await interaction.channel.send(f'Now playing: {song_name}')
                except:
                    pass

    except Exception as e:
        logger.error(f"Error in play_next_random: {e}")
        state.is_random_playing = False

@tree.command(name='stop_random', description='Stop random music playback')
async def stop_random(interaction: discord.Interaction):
    if not await guild_only(interaction):
        return
    state = get_server_state(interaction.guild.id)
    guild = interaction.guild
    voice_client = discord.utils.get(client.voice_clients, guild=interaction.guild)

    if voice_client and voice_client.is_playing():
        voice_client.stop()
    state.is_random_playing = False
    await interaction.response.send_message('Stopped random music playback.')

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

@tree.command(name='download_channel', description='Download all attachments from channel')
async def download_attachments(interaction: discord.Interaction):
    if not await guild_only(interaction):
        return

    if not interaction.user.guild_permissions.administrator and not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
        return

    await interaction.response.defer()
    today = datetime.now().strftime('%Y-%m-%d')
    server_name = sanitize_filename(interaction.guild.name)
    channel_name = sanitize_filename(interaction.channel.name)

    downloads_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'downloads',
        server_name,
        channel_name,
        today
    )

    if not os.path.exists(downloads_dir):
        os.makedirs(downloads_dir)

    channel = interaction.channel
    downloaded = 0
    failed = 0
    total_attachments = 0

    async for message in channel.history(limit=None):
        total_attachments += len(message.attachments)

    if total_attachments == 0:
        await interaction.followup.send("No attachments found in this channel!")
        return

    status_message = await interaction.followup.send(f'Starting download of {total_attachments} attachments...')

    async with aiohttp.ClientSession() as session:
        async for message in channel.history(limit=None):
            for attachment in message.attachments:
                try:
                    filename = os.path.join(downloads_dir, sanitize_filename(attachment.filename))
                    async with session.get(attachment.url) as resp:
                        if resp.status == 200:
                            with open(filename, 'wb') as f:
                                f.write(await resp.read())
                            downloaded += 1
                            if downloaded % 10 == 0:
                                await status_message.edit(content=f'Progress: {downloaded}/{total_attachments} files downloaded...')
                        else:
                            failed += 1
                except Exception as e:
                    logger.error(f"Failed to download {attachment.filename}: {e}")
                    failed += 1

    final_message = (
        f'Download complete!\n'
        f'Location: {downloads_dir}\n'
        f'Successfully downloaded: {downloaded}\n'
        f'Failed: {failed}'
    )
    await status_message.edit(content=final_message)

@tree.command(name='delete_messages', description='Delete provided number of messages from channel')
async def delete_messages(interaction: discord.Interaction, count: int):
    if not await guild_only(interaction):
        return

    if not interaction.user.guild_permissions.administrator and not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
        return

    if count <= 0:
        await interaction.response.send_message("Please provide a positive number of messages to delete.", ephemeral=True)
        return

    await interaction.response.send_message(f"Starting deletion of {count} messages...", ephemeral=True, delete_after=30)
    channel = interaction.channel
    deleted = 0
    failed = 0

    try:
        async for message in channel.history(limit=count):
            try:
                await message.delete()
                deleted += 1
                await asyncio.sleep(0.76)
            except Exception as e:
                logger.error(f"Failed to delete message: {e}")
                failed += 1

        final_message = f"Completed! Deleted {deleted} messages."
        if failed > 0:
            final_message += f" Failed to delete {failed} messages."

        await interaction.channel.send(final_message, delete_after=10)

    except Exception as e:
        logger.error(f"Error in delete_messages: {e}")
        await interaction.channel.send("An error occurred while deleting messages.", delete_after=10)

@tree.command(name='let_knur_cook', description='Let Knur speak or sing!')
@app_commands.choices(mode=[
    app_commands.Choice(name='speak', value='speak'),
    app_commands.Choice(name='sing', value='sing')
])
async def let_knur_cook(interaction: discord.Interaction, mode: app_commands.Choice[str], text: str):
    await interaction.response.defer()
    try:
        filename = f"knur_{mode.value}.wav"
        if mode.value == 'speak':
            audio_path = generator.generate_speech(text, filename)
        else:
            audio_path = generator.generate_singing(text, filename)

        if not audio_path:
            await interaction.followup.send("🐗 Something went wrong...")
            return

        if interaction.guild and interaction.user.voice:
            guild = interaction.guild
            voice_channel = interaction.user.voice.channel
            if guild.voice_client is None:
                voice_client = await voice_channel.connect()
            else:
                voice_client = guild.voice_client
                if not voice_client.is_playing():
                    voice_client.play(discord.FFmpegPCMAudio(audio_path))
                    voice_client.source = discord.PCMVolumeTransformer(voice_client.source)
                    voice_client.source.volume = 0.7

        with open(audio_path, 'rb') as f:
            file = discord.File(f, filename=filename)
            await interaction.followup.send(
                content=f"🐗 Knur is {mode.value}ing: {text}",
                file=file
            )
    except Exception as e:
        logger.error(f"Error in let_knur_cook: {str(e)}")
        await interaction.followup.send("Knur can't cook right now... 🐗")

@tree.command(name='stats', description='Display server stats')
async def stats(interaction: discord.Interaction):
    if not await guild_only(interaction):
        return

    guild = interaction.guild
    num_members = guild.member_count
    created_at = guild.created_at.strftime("%Y-%m-%d %H:%M:%S")

    stats_message = (
        f"Total Members: {num_members}\n"
        f"Created On: {created_at}\n"
    )
    await interaction.response.send_message(stats_message)

@tree.command(name='effect', description='Add sound effect to current song')
@app_commands.choices(effect=[
    app_commands.Choice(name='nightcore', value='nightcore'),
    app_commands.Chocie(name='bass_boost', value='bass_boost'),
    app_commands.Choice(name='cave', value='cave'),
    app_commands.Choice(name='earrape', value='earrape')
])
async def effect(interaction: discord.Interaction, effect:app_commands.Choice[str]):
    if not await guild_only(interaction):
        return
    
    state = get_server_state(interaction.guild.id)
    guild = interaction.guild.id
    voice_client = discord.utils.get(client.voice_clients, guild=guild)

    if voice_client is None or not voice_client.is_playing():
        await interaction.resposne.send_message("Knur is not playing")
        return

    await interaction.response.defer()

    try:
        effect_file= f'audios/effect_{effect.value}.mp3'

        ffmpeg_filters = {
            'nightcore': '-af "asetrate=44100*1.25,aresample=44100,atempo=1.06"',
            'bass_boost': '-af "bass=g=10,dynaudnorm"',
            'cave': '-af "aecho=0.8:0.9:1000|1800:0.3|0.25"',
            'ear_rape': '-af bass=g=20,volume=10'
        }

        current_audio = 'audios/temp.audi.mp3'
        filter_cc = ffmpeg_filters[effect.value]

        os.system(f'ffmpeg -y -i {current_audio} {filter_cc} {effect_file}')

        voice_client.stop()

        voice_client.play(
            discord.FFmpegAudio(effect_file),
            after=lambda e: client.loop.create_task(_play_next(interaction, True))
        )

        voice_client.source = discord.PCMVolumeTranformer(voice_client.source)
        voice_client.source.volume = 0.5

        await interaction.followup.send(f'Applied {effect.value} effect to the current song...')

    except Exception as e:
        logger.error(f"Error applying effect: {e}")
        await interaction.followup.send("An error occured")



client.run(TOKEN)