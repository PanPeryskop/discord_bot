import os
from discord import app_commands, FFmpegPCMAudio
import discord
import asyncio
import random

from youtubesearchpython import VideosSearch

from pytube import YouTube
import librosa
import soundfile as sf
import numpy as np
from dotenv import load_dotenv

import spotipy
from spotipy import SpotifyOAuth

load_dotenv()

SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
TOKEN = os.getenv('TOKEN')

client_id = SPOTIPY_CLIENT_ID
client_secret = SPOTIPY_CLIENT_SECRET
redirect_uri = 'http://localhost:3000/'

scope = 'playlist-read-private user-modify-playback-state playlist-modify-public playlist-modify-private user-top-read'
auth_manager = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri,
                            scope=scope)
sp = spotipy.Spotify(auth_manager=auth_manager)

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

song_queue = []


def spot_to_yt(url):
    if url.startswith('https://open.spotify.com/track/'):
        if '?' in url:
            track_id = url.split('/')[-1].split('?')[0]
        else:
            track_id = url.split('/')[-1]
        track_info = sp.track(track_id)
        track_name = track_info['name']
        artist_name = track_info['artists'][0]['name']

        videos_search = VideosSearch(f'{track_name} {artist_name}', limit=1)
        yt_url = videos_search.result()['result'][0]['link']
        return yt_url
    else:
        return None


@tree.command(name='add_playlist', description='To add a Spotify playlist to the queue')
async def add_playlist(interaction: discord.Interaction, url: str):
    await interaction.response.send_message('Processing your request...')
    if url.startswith('https://open.spotify.com/playlist/'):
        if '?' in url:
            playlist_id = url.split('/')[-1].split('?')[0]
        else:
            playlist_id = url.split('/')[-1]
        results = sp.playlist_tracks(playlist_id)
        for item in results['items']:
            song = item['track']
            song_url = 'https://open.spotify.com/track/' + song['id']
            song_queue.append(song_url)
        await interaction.followup.send('Songs from playlist added to queue.')
    else:
        await interaction.followup.send('Invalid URL. Please provide a valid Spotify playlist URL.')


@tree.command(name='toqueue', description='To add song to queue')
async def toqueue(interaction: discord.Interaction, url: str):
    song_queue.append(url)
    print(song_queue)
    await interaction.response.send_message('Song added to queue.')


@tree.command(name='clearqueue', description='To clear the song queue')
async def clearqueue(interaction: discord.Interaction):
    song_queue.clear()
    await interaction.response.send_message('Song queue cleared.')


async def _play_next(interaction):
    print("Playing next song")
    if len(song_queue) > 0:
        print(f"Playing next song: {song_queue[0]}")
        url = song_queue.pop(0)
        await _play(interaction, url)


async def _play(interaction: discord.Interaction, url: str):
    global is_theme_playing

    if is_theme_playing:
        await interaction.response.send_message('A theme is currently playing. Please wait for it to finish.')
        return
    
    if interaction.response.is_done():
        await interaction.followup.send('Processing your request...')
    else:
        await interaction.response.send_message('Processing your request...')
    guild = interaction.guild
    member = guild.get_member(interaction.user.id)
    channel = member.voice.channel

    if guild.voice_client is None:
        voice_channel = await channel.connect()
    else:
        voice_channel = guild.voice_client
        if voice_channel.is_playing():
            voice_channel.stop()
    if url.startswith('https://www.youtube.com/watch?v='):
        yt = YouTube(url)
        stream = yt.streams.filter(only_audio=True).first()
        stream.download(filename='temp_audio.mp3')

        voice_channel.play(discord.FFmpegPCMAudio('temp_audio.mp3'),
                           after=lambda e: client.loop.create_task(_play_next(interaction)))
        voice_channel.source = discord.PCMVolumeTransformer(voice_channel.source)
        voice_channel.source.volume = 0.5

        await interaction.edit_original_response(content='Playing your song now.')

    elif url.startswith('https://open.spotify.com/track/'):
        if '?' in url:
            track_id = url.split('/')[-1].split('?')[0]
        else:
            track_id = url.split('/')[-1]
        track_info = sp.track(track_id)
        track_name = track_info['name']
        artist_name = track_info['artists'][0]['name']

        videos_search = VideosSearch(f'{track_name} {artist_name}', limit=1)
        yt_url = videos_search.result()['result'][0]['link']
        yt = YouTube(yt_url)

        stream = yt.streams.filter(only_audio=True).first()
        stream.download(filename='temp_audio.mp3')

        voice_channel.play(discord.FFmpegPCMAudio('temp_audio.mp3'),
                           after=lambda e: client.loop.create_task(_play_next(interaction)))
        voice_channel.source = discord.PCMVolumeTransformer(voice_channel.source)
        voice_channel.source.volume = 0.5

        await interaction.edit_original_response(content='Playing your song now.')

    elif url.startswith('https://open.spotify.com/playlist/'):
        if '?' in url:
            playlist_id = url.split('/')[-1].split('?')[0]
        else:
            playlist_id = url.split('/')[-1]
        results = sp.playlist_tracks(playlist_id)
        for item in results['items']:
            song = item['track']
            song_url = 'https://open.spotify.com/track/' + song['id']
            song_queue.append(song_url)
        current_song = song_queue.pop(0)
        await _play(interaction, current_song)
    else:
        await interaction.edit_original_response(content='Invalid URL. Please provide a valid Spotify track URL.')


