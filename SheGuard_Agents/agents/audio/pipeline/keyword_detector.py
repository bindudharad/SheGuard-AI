from typing import List, Dict, Optional
from dataclasses import dataclass, field
from difflib import SequenceMatcher
import re

from agents.audio.schemas import AudioConfig, KeywordMatch, Transcription, KeywordMatch

# Multi-language emergency keywords
EMERGENCY_KEYWORDS = {
    'en': {
        'emergency': ['help', 'emergency', 'urgent', 'sos', 'danger', '911', 'police', 'ambulance'],
        'help': ['help me', 'please help', 'save me', 'help please', 'somebody help', 'anyone help'],
        'stop': ['stop', 'don\'t', 'dont', 'leave me', 'get away', 'back off', 'let me go'],
        'distress': ['scared', 'frightened', 'terrified', 'help me god', 'oh my god', 'omg']
    },
    'hi': {
        'emergency': ['bachao', 'madad', 'emergency', 'khatra', 'police', 'ambulance'],
        'help': ['mujhe bachao', 'madad kijiye', 'kripya madad', 'koi bachao', 'bachao mujhe'],
        'stop': ['ruk jao', 'mat karo', 'chhodo', 'peeche hato', 'mujhe chhodo'],
        'distress': ['dar lag raha', 'bhaut darr', 'bhagwan bachao', 'hay mere bhagwan']
    },
    'kn': {
        'emergency': ['bachiso', 'sahaya', 'emergency', 'hatra', 'police', 'ambulance'],
        'help': ['nanage bachiso', 'dayavittu sahaya', 'kripaya sahaya', 'elli bachiso', 'bachiso nanage'],
        'stop': ['nillisi', 'madi', 'bidi', 'hatthu', 'nanage bidi'],
        'distress': ['bhaya aagide', 'tumba bhaya', 'devaru bachiso', 'ayyo devre']
    }
}

class KeywordDetector:
    def __init__(self, config: AudioConfig):
        self.config = config
        self.keywords_by_lang = EMERGENCY_KEYWORDS
        self.threshold = config.keyword_similarity_threshold
        self.fuzzy = config.keyword_fuzzy_matching
    
    def normalize_text(self, text: str) -> str:
        '''Normalize text for keyword matching'''
        # Lowercase
        text = text.lower()
        # Remove punctuation
        text = re.sub(r'[^\w\s]', ' ', text)
        # Normalize repeated characters (e.g., 'heeeeelp' -> 'help')
        text = re.sub(r'(.)\1{2,}', r'\1\1', text)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text
    
    def similarity(self, a: str, b: str) -> float:
        '''Calculate similarity ratio'''
        return SequenceMatcher(None, a, b).ratio()
    
    def detect(self, transcription: Transcription) -> List[KeywordMatch]:
        if not transcription or not transcription.text:
            return []
        
        text = self.normalize_text(transcription.text)
        matches = []
        
        # Detect language
        lang = transcription.language if transcription.language and transcription.language != 'auto' else 'en'
        if lang not in self.keywords_by_lang:
            lang = 'en'
        
        lang_keywords = self.keywords_by_lang.get(lang, self.keywords_by_lang['en'])
        
        # Check exact matches first
        for category, keywords in lang_keywords.items():
            for kw in keywords:
                kw_norm = self.normalize_text(kw)
                if kw_norm in text:
                    matches.append(KeywordMatch(
                        keyword=kw,
                        category=category,
                        confidence=1.0,
                        matched_text=kw_norm,
                        start_time=transcription.start_time,
                        end_time=transcription.end_time
                    ))
        
        # Fuzzy matching if enabled and no exact matches
        if self.fuzzy and not matches:
            for category, keywords in lang_keywords.items():
                for kw in keywords:
                    kw_norm = self.normalize_text(kw)
                    sim = self.similarity(kw_norm, text)
                    if sim >= self.threshold:
                        matches.append(KeywordMatch(
                            keyword=kw,
                            category=category,
                            confidence=sim,
                            matched_text=text,
                            start_time=transcription.start_time,
                            end_time=transcription.end_time
                        ))
        
        # Sort by confidence descending
        matches.sort(key=lambda x: x.confidence, reverse=True)
        
        # Deduplicate - keep highest confidence per keyword
        seen = set()
        deduped = []
        for m in matches:
            if m.keyword not in seen:
                seen.add(m.keyword)
                deduped.append(m)
        
        return deduped
