"""
language_engine.py - multilingual learning and accuracy helpers.

Tamil stays the source of truth. Other languages are learner-facing bridges:
captions, narration support lines, and UI labels.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

from schemas import (
    MOOD_TAMIL,
    THINAI_MEANING,
    THINAI_TAMIL,
    Mood,
    Poem,
    PoemAnalysis,
    SceneFrame,
    SubtitleEntry,
    Thinai,
)


LANGUAGE_OPTIONS: dict[str, str] = {
    "ta": "Tamil",
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "ur": "Urdu",
    "si": "Sinhala",
    "ar": "Arabic",
    "zh-CN": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
}

GTTS_LANGUAGE_ALIASES = {
    "zh-CN": "zh-CN",
}

TAMIL_THINAI_NAMES: dict[Thinai, str] = {
    Thinai.KURINJI: "குறிஞ்சி",
    Thinai.MULLAI: "முல்லை",
    Thinai.MARUTHAM: "மருதம்",
    Thinai.NEYTAL: "நெய்தல்",
    Thinai.PALAI: "பாலை",
    Thinai.UNKNOWN: "திணை",
}

TAMIL_TERMS = {
    "thinai": "திணை",
    "akam": "அகம்",
    "puram": "புறம்",
    "pulavar": "புலவர்",
    "sangam": "சங்கம்",
}

THINAI_HINTS: dict[Thinai, tuple[str, ...]] = {
    Thinai.KURINJI: ("mountain", "hill", "kurinji", "waterfall", "union", "secret meeting"),
    Thinai.MULLAI: ("forest", "mullai", "jasmine", "waiting", "return", "monsoon"),
    Thinai.MARUTHAM: ("field", "paddy", "river", "marutham", "quarrel", "infidelity"),
    Thinai.NEYTAL: ("sea", "shore", "wave", "boat", "neytal", "separation"),
    Thinai.PALAI: ("desert", "wilderness", "journey", "palai", "hardship", "bandit"),
}

FALLBACK_TERMS: dict[str, dict[str, str]] = {
    "en": {
        "thinai": "landscape-emotion tradition",
        "akam": "inner life or love poetry",
        "puram": "public life or heroic poetry",
        "pulavar": "poet-scholar",
    },
    "hi": {
        "thinai": "भू-दृश्य और भाव की परंपरा",
        "akam": "अंतरंग प्रेम काव्य",
        "puram": "वीरता और सार्वजनिक जीवन का काव्य",
        "pulavar": "कवि-विद्वान",
    },
    "fr": {
        "thinai": "tradition reliant paysage et emotion",
        "akam": "poesie de l'interieur et de l'amour",
        "puram": "poesie de la vie publique et heroique",
        "pulavar": "poete erudit",
    },
    "es": {
        "thinai": "tradicion de paisaje y emocion",
        "akam": "poesia interior o amorosa",
        "puram": "poesia publica o heroica",
        "pulavar": "poeta sabio",
    },
}

FALLBACK_TERMS["hi"] = {
    "thinai": "भूमि-दृश्य और भावना की परंपरा",
    "akam": "अंतरंग प्रेम काव्य",
    "puram": "वीरता और सार्वजनिक जीवन का काव्य",
    "pulavar": "कवि-विद्वान",
}

LANGUAGE_BRIDGES: dict[str, dict[str, str]] = {
    "en": {
        "learner_prefix": "For learners in English",
        "thinai_intro": "Thinai means a landscape-emotion tradition",
        "remember": "Remember the Tamil word",
        "place_feeling": "it names both place and feeling",
    },
    "hi": {
        "learner_prefix": "हिंदी सीखने वालों के लिए",
        "thinai_intro": "तिणै का अर्थ है भूमि-दृश्य और भाव की संगम परंपरा",
        "remember": "तमिल शब्द याद रखिए",
        "place_feeling": "यह स्थान और भावना दोनों को एक साथ नाम देता है",
    },
    "fr": {
        "learner_prefix": "Pour les apprenants en francais",
        "thinai_intro": "Thinai relie paysage et emotion dans la tradition Sangam",
        "remember": "Gardez en memoire le mot tamoul",
        "place_feeling": "il nomme a la fois le lieu et le sentiment",
    },
    "es": {
        "learner_prefix": "Para estudiantes en espanol",
        "thinai_intro": "Thinai une paisaje y emocion en la tradicion Sangam",
        "remember": "Recuerda la palabra tamil",
        "place_feeling": "nombra a la vez el lugar y el sentimiento",
    },
}

PULAVAR_OPENINGS: dict[str, str] = {
    "en": "Listen as a Pulavar would: slowly, with the land speaking before the heart answers.",
    "hi": "एक पुलवर की तरह सुनिए: धीरे और गंभीर ढंग से; पहले भूमि बोलती है, फिर मन का भाव उत्तर देता है.",
    "fr": "Ecoutez comme un Pulavar: lentement, avec la terre qui parle avant que le coeur reponde.",
    "es": "Escucha como un Pulavar: despacio, dejando que la tierra hable antes de que responda el corazon.",
}

SCENE_PHRASES: dict[str, dict[str, str]] = {
    "en": {
        "scene": "Scene",
        "behold": "Behold",
        "meaning": "In this image, the poem's feeling gathers quietly.",
        "setting": "The land is",
        "closing": "The scene rests there, like a verse held on the tongue.",
    },
    "hi": {
        "scene": "दृश्य",
        "behold": "देखिए",
        "meaning": "इस चित्र में कविता का भाव शांत रूप से इकट्ठा होता है.",
        "setting": "यह भूमि है",
        "closing": "दृश्य यहीं ठहर जाता है, जैसे जिह्वा पर ठहरा हुआ एक पद.",
    },
    "fr": {
        "scene": "Scene",
        "behold": "Regardez",
        "meaning": "Dans cette image, le sentiment du poeme se rassemble doucement.",
        "setting": "Le paysage est",
        "closing": "La scene demeure la, comme un vers garde sur la langue.",
    },
    "es": {
        "scene": "Escena",
        "behold": "Mira",
        "meaning": "En esta imagen, el sentimiento del poema se reune en silencio.",
        "setting": "La tierra es",
        "closing": "La escena queda alli, como un verso sostenido en la lengua.",
    },
}

HINDI_SCENE_TITLES: dict[str, str] = {
    "Mountain Opening": "पर्वत का आरंभ",
    "Flowered Slope": "फूलों वाली ढलान",
    "First Meeting": "पहली भेंट",
    "Moonlit Visit": "चांदनी में आगमन",
    "Poetic Echo": "काव्य की प्रतिध्वनि",
    "Forest Dusk": "वन की सांझ",
    "Ayar Settlement": "आयर बस्ती",
    "Waiting Path": "प्रतीक्षा का पथ",
    "Twilight Return": "सांझ की वापसी",
    "Jasmine Rest": "मुल्लै की शांति",
    "Paddy Dawn": "धान के खेतों की सुबह",
    "Lotus Pond": "कमल का तालाब",
    "Village Courtyard": "गांव का आंगन",
    "Domestic Quarrel": "घर का मनमुटाव",
    "Return Home": "घर वापसी",
    "Sugarcane Edge": "गन्ने के खेत का किनारा",
    "Reconciliation": "मिलन और शांति",
    "Seashore Wind": "समुद्र तट की हवा",
    "Waiting Tide": "प्रतीक्षा की लहर",
    "Fishing Boats": "मछुआरों की नावें",
    "Pale Horizon": "फीका क्षितिज",
    "Wave Memory": "लहरों की स्मृति",
    "Dry Road": "सूखा मार्ग",
    "Travel Heat": "यात्रा की गर्मी",
    "Lonely Pause": "एकाकी ठहराव",
    "Distant Figure": "दूर जाता यात्री",
    "Heat Haze": "गर्मी की धुंध",
}


def language_choices() -> list[tuple[str, str]]:
    return [(code, name) for code, name in LANGUAGE_OPTIONS.items()]


def language_label(code: str | None) -> str:
    return LANGUAGE_OPTIONS.get(normalize_language(code), LANGUAGE_OPTIONS["en"])


def normalize_language(code: str | None) -> str:
    if not code:
        return "en"
    code = code.strip()
    if code in LANGUAGE_OPTIONS:
        return code
    short = code.split("-")[0].lower()
    return short if short in LANGUAGE_OPTIONS else "en"


def gtts_language(code: str | None) -> str:
    code = normalize_language(code)
    return GTTS_LANGUAGE_ALIASES.get(code, code)


def improve_analysis_accuracy(
    analysis: PoemAnalysis,
    poem_text: str = "",
    library_poem: Poem | None = None,
) -> PoemAnalysis:
    """Conservative cleanup so weak AI output still follows Sangam rules."""
    if library_poem:
        analysis.thinai = library_poem.thinai or analysis.thinai
        analysis.thurai = analysis.thurai or library_poem.thurai
        analysis.speaker = analysis.speaker or library_poem.speaker
        analysis.listener = analysis.listener or library_poem.listener
        analysis.poet = analysis.poet or library_poem.author
        analysis.poet_tamil = analysis.poet_tamil or library_poem.author_ta
        analysis.collection = analysis.collection or library_poem.collection
        analysis.collection_tamil = analysis.collection_tamil or library_poem.collection_ta
        analysis.period = analysis.period or library_poem.period
        analysis.akam_puram = analysis.akam_puram or library_poem.akam_puram
        analysis.uri_porul = analysis.uri_porul or library_poem.uri_porul
        analysis.meyppadu = analysis.meyppadu or library_poem.meyppadu
        if not analysis.karu_porul:
            analysis.karu_porul = library_poem.karu_porul
        if not analysis.word_meanings:
            analysis.word_meanings = library_poem.word_meanings

    if analysis.thinai == Thinai.UNKNOWN:
        analysis.thinai = infer_thinai(poem_text, analysis)

    if analysis.thinai != Thinai.UNKNOWN:
        analysis.summary = analysis.summary or f"This poem belongs to the {analysis.thinai.value} Sangam landscape."
        analysis.summary_tamil = analysis.summary_tamil or f"இந்தப் பாடல் {THINAI_TAMIL.get(analysis.thinai, '')} திணையின் உணர்வை வெளிப்படுத்துகிறது."
        analysis.mood = analysis.mood if analysis.mood != Mood.UNKNOWN else mood_for_thinai(analysis.thinai)
        analysis.emotion_tamil = analysis.emotion_tamil or MOOD_TAMIL.get(analysis.mood, "")

    analysis.cultural_context = analysis.cultural_context or (
        "Sangam poems join landscape, time, nature, and human feeling into one symbolic system."
    )
    analysis.literary_devices = analysis.literary_devices or (
        "Thinai symbolism, karu imagery, uri emotion, and implied inner meaning."
    )
    return analysis


def infer_thinai(poem_text: str, analysis: PoemAnalysis | None = None) -> Thinai:
    haystack = " ".join(
        [
            poem_text or "",
            getattr(analysis, "summary", "") or "",
            getattr(analysis, "cultural_context", "") or "",
            getattr(analysis, "uri_porul", "") or "",
        ]
    ).lower()
    scores: dict[Thinai, int] = {}
    for thinai, hints in THINAI_HINTS.items():
        scores[thinai] = sum(1 for hint in hints if hint in haystack)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else Thinai.UNKNOWN


def mood_for_thinai(thinai: Thinai) -> Mood:
    return {
        Thinai.KURINJI: Mood.JOY,
        Thinai.MULLAI: Mood.LONGING,
        Thinai.MARUTHAM: Mood.ANGER,
        Thinai.NEYTAL: Mood.LONGING,
        Thinai.PALAI: Mood.SORROW,
    }.get(thinai, Mood.UNKNOWN)


def build_learning_script(
    analysis: PoemAnalysis,
    scenes: list[SceneFrame] | None = None,
    target_language: str = "en",
) -> str:
    """Build human narration: Tamil first, learner-language bridge second."""
    target_language = normalize_language(target_language)
    intro_bridge = learning_bridge_text(analysis, target_language)

    tamil_lines = [
        "வணக்கம். சங்கத் தமிழின் உலகுக்குள் நாம் மெதுவாக நடக்கிறோம்.",
        f"இது {analysis.thinai.value} திணையின் பாடல்; {THINAI_TAMIL.get(analysis.thinai, '')} நிலம் இதன் இதயம்.",
        "ஒரு புலவர் போல கேளுங்கள்: இயற்கை முதலில் பேசுகிறது, மனித உணர்வு பின்னர் திறக்கிறது.",
    ]
    if analysis.summary_tamil:
        tamil_lines.append(analysis.summary_tamil)
    elif analysis.summary:
        tamil_lines.append(analysis.summary)

    scene_lines: list[str] = []
    for scene in scenes or []:
        scene_lines.append(
            f"காட்சி {scene.scene_id}. {scene.title}. {scene.description}"
        )

    closing = [
        "இந்த அனுபவத்தில் காட்சி, குரல், பொருள் மூன்றும் ஒன்றாக நகர்கின்றன.",
        "தமிழை கற்கும் ஒவ்வொருவருக்கும், இந்தப் பாடல் ஒரு சிறிய வாசல் ஆகட்டும்.",
    ]

    parts = tamil_lines + [intro_bridge] + scene_lines + closing
    return " ".join(part.strip() for part in parts if part and part.strip())


def learning_bridge_text(analysis: PoemAnalysis, target_language: str) -> str:
    target_language = normalize_language(target_language)
    if target_language == "ta":
        return "இந்த விளக்கம் முழுவதும் தமிழில் தொடர்கிறது."

    source = {
        "thinai": analysis.thinai.value,
        "thinai_tamil": THINAI_TAMIL.get(analysis.thinai, ""),
        "meaning": THINAI_MEANING.get(analysis.thinai, ""),
        "summary": analysis.summary,
        "mood": analysis.mood.value,
    }
    translated = translate_json(source, target_language)
    terms = FALLBACK_TERMS.get(target_language, FALLBACK_TERMS["en"])
    return (
        f"For learners in {language_label(target_language)}: "
        f"Thinai means {terms['thinai']}. "
        f"{translated.get('summary') or analysis.summary} "
        f"Remember the Tamil word {THINAI_TAMIL.get(analysis.thinai, '')}: it names both place and feeling."
    )


def scene_caption_text(
    scene: SceneFrame,
    analysis: PoemAnalysis,
    target_language: str = "en",
) -> tuple[str, str]:
    target_language = normalize_language(target_language)
    tamil = f"{THINAI_TAMIL.get(analysis.thinai, '')} நிலத்தின் உணர்வு: {scene.title}"
    englishish = f"{scene.title}. {scene.description}"
    if target_language in ("en", "ta"):
        return englishish, tamil
    translated = translate_text(englishish, target_language)
    if target_language == "hi" and translated == englishish:
        title = HINDI_SCENE_TITLES.get(scene.title, scene.title)
        translated = (
            f"{title}. इस दृश्य में {analysis.thinai.value} तिणै की भूमि, "
            "प्रकृति और मानवीय भावना एक साथ खुलती है."
        )
    return translated or englishish, tamil


def learning_bridge_text(analysis: PoemAnalysis, target_language: str) -> str:
    target_language = normalize_language(target_language)
    if target_language == "ta":
        return "Tamil learner mode: source Tamil terms are kept as the main guide."

    source = {
        "thinai": analysis.thinai.value,
        "thinai_tamil": THINAI_TAMIL.get(analysis.thinai, ""),
        "meaning": THINAI_MEANING.get(analysis.thinai, ""),
        "summary": analysis.summary,
        "mood": analysis.mood.value,
    }
    translated = translate_json(source, target_language)
    terms = FALLBACK_TERMS.get(target_language, FALLBACK_TERMS["en"])
    bridge = LANGUAGE_BRIDGES.get(target_language, LANGUAGE_BRIDGES["en"])
    return (
        f"{bridge['learner_prefix']}: "
        f"{bridge['thinai_intro']} ({terms['thinai']}). "
        f"{translated.get('summary') or analysis.summary} "
        f"{bridge['remember']} {THINAI_TAMIL.get(analysis.thinai, '')}: "
        f"{bridge['place_feeling']}."
    )


def build_learning_script(
    analysis: PoemAnalysis,
    scenes: list[SceneFrame] | None = None,
    target_language: str = "en",
) -> str:
    """Build a scene-led Pulavar narration in the learner language."""
    target_language = normalize_language(target_language)
    phrases = SCENE_PHRASES.get(target_language, SCENE_PHRASES["en"])
    opening = PULAVAR_OPENINGS.get(target_language, PULAVAR_OPENINGS["en"])

    parts = [opening, learning_bridge_text(analysis, target_language)]
    for scene in scenes or []:
        caption, _ = scene_caption_text(scene, analysis, target_language)
        setting = f"{phrases['setting']} {scene.environment}." if scene.environment else ""
        parts.append(
            " ".join(
                part
                for part in (
                    f"{phrases['scene']} {scene.scene_id}.",
                    f"{phrases['behold']}: {caption}",
                    setting,
                    phrases["meaning"],
                    phrases["closing"],
                )
                if part
            )
        )

    return " ".join(part.strip() for part in parts if part and part.strip())


def build_multilingual_subtitles(
    scenes: list[SceneFrame],
    tracks: list[Any],
    analysis: PoemAnalysis,
    target_language: str = "en",
) -> list[SubtitleEntry]:
    scene_map = {scene.scene_id: scene for scene in scenes}
    subtitles: list[SubtitleEntry] = []
    for track in tracks:
        scene = scene_map.get(track.scene_id)
        if not scene:
            continue
        text_target, text_ta = scene_caption_text(scene, analysis, target_language)
        subtitles.append(
            SubtitleEntry(
                index=len(subtitles) + 1,
                start_seconds=track.start_seconds,
                end_seconds=track.end_seconds,
                text_en=text_target,
                text_ta=text_ta,
                speaker=f"Pulavar - {language_label(target_language)}",
                scene_id=track.scene_id,
            )
        )
    return subtitles


UI_TRANSLATIONS: dict[str, dict[str, str]] = {
    "ta": {
        "Literary Analysis": "இலக்கிய ஆய்வு",
        "Analyzed from image": "படத்திலிருந்து ஆய்வு செய்யப்பட்டது",
        "Poet": "புலவர்",
        "Collection": "தொகை",
        "Period": "காலம்",
        "Thinai": "திணை",
        "Emotion": "உணர்வு",
        "Mood": "மனநிலை",
        "Thurai": "துறை",
        "Speaker": "பேசுவோர்",
        "Listener": "கேட்போர்",
        "Summary": "சுருக்கம்",
        "Learner Guide": "கற்றல் வழிகாட்டி",
        "Sangam Poetics": "சங்கப் பொருள் அமைப்பு",
        "Muthal Porul": "முதற்பொருள்",
        "Time and Place": "காலமும் இடமும்",
        "Landscape": "நிலம்",
        "Season": "பருவம்",
        "Time": "பொழுது",
        "Karu Porul": "கருப்பொருள்",
        "Flora, Fauna and Objects": "மலர், விலங்கு, பொருட்கள்",
        "Uri Porul": "உரிப்பொருள்",
        "Central Emotion or Action": "மைய உணர்வு அல்லது செயல்",
        "Cultural Context": "பண்பாட்டு சூழல்",
        "Literary Devices": "இலக்கிய உத்திகள்",
        "Grammar Notes": "இலக்கணக் குறிப்புகள்",
        "In this poem": "இந்தப் பாடலில்",
        "Word Meanings": "சொற்பொருள்",
        "Characters": "கதாபாத்திரங்கள்",
        "Meaning Breakdown": "பொருள் விளக்கம்",
        "Scene Breakdown": "காட்சி பிரிவு",
        "Scene": "காட்சி",
        "Advanced Details": "மேலும் விவரங்கள்",
        "Environment": "சூழல்",
        "Lighting": "ஒளி",
        "Palette": "நிறத் தொகுப்பு",
        "Image unavailable": "படம் கிடைக்கவில்லை.",
        "Illustration unavailable": "விளக்கப்படம் கிடைக்கவில்லை",
        "Sangam Voice": "சங்கக் குரல்",
        "Narration audio is being prepared for this poem.": "இந்தப் பாடலுக்கான குரல் தயாராகிறது.",
        "Narration audio could not be played here, but the analysis remains available.": "குரலை இங்கே இயக்க முடியவில்லை; ஆய்வு கிடைக்கிறது.",
        "Narration is unavailable for this run.": "இந்த ஓட்டத்தில் குரல் கிடைக்கவில்லை.",
        "Enable narration in the sidebar to hear the poem.": "பாடலைக் கேட்க பக்கப்பட்டியில் குரலை இயக்கவும்.",
        "Ask Pulavar": "புலவரைக் கேளுங்கள்",
        "Ask the ancient scholar anything about Sangam poetry, culture, or this poem.": "சங்கக் கவிதை, பண்பாடு, இந்தப் பாடல் பற்றி புலவரிடம் கேளுங்கள்.",
        "Ask Pulavar a question...": "புலவரிடம் கேள்வி கேளுங்கள்...",
        "Pulavar reflects...": "புலவர் சிந்திக்கிறார்...",
        "Poem source": "பாடல் மூலம்",
        "Type / Paste": "தட்டச்சு / ஒட்டு",
        "Library": "நூலகம்",
        "Camera / Image": "கேமரா / படம்",
        "Enter Sangam poem": "சங்கப் பாடலை உள்ளிடுங்கள்",
        "Paste Tamil or English poem here...": "தமிழ் அல்லது வேறு மொழிப் பாடலை இங்கே ஒட்டுங்கள்...",
        "Select a poem": "பாடலைத் தேர்ந்தெடுக்கவும்",
        "Show Tamil version": "தமிழ் வடிவைக் காட்டு",
        "Poetic Structure": "கவிதை அமைப்பு",
        "Options": "விருப்பங்கள்",
        "Demo judging mode": "டெமோ மதிப்பீட்டு முறை",
        "Learning": "கற்றல்",
        "Narration and subtitle language": "குரல் மற்றும் வசன மொழி",
        "Generate scene images": "காட்சி படங்களை உருவாக்கு",
        "Generate voice narration": "குரல் விளக்கத்தை உருவாக்கு",
        "Generate Experience video": "அனுபவ வீடியோவை உருவாக்கு",
        "Analyze Poem": "பாடலை ஆய்வு செய்",
        "Please enter a poem to analyze.": "ஆய்வு செய்ய ஒரு பாடலை உள்ளிடுங்கள்.",
        "Enter a Sangam poem to begin": "தொடங்க ஒரு சங்கப் பாடலை உள்ளிடுங்கள்",
        "Analysis": "ஆய்வு",
        "Scenes": "காட்சிகள்",
        "Voice": "குரல்",
        "Experience": "அனுபவம்",
        "Ask": "கேள்",
    },
    "hi": {
        "Literary Analysis": "साहित्यिक विश्लेषण",
        "Summary": "सारांश",
        "Scene Breakdown": "दृश्य विभाजन",
        "Scene": "दृश्य",
        "Sangam Voice": "संगम आवाज़",
        "Ask Pulavar": "पुलवर से पूछें",
        "Poem source": "कविता स्रोत",
        "Type / Paste": "टाइप / पेस्ट",
        "Library": "पुस्तकालय",
        "Camera / Image": "कैमरा / छवि",
        "Options": "विकल्प",
        "Learning": "अध्ययन",
        "Narration and subtitle language": "वाचन और उपशीर्षक भाषा",
        "Generate scene images": "दृश्य चित्र बनाएं",
        "Generate voice narration": "वाचन बनाएं",
        "Generate Experience video": "अनुभव वीडियो बनाएं",
        "Analyze Poem": "कविता का विश्लेषण करें",
        "Analysis": "विश्लेषण",
        "Scenes": "दृश्य",
        "Voice": "आवाज़",
        "Experience": "अनुभव",
        "Ask": "पूछें",
    },
    "fr": {
        "Literary Analysis": "Analyse litteraire",
        "Summary": "Resume",
        "Scene Breakdown": "Decoupage des scenes",
        "Scene": "Scene",
        "Sangam Voice": "Voix Sangam",
        "Ask Pulavar": "Demander au Pulavar",
        "Options": "Options",
        "Learning": "Apprentissage",
        "Narration and subtitle language": "Langue de narration et de sous-titres",
        "Analyze Poem": "Analyser le poeme",
        "Analysis": "Analyse",
        "Scenes": "Scenes",
        "Voice": "Voix",
        "Experience": "Experience",
        "Ask": "Demander",
    },
    "es": {
        "Literary Analysis": "Analisis literario",
        "Summary": "Resumen",
        "Scene Breakdown": "Desglose de escenas",
        "Scene": "Escena",
        "Sangam Voice": "Voz Sangam",
        "Ask Pulavar": "Preguntar al Pulavar",
        "Options": "Opciones",
        "Learning": "Aprendizaje",
        "Narration and subtitle language": "Idioma de narracion y subtitulos",
        "Analyze Poem": "Analizar poema",
        "Analysis": "Analisis",
        "Scenes": "Escenas",
        "Voice": "Voz",
        "Experience": "Experiencia",
        "Ask": "Preguntar",
    },
}


def ui_text(text: str, target_language: str | None = None) -> str:
    """Translate stable UI labels. Falls back to live translation when available."""
    target_language = normalize_language(target_language)
    if target_language == "en" or not text:
        return text
    local = UI_TRANSLATIONS.get(target_language, {})
    if text in local:
        return local[text]
    if target_language == "ta":
        return text
    translated = translate_text(text, target_language)
    return translated if not _translation_failed(text, translated, target_language) else text


def translate_analysis_payload(analysis: PoemAnalysis, target_language: str) -> dict[str, Any]:
    """Build translated display text for analysis panels."""
    target_language = normalize_language(target_language)
    if target_language == "ta":
        return {
            "summary": analysis.summary_tamil or analysis.summary,
            "emotion": analysis.emotion_tamil or analysis.emotion,
            "mood": MOOD_TAMIL.get(analysis.mood, analysis.mood.value),
            "thinai_meaning": THINAI_MEANING.get(analysis.thinai, ""),
            "cultural_context": analysis.cultural_context_tamil or analysis.cultural_context,
            "literary_devices": analysis.literary_devices,
            "uri_porul": analysis.uri_porul_tamil or analysis.uri_porul,
            "meyppadu": analysis.meyppadu_tamil or analysis.meyppadu,
        }
    payload = {
        "summary": analysis.summary,
        "emotion": analysis.emotion,
        "mood": analysis.mood.value,
        "thinai_meaning": THINAI_MEANING.get(analysis.thinai, ""),
        "cultural_context": analysis.cultural_context,
        "literary_devices": analysis.literary_devices,
        "uri_porul": analysis.uri_porul,
        "meyppadu": analysis.meyppadu,
    }
    if target_language == "en":
        return payload
    return translate_json(payload, target_language)


def translate_text(text: str, target_language: str) -> str:
    if not text or normalize_language(target_language) in ("en", "ta"):
        return text
    translated = translate_json({"text": text}, target_language)
    return translated.get("text", text)


@lru_cache(maxsize=128)
def _translate_json_cached(payload_json: str, target_language: str) -> str:
    if os.getenv("DTEC_ENABLE_LIVE_TRANSLATION", "1") != "1":
        return payload_json
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        return payload_json
    try:
        from gemini_client import get_model

        prompt = (
            "Translate the JSON string values into "
            f"{language_label(target_language)} for a global learner of Tamil. "
            "Keep Tamil words such as Thinai, Akam, Puram, Kurinji, Mullai, Marutham, Neytal, Palai unchanged, "
            "and explain them briefly when helpful. Return ONLY valid JSON.\n\n"
            f"{payload_json}"
        )
        response = get_model().generate_content(prompt)
        return _extract_json(response.text)
    except Exception:
        return payload_json


def translate_json(payload: dict[str, Any], target_language: str) -> dict[str, Any]:
    target_language = normalize_language(target_language)
    if target_language in ("en", "ta"):
        return payload
    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    try:
        return json.loads(_translate_json_cached(payload_json, target_language))
    except Exception:
        return payload


def _extract_json(text: str) -> str:
    text = (text or "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end >= start:
        return text[start : end + 1]
    return text


STRICT_LANGUAGE_COPY: dict[str, dict[str, str]] = {
    "en": {
        "opening": "Listen as a புலவர் would: slowly, with the land speaking before the heart answers.",
        "learner": "This poem belongs to the {thinai_ta} திணை. In சங்கம் poetry, திணை is not just scenery; it joins place, time, nature, and feeling.",
        "scene": "Scene",
        "behold": "Behold",
        "setting": "The landscape is",
        "meaning": "The image gathers the poem's feeling without leaving the சங்கம் world.",
        "closing": "Let the verse settle fully; the காட்சி, the voice, and the meaning now rest together.",
    },
    "ta": {
        "opening": "புலவர் உரைப்பது போல மெதுவாகக் கேளுங்கள்; முதலில் நிலம் பேசும், பின்னர் உள்ளம் பதிலளிக்கும்.",
        "learner": "இந்தப் பாடல் {thinai_ta} திணையைச் சார்ந்தது. சங்க இலக்கியத்தில் திணை என்பது நிலம், காலம், இயற்கை, உணர்வு ஆகியவை ஒன்றாக இணையும் வழி.",
        "scene": "காட்சி",
        "behold": "பாருங்கள்",
        "setting": "நிலப்பரப்பு",
        "meaning": "இந்த காட்சி, பாடலின் உணர்வை சங்க மரபிலேயே அமைதியாகத் தாங்குகிறது.",
        "closing": "பாடல் முழுமையாக அமைதியடையட்டும்; காட்சி, குரல், பொருள் மூன்றும் இங்கே ஒன்றாக நிற்கின்றன.",
    },
    "hi": {
        "opening": "एक புலவர் की तरह सुनिए: धीरे, गंभीरता से; पहले भूमि बोलती है, फिर हृदय उत्तर देता है.",
        "learner": "यह कविता {thinai_ta} திணை से जुड़ी है. சங்கம் काव्य में திணை स्थान, समय, प्रकृति और भाव को एक साथ रखता है.",
        "scene": "दृश्य",
        "behold": "देखिए",
        "setting": "भूमि है",
        "meaning": "यह चित्र कविता की भावना को சங்கம் परंपरा के भीतर शांत ढंग से संजोता है.",
        "closing": "पंक्ति को पूरा ठहरने दीजिए; காட்சி, स्वर और अर्थ अब साथ विश्राम करते हैं.",
    },
    "fr": {
        "opening": "Ecoutez comme un புலவர்: lentement, avec la terre qui parle avant que le coeur reponde.",
        "learner": "Ce poeme appartient au திணை {thinai_ta}. Dans la poesie சங்கம், le திணை unit lieu, temps, nature et sentiment.",
        "scene": "Scene",
        "behold": "Regardez",
        "setting": "Le paysage est",
        "meaning": "Cette image rassemble le sentiment du poeme sans quitter le monde சங்கம்.",
        "closing": "Laissez le vers se poser pleinement; la காட்சி, la voix et le sens reposent ensemble.",
    },
    "es": {
        "opening": "Escucha como un புலவர்: despacio, dejando que la tierra hable antes que responda el corazon.",
        "learner": "Este poema pertenece al திணை {thinai_ta}. En la poesia சங்கம், el திணை une lugar, tiempo, naturaleza y emocion.",
        "scene": "Escena",
        "behold": "Mira",
        "setting": "El paisaje es",
        "meaning": "Esta imagen recoge el sentimiento del poema sin salir del mundo சங்கம்.",
        "closing": "Deja que el verso repose por completo; la காட்சி, la voz y el sentido descansan juntos.",
    },
}


def tamil_thinai_name(thinai: Thinai | None) -> str:
    return TAMIL_THINAI_NAMES.get(thinai or Thinai.UNKNOWN, TAMIL_THINAI_NAMES[Thinai.UNKNOWN])


def _strict_copy(target_language: str) -> dict[str, str]:
    target_language = normalize_language(target_language)
    return STRICT_LANGUAGE_COPY.get(target_language, STRICT_LANGUAGE_COPY["en"])


def _translation_failed(source: str, translated: str, target_language: str) -> bool:
    if normalize_language(target_language) == "en":
        return False
    return not translated or translated.strip() == (source or "").strip()


def _fallback_scene_caption(scene: SceneFrame, analysis: PoemAnalysis, target_language: str) -> str:
    copy = _strict_copy(target_language)
    thinai_ta = tamil_thinai_name(analysis.thinai)
    if normalize_language(target_language) == "ta":
        return f"{copy['scene']} {scene.scene_id}. {scene.title}. {thinai_ta} திணையின் உணர்வு இங்கே விரிகிறது."
    return (
        f"{copy['scene']} {scene.scene_id}. {scene.title}. "
        f"{thinai_ta} திணை. {copy['meaning']}"
    )


def learning_bridge_text(analysis: PoemAnalysis, target_language: str) -> str:
    target_language = normalize_language(target_language)
    copy = _strict_copy(target_language)
    thinai_ta = tamil_thinai_name(analysis.thinai)
    if target_language in STRICT_LANGUAGE_COPY:
        return copy["learner"].format(thinai_ta=thinai_ta)

    source = {
        "text": (
            f"This poem belongs to the Tamil {thinai_ta} திணை. "
            "In Sangam poetry, திணை joins place, time, nature, and feeling."
        )
    }
    translated = translate_json(source, target_language).get("text", source["text"])
    return translated if not _translation_failed(source["text"], translated, target_language) else source["text"]


def scene_caption_text(
    scene: SceneFrame,
    analysis: PoemAnalysis,
    target_language: str = "en",
) -> tuple[str, str]:
    target_language = normalize_language(target_language)
    thinai_ta = tamil_thinai_name(analysis.thinai)
    tamil = f"{thinai_ta} திணையின் காட்சி {scene.scene_id}: {scene.title}"

    if target_language == "ta":
        return "", tamil

    englishish = f"Scene {scene.scene_id}. {scene.title}. {scene.description}"
    if target_language == "en":
        return englishish.replace(analysis.thinai.value, thinai_ta), tamil

    translated = translate_text(englishish, target_language)
    if _translation_failed(englishish, translated, target_language):
        translated = _fallback_scene_caption(scene, analysis, target_language)
    return translated, tamil


def build_learning_script(
    analysis: PoemAnalysis,
    scenes: list[SceneFrame] | None = None,
    target_language: str = "en",
) -> str:
    """Build a strict selected-language Pulavar narration for the video scenes."""
    target_language = normalize_language(target_language)
    copy = _strict_copy(target_language)
    parts = [
        copy["opening"],
        learning_bridge_text(analysis, target_language),
    ]

    for scene in (scenes or [])[:3]:
        caption, tamil = scene_caption_text(scene, analysis, target_language)
        spoken_caption = tamil if target_language == "ta" else caption
        setting = f"{copy['setting']} {scene.environment}." if scene.environment else ""
        parts.append(
            " ".join(
                part
                for part in (
                    f"{copy['scene']} {scene.scene_id}.",
                    f"{copy['behold']}: {spoken_caption}",
                    setting,
                    copy["meaning"],
                )
                if part
            )
        )

    parts.append(copy["closing"])
    return " ".join(part.strip() for part in parts if part and part.strip())


def build_multilingual_subtitles(
    scenes: list[SceneFrame],
    tracks: list[Any],
    analysis: PoemAnalysis,
    target_language: str = "en",
) -> list[SubtitleEntry]:
    target_language = normalize_language(target_language)
    scene_map = {scene.scene_id: scene for scene in scenes[:3]}
    subtitles: list[SubtitleEntry] = []
    for track in tracks:
        scene = scene_map.get(track.scene_id)
        if not scene:
            continue
        text_target, text_ta = scene_caption_text(scene, analysis, target_language)
        subtitles.append(
            SubtitleEntry(
                index=len(subtitles) + 1,
                start_seconds=track.start_seconds,
                end_seconds=track.end_seconds,
                text_en=text_target,
                text_ta=text_ta,
                speaker=f"Pulavar - {language_label(target_language)}",
                scene_id=track.scene_id,
            )
        )
    return subtitles