play_next = tree.command(name='play_next', description='To play next song')(_play_next)
play = tree.command(name='play', description='To play song')(_play)


@tree.command(name='skip', description='To skip song')
async def skip(interaction: discord.Interaction):
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
    guild = interaction.guild

    song_queue.clear()
    await interaction.response.send_message('Disconnecting from voice channel.')
    await interaction.guild.voice_client.disconnect()


@tree.command(name='checkqueue', description='To check the song queue')
async def check_queue(interaction: discord.Interaction):
    if len(song_queue) == 0:
        await interaction.response.send_message('The song queue is empty.')
    else:
        await interaction.response.send_message(f'The song queue has {len(song_queue)} songs.')


@tree.command(name='help', description='Display all available commands and their descriptions')
async def help(interaction: discord.Interaction):
    message = """```
/toqueue: Dodaje utwór do kolejki.
/clearqueue: Czyści kolejkę utworów.  
/play : Odtwarza utwór. Jeśli aktualnie odtwarzany jest inny utwór, zostanie on zatrzymany.
/skip: Zatrzymuje odtwarzanie utworu lub skipuje.  
/disconnect: Zatrzymuje odtwarzanie utworu i rozłącza bota z kanałem głosowym.  
/checkqueue: Wyświetla liczbę utworów w kolejce.  
/help: Wyświetla wszystkie dostępne komendy i ich opisy.
/chat: Rozmawia z botem (llama 2 7b).
/add_playlist: Dodaje playlistę do kolejki.
/showqueue: Pokazuje kolejke utworości.
/ficzur: Ficzurin'.```"""
    await interaction.response.send_message(message)


@tree.command(name='showqueue', description='To show the song queue')
async def show_queue(interaction: discord.Interaction):
    if len(song_queue) == 0:
        await interaction.response.send_message('The song queue is empty.')
    else:
        await interaction.response.send_message('Song queue:')
        for i in range(0, len(song_queue), 30):
            message = ''
            for j, song in enumerate(song_queue[i:i + 30], start=i + 1):
                message += f'{j}. {song}\n'
            await interaction.followup.send(message)


@tree.command(name='ficzur', description='Ficzuring')
async def ficzur(interaction: discord.Interaction, url1: str, url2: str):
    if interaction.response.is_done():
        await interaction.followup.send('Ficzurin\'...')
    else:
        await interaction.response.send_message('Ficzurin\'...')
    guild = interaction.guild
    member = guild.get_member(interaction.user.id)
    channel = member.voice.channel

    if guild.voice_client is None:
        voice_channel = await channel.connect()
    else:
        voice_channel = guild.voice_client
        if voice_channel.is_playing():
            voice_channel.stop()
    if (not url1.startswith('https://www.youtube.com/watch?v=') and not url1.startswith(
            'https://open.spotify.com/track/')) or (
            not url2.startswith('https://www.youtube.com/watch?v=') and not url2.startswith(
            'https://open.spotify.com/track/')):
        await interaction.edit_original_response(
            content='Invalid URL. Please provide a valid YouTube and Spotify track URL.')
        return
    if url1.startswith('https://open.spotify.com/track/'):
        url1 = spot_to_yt(url1)
    if url2.startswith('https://open.spotify.com/track/'):
        url2 = spot_to_yt(url2)

    yt1 = YouTube(url1)
    stream1 = yt1.streams.filter(only_audio=True).first()
    stream1.download(filename='temp_audio1.mp4')  # download as MP4

    yt2 = YouTube(url2)
    stream2 = yt2.streams.filter(only_audio=True).first()
    stream2.download(filename='temp_audio2.mp4')  # download as MP4

    y1, sr1 = librosa.load('temp_audio1.mp4')
    y2, sr2 = librosa.load('temp_audio2.mp4')

    if sr1 != sr2:
        raise ValueError("The two audio files have different sample rates!")

    if len(y1) < len(y2):
        y1 = np.tile(y1, int(np.ceil(len(y2) / len(y1))))
    elif len(y2) < len(y1):
        y2 = np.tile(y2, int(np.ceil(len(y1) / len(y2))))

    y1 = y1[:len(y2)]
    y2 = y2[:len(y1)]

    combined = np.vstack((y1, y2))

    sf.write('ficzur.wav', combined.T, sr1)

    voice_channel.play(discord.FFmpegPCMAudio('ficzur.wav'),
                       after=lambda e: client.loop.create_task(_play_next(interaction)))
    voice_channel.source = discord.PCMVolumeTransformer(voice_channel.source)
    voice_channel.source.volume = 0.5

    await interaction.edit_original_response(content='Playing your song now.')

    while voice_channel.is_playing():
        await asyncio.sleep(1)

    os.remove('temp_audio1.mp4')
    os.remove('temp_audio2.mp4')
    os.remove('ficzur.wav')


