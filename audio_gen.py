import os
import random
import warnings
from bark import SAMPLE_RATE, generate_audio, preload_models
from scipy.io.wavfile import write as write_wav
import numpy as np
from langdetect import detect

warnings.filterwarnings('ignore')

class AudioGenerator:
    def __init__(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            preload_models()
        print("Models preloaded")
        self.sample_rate = SAMPLE_RATE
        self.output_dir = "generated_songs/"

        self.singing_speakers = {
            'en': ['v2/en_speaker_6', 'v2/en_speaker_2'],  
            'pl': ['v2/pl_speaker_0', 'v2/pl_speaker_8'],  
            'de': ['v2/de_speaker_4', 'v2/de_speaker_5'],
            'es': ['v2/es_speaker_0', 'v2/es_speaker_4'],
            'fr': ['v2/fr_speaker_3', 'v2/fr_speaker_4'],
            'it': ['v2/it_speaker_4', 'v2/it_speaker_8'],  
            'ja': ['v2/ja_speaker_2', 'v2/ja_speaker_6'],
            'ko': ['v2/ko_speaker_1', 'v2/ko_speaker_2'],
            'ru': ['v2/ru_speaker_3', 'v2/ru_speaker_4'],
            'tr': ['v2/tr_speaker_0', 'v2/tr_speaker_6']
        }
        
        self.speakers = {
            'en': [f'v2/en_speaker_{i}' for i in range(10)],
            'pl': [f'v2/pl_speaker_{i}' for i in range(10)],
            'de': [f'v2/de_speaker_{i}' for i in range(10)],
            'es': [f'v2/es_speaker_{i}' for i in range(10)],
            'fr': [f'v2/fr_speaker_{i}' for i in range(10)],
            'hi': [f'v2/hi_speaker_{i}' for i in range(10)],
            'it': [f'v2/it_speaker_{i}' for i in range(10)],
            'ja': [f'v2/ja_speaker_{i}' for i in range(10)],
            'ko': [f'v2/ko_speaker_{i}' for i in range(10)],
            'pt': [f'v2/pt_speaker_{i}' for i in range(10)],
            'ru': [f'v2/ru_speaker_{i}' for i in range(10)],
            'tr': [f'v2/tr_speaker_{i}' for i in range(10)],
            'zh': [f'v2/zh_speaker_{i}' for i in range(10)]
        }
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def _get_speaker(self, text, for_singing=False):
        try:
            lang = detect(text)[:2].lower()
            if for_singing:
                speakers = self.singing_speakers.get(lang, self.singing_speakers['en'])
            else:
                speakers = self.speakers.get(lang, self.speakers['en'])
            return random.choice(speakers)
        except:
            return 'v2/en_speaker_6' if for_singing else random.choice(self.speakers['en'])

    def generate_speech(self, text, filename="speech.wav"):
        try:
            speaker = self._get_speaker(text)
            audio_array = generate_audio(text, history_prompt=speaker)
            output_path = os.path.join(self.output_dir, filename)
            write_wav(output_path, self.sample_rate, audio_array)
            return output_path
        except:
            return None

    def generate_singing(self, lyrics, filename="singing.wav"):
        try:
            speaker = self._get_speaker(lyrics)
            singing_prompt = f"""
            ♪ {lyrics} ♪
            """
            audio_array = generate_audio(singing_prompt, history_prompt=speaker) 
            output_path = os.path.join(self.output_dir, filename)
            write_wav(output_path, self.sample_rate, audio_array)
            return output_path
        except:
            return None
        

    def generate_singing(self, lyrics, filename="singing.wav"):
        try:
            speaker = self._get_speaker(lyrics, for_singing=True)
            singing_prompt = f"""
            ♪ {lyrics} ♪
            """
            audio_array = generate_audio(
                singing_prompt, 
                history_prompt=speaker,
            )
            output_path = os.path.join(self.output_dir, filename)
            write_wav(output_path, self.sample_rate, audio_array)
            return output_path
        except:
            return None