last_audio_file = None


@client.event
async def on_message(message):
    global last_audio_file
    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.endswith(('.mp3', '.wav')):
                await attachment.save(f"./songs/{attachment.filename}")
                last_audio_file = f"./songs/{attachment.filename}"
                break
        print(f"Last audio file: {last_audio_file}")


@tree.command(name='play_my', description='Play a user\'s audio file')
async def play_my(interaction: discord.Interaction):
    global last_audio_file
    guild = interaction.guild
    member = guild.get_member(interaction.user.id)
    channel = member.voice.channel

    if guild.voice_client is None:
        voice_channel = await channel.connect()
    else:
        voice_channel = guild.voice_client
        if voice_channel.is_playing():
            voice_channel.stop()

    if last_audio_file is not None:
        voice_channel.play(discord.FFmpegPCMAudio(last_audio_file),
                           after=lambda e: client.loop.create_task(_play_next(interaction)))
        voice_channel.source = discord.PCMVolumeTransformer(voice_channel.source)
        voice_channel.source.volume = 0.5

        await interaction.response.send_message('Playing your audio file now.')
    else:
        await interaction.response.send_message('No audio file found.')


theme_queue = []
is_theme_playing = False

@tree.command(name='theme', description='Play a theme from a predefined list')
@app_commands.choices(theme=[
    app_commands.Choice(name='fent', value='fent'),
    app_commands.Choice(name='miodowanie', value='miodowanie'),
    app_commands.Choice(name='speegarage', value='speegarage'),
    app_commands.Choice(name='sebol', value='sebol')
])
async def theme(interaction: discord.Interaction, theme: app_commands.Choice[str]):
    global is_theme_playing, theme_queue
    if is_theme_playing:
        await interaction.response.send_message('A theme is already playing.')
        return
    is_theme_playing = True
    theme_folder = {
        'fent': 'C:/Users/stgad/Music/Fent',
        'miodowanie': 'C:/Users/stgad/Music/Poldon Crusin',
        'speegarage': 'C:/Users/stgad/Music/Speedgarae',
        'sebol': 'C:/Users/stgad/Music/sebol'
    }
    folder = theme_folder[theme.value]
    songs = [os.path.join(folder, file) for file in os.listdir(folder) if file.endswith('.mp3')]
    random.shuffle(songs)
    theme_queue.extend(songs)
    await interaction.response.send_message(f'Added {theme.value} theme songs to the queue.')
    await play_next_theme_song(interaction)

async def play_next_theme_song(interaction):
    global is_theme_playing, theme_queue
    if len(theme_queue) > 0:
        song = theme_queue.pop(0)
        guild = interaction.guild
        member = guild.get_member(interaction.user.id)
        channel = member.voice.channel

        if guild.voice_client is None:
            voice_channel = await channel.connect()
        else:
            voice_channel = guild.voice_client
            if voice_channel.is_playing():
                voice_channel.stop()

        voice_channel.play(discord.FFmpegPCMAudio(song), after=lambda e: client.loop.create_task(play_next_theme_song(interaction)))
        voice_channel.source = discord.PCMVolumeTransformer(voice_channel.source)
        voice_channel.source.volume = 0.5
    else:
        is_theme_playing = False

@tree.command(name='stop_theme', description='Stop the current theme and clear the theme queue')
async def stop_theme(interaction: discord.Interaction):
    global is_theme_playing, theme_queue
    guild = interaction.guild
    voice_client = discord.utils.get(client.voice_clients, guild=interaction.guild)
    theme_queue = []
    if voice_client and voice_client.is_playing():
        voice_client.stop()
    is_theme_playing = False
    await interaction.response.send_message('Stopped the theme and cleared the theme queue.')


@client.event
async def on_ready():
    for guild in client.guilds:
        print(f'{client.user} has connected to {guild.name}!')
        await tree.sync()
    print("Ready!")




client.run(TOKEN)