"""
scene_weaver.py — Visual Breakdown Engine 🎬
Converts PoemAnalysis into cinematic SceneFrames.
Does NOT generate images. Only prepares prompts.
No UI. No API calls.
"""

import os
from schemas import PoemAnalysis, SceneFrame, Thinai, Mood
from pulavar_engine import (
    build_scene_prompt,
    parse_scenes_response,
    load_prompt,
)

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────


SCENE_PROMPT_PATH = "prompts/scene_prompt.txt"

DEFAULT_SCENE_PROMPT = """
You are a Sangam-era cinematic director. Based on the poem analysis below, 
break the poem into 2-4 visual scenes. Return ONLY a valid JSON array (no extra text).

Analysis:
{analysis_json}

Return this exact JSON structure:
[
  {{
    "scene_id": 1,
    "title": "Short evocative scene title",
    "description": "Detailed visual description of the scene (2-3 sentences)",
    "mood": "One of: longing, joy, sorrow, anger, devotion, serenity, yearning, melancholy, unknown",
    "visual_prompt": "Detailed image generation prompt in Sangam aesthetic style",
    "characters": ["Character 1 name", "Character 2 name"],
    "environment": "Natural environment description",
    "lighting": "Time of day and lighting quality",
    "color_palette": "Dominant colors and palette description"
  }}
]

Aesthetic rules:
- All scenes must reflect ancient Tamil Sangam era (300 BCE - 300 CE)
- Use landscape imagery from the poem's Thinai classification
- Visual prompts must be rich enough for image generation
- Preserve the emotional weight of the original poem
"""

# ─────────────────────────────────────────────
# THINAI → LANDSCAPE MAPPING
# ─────────────────────────────────────────────
NEGATIVE_PROMPT = (
    "modern clothing, jeans, t-shirt, cars, electricity, "
    "buildings, futuristic architecture, photorealistic, "
    "western fantasy, sci-fi, watermark, text, logo, "
    "low quality, blurry, distorted anatomy"
)


KURINJI_CACHE_KEYS = [
    "hero_withhoney",
    "hero_gazing",
    "hero_gazing_heroine",
    "heroine_waiting",
    "kurinji_hills",
    "lovers_conversing",
    "lovers_first_meeting",
    "lovers_meeting",
    "moonlit_kurinji",
    "mountain_path",
    "night_visit",
    "sangam_hero",
    "waterfall",
    "mountain_pool",
    "elephant_stream",
    "peacock_rain_dance",
    "monkey_family_jackfruit",
    "kurinji_landscape",
]

MULLAI_CACHE_KEYS = [
    "mullai_forest",
    "heroine_waiting_dusk",
    "thozhi_consoling",
    "ayar_cattle_return",
    "ayar_settlement",
    "milkmaid_churning",
    "deer_mullai",
    "rabbit_jasmine",
    "ayar_flute",
    "mayon_worship",
    "monsoon_arrival",
    "watching_forest_path",
    "konrai_reunion",
    "hero_returns_twilight",
    "mullai_landscape",
]

MARUTHAM_CACHE_KEYS = [
    "marutham_paddy_fields",
    "uzhavar_farmers",
    "buffalo_paddy",
    "marutham_heroine_waiting",
    "hero_returning_home",
    "domestic_quarrel",
    "thozhi_mediation",
    "parathiyar",
    "lotus_pond",
    "buffalo_lotus_ullurai",
    "marutham_village",
    "sugarcane",
    "marutham_landscape",
]

NEYTAL_CACHE_KEYS = [
    "neytal_landscape",
    "neital_shoreline",
    "waves_longing",
    "heroine_seashore_waiting",
    "catamaran_boat",
    "fisherman_returning",
    "paratavar_fishermen",
    "punnai_tree",
    "seagull_coast",
    "shark_fishermen",
    "salt_merchants",
    "varunan_invocation",
    "neytalthozhi_consoling",
    "moonlit_beach",
]

PALAI_CACHE_KEYS = [
    "palai_landscape",
    "palai_landscape2",
    "desert_travellers",
    "dry_waterhole",
    "drought_forest",
    "blazing_sun",
    "hero_departure",
    "heroine_separation",
    "eloping_lovers",
    "vulture_sky",
    "starving_elephant",
    "maravar_warrior",
    "bandit_ambush",
    "kottravai_invocation",
    "grieving_mother",
]

KEYWORD_CACHE_MAP: dict[str, list[str]] = {
    "honey": ["hero_withhoney", "sunbird_kurinji", "hummingbird_flower", "peacock_rain_dance"],
    "nectar": ["hero_withhoney", "hummingbird_flower"],
    "hummingbird": ["sunbird_kurinji", "hummingbird_flower", "peacock_rain_dance"],
    "sunbird": ["sunbird_kurinji", "hummingbird_flower", "peacock_rain_dance"],
    "waterfall": ["waterfall", "mountain_pool", "elephant_stream"],
    "falls": ["waterfall", "mountain_pool", "elephant_stream"],
    "stream": ["waterfall", "mountain_pool", "elephant_stream"],
    "pool": ["mountain_pool", "waterfall"],
    "elephant": ["elephant_stream"],
    "peacock": ["peacock_rain_dance"],
    "rain": ["peacock_rain_dance", "moonlit_kurinji"],
    "monsoon": ["peacock_rain_dance", "monsoon_arrival", "watching_forest_path"],
    "moon": ["moonlit_kurinji", "night_visit"],
    "night": ["moonlit_kurinji", "night_visit"],
    "mountain": ["kurinji_hills", "mountain_path", "waterfall", "mountain_pool"],
    "hill": ["kurinji_hills", "mountain_path", "kurinji_landscape"],
    "forest": ["mullai_forest", "deer_mullai", "rabbit_jasmine", "konrai_reunion", "watching_forest_path"],
    "jasmine": ["rabbit_jasmine", "mullai_forest", "mayon_worship"],
    "thozhi": ["thozhi_consoling", "heroine_waiting_dusk", "konrai_reunion"],
    "heroine": ["heroine_waiting", "hero_gazing_heroine", "sangam_heroine", "lovers_conversing", "lovers_first_meeting"],
    "hero": ["hero_gazing_heroine", "sangam_hero", "hero_gazing"],
    "lover": ["lovers_first_meeting", "lovers_conversing", "lovers_walking_hills", "lovers_meeting"],
    "lovers": ["lovers_first_meeting", "lovers_conversing", "lovers_walking_hills", "lovers_meeting"],
    "meeting": ["lovers_first_meeting", "lovers_meeting", "lovers_conversing"],
    "path": ["mountain_path", "kurinji_hills", "watching_forest_path"],
    "walk": ["mountain_path", "kurinji_hills"],
    "deer": ["deer_mullai"],
    "rabbit": ["rabbit_jasmine"],
    "mayon": ["mayon_worship"],
    "poet": ["poet_recitation"],
    "village": ["marutham_village", "ayar_settlement", "village_life", "royal_court"],
    "market": ["marutham_village", "ayar_settlement", "village_life"],
    "home": ["marutham_village", "ayar_settlement", "royal_court"],
    "farm": ["marutham_paddy_fields", "uzhavar_farmers", "buffalo_paddy", "sugarcane"],
    "paddy": ["marutham_paddy_fields", "buffalo_paddy"],
    "field": ["marutham_paddy_fields", "marutham_landscape", "sugarcane"],
    "rice": ["marutham_paddy_fields", "buffalo_paddy"],
    "buffalo": ["buffalo_paddy"],
    "sea": ["neytal_landscape", "neital_shoreline", "waves_longing", "catamaran_boat"],
    "shore": ["neytal_landscape", "neital_shoreline", "heroine_seashore_waiting"],
    "seashore": ["neytal_landscape", "neital_shoreline", "waves_longing"],
    "wave": ["waves_longing", "neytal_landscape", "neital_shoreline"],
    "waves": ["waves_longing", "neytal_landscape", "neital_shoreline"],
    "boat": ["catamaran_boat", "fisherman_returning", "paratavar_fishermen"],
    "fisher": ["fisherman_returning", "paratavar_fishermen", "shark_fishermen"],
    "fishermen": ["paratavar_fishermen", "fisherman_returning", "shark_fishermen"],
    "sand": ["neytal_landscape", "neital_shoreline", "palai_landscape", "dry_waterhole"],
    "desert": ["palai_landscape", "palai_landscape2", "desert_travellers", "blazing_sun"],
    "dry": ["palai_landscape", "dry_waterhole", "drought_forest", "blazing_sun"],
    "drought": ["drought_forest", "dry_waterhole", "palai_landscape"],
    "sun": ["blazing_sun", "palai_landscape", "desert_travellers"],
    "journey": ["desert_travellers", "hero_departure", "palai_landscape"],
    "traveller": ["desert_travellers", "hero_departure", "palai_landscape"],
    "travel": ["desert_travellers", "hero_departure", "palai_landscape"],
    "separation": ["heroine_separation", "hero_departure", "desert_travellers"],
}


def select_cache_scene(scene: SceneFrame, analysis: PoemAnalysis | None = None) -> list[str]:
    """Choose the best scene cache key list for this scene."""

    text = " ".join(
        [
            scene.title or "",
            scene.description or "",
            scene.environment or "",
            scene.lighting or "",
            scene.color_palette or "",
            " ".join(scene.characters or []),
        ]
    ).lower()

    candidates: list[str] = []

    for keyword, keys in KEYWORD_CACHE_MAP.items():
        if keyword in text:
            candidates.extend(keys)

    if analysis and analysis.thinai and analysis.thinai != Thinai.UNKNOWN:
        if analysis.thinai == Thinai.KURINJI:
            candidates.extend(KURINJI_CACHE_KEYS)
        elif analysis.thinai == Thinai.MULLAI:
            candidates.extend(MULLAI_CACHE_KEYS)
        elif analysis.thinai == Thinai.MARUTHAM:
            candidates.extend(MARUTHAM_CACHE_KEYS)
        elif analysis.thinai == Thinai.NEYTAL:
            candidates.extend(NEYTAL_CACHE_KEYS)
        elif analysis.thinai == Thinai.PALAI:
            candidates.extend(PALAI_CACHE_KEYS)
        else:
            candidates.append(f"{analysis.thinai.value.lower()}_landscape")

    if "kurinji" in text:
        candidates.extend(KURINJI_CACHE_KEYS)
    if "mullai" in text:
        candidates.extend(MULLAI_CACHE_KEYS)
    if "marutham" in text:
        candidates.extend(MARUTHAM_CACHE_KEYS)
    if "neytal" in text:
        candidates.extend(NEYTAL_CACHE_KEYS)
    if "palai" in text:
        candidates.extend(PALAI_CACHE_KEYS)

    if analysis and analysis.thinai == Thinai.KURINJI:
        seen = set()
        ordered: list[str] = []
        for k in KURINJI_CACHE_KEYS:
            if k in candidates and k not in seen:
                ordered.append(k)
                seen.add(k)
        for k in candidates:
            if k not in seen:
                ordered.append(k)
                seen.add(k)
        candidates = ordered

    if analysis and analysis.thinai == Thinai.MULLAI:
        seen = set()
        ordered: list[str] = []
        for k in MULLAI_CACHE_KEYS:
            if k in candidates and k not in seen:
                ordered.append(k)
                seen.add(k)
        for k in candidates:
            if k not in seen:
                ordered.append(k)
                seen.add(k)
        candidates = ordered

    if analysis and analysis.thinai == Thinai.MARUTHAM:
        seen = set()
        ordered: list[str] = []
        for k in MARUTHAM_CACHE_KEYS:
            if k in candidates and k not in seen:
                ordered.append(k)
                seen.add(k)
        for k in candidates:
            if k not in seen:
                ordered.append(k)
                seen.add(k)
        candidates = ordered

    if analysis and analysis.thinai == Thinai.NEYTAL:
        seen = set()
        ordered: list[str] = []
        for k in NEYTAL_CACHE_KEYS:
            if k in candidates and k not in seen:
                ordered.append(k)
                seen.add(k)
        for k in candidates:
            if k not in seen:
                ordered.append(k)
                seen.add(k)
        candidates = ordered

    if analysis and analysis.thinai == Thinai.PALAI:
        seen = set()
        ordered: list[str] = []
        for k in PALAI_CACHE_KEYS:
            if k in candidates and k not in seen:
                ordered.append(k)
                seen.add(k)
        for k in candidates:
            if k not in seen:
                ordered.append(k)
                seen.add(k)
        candidates = ordered

    candidates.extend([
        "kurinji_hills",
        "kurinji_landscape",
        "mullai_landscape",
        "marutham_landscape",
        "neytal_landscape",
        "palai_landscape",
    ])

    return candidates

THINAI_NOTES = {
    Thinai.KURINJI:
        "Kurinji represents mountain landscapes and secret union of lovers.",

    Thinai.MULLAI:
        "Mullai represents forests and patient waiting.",

    Thinai.MARUTHAM:
        "Marutham represents agricultural lands and domestic conflict.",

    Thinai.NEYTAL:
        "Neytal represents seashores and painful separation.",

    Thinai.PALAI:
        "Palai represents hardship, travel, and dangerous journeys.",

    Thinai.UNKNOWN:
        "A timeless Sangam landscape."
} 

THINAI_LANDSCAPE = {
    Thinai.KURINJI:  "misty mountain slopes, waterfalls, kurinjI flowers, cool mountain air",
    Thinai.MULLAI:   "dense forest, jasmine vines, monsoon season, green undergrowth",
    Thinai.MARUTHAM: "fertile farmland, river delta, paddy fields, herons and ducks",
    Thinai.NEYTAL:   "seashore, crashing waves, sea breeze, fishing boats, sand dunes",
    Thinai.PALAI:    "arid desert, harsh sun, withered trees, dusty landscape",
    Thinai.UNKNOWN:  "ancient Tamil landscape, Sangam era scenery",
}

MOOD_LIGHTING = {
    Mood.LONGING:    "twilight, soft golden light fading to purple",
    Mood.JOY:        "golden sunrise, warm light, dappled shadows",
    Mood.SORROW:     "overcast sky, muted grey-blue tones, diffused light",
    Mood.ANGER:      "harsh midday sun, stark high-contrast shadows",
    Mood.DEVOTION:   "pre-dawn, pale silver moonlight",
    Mood.SERENITY:   "soft afternoon light, warm amber glow",
    Mood.YEARNING:   "sunset, deep orange and rose hues",
    Mood.MELANCHOLY: "dusk, fading light, long shadows",
    Mood.UNKNOWN:    "natural Sangam era lighting",
}


# ─────────────────────────────────────────────
# GEMINI CLIENT (centralized)
# ─────────────────────────────────────────────

from gemini_client import get_model as _get_gemini_model

def _sanitize_prompt(prompt: str) -> str:
    """
    Clean prompts before sending them to image generators.
    Removes duplicate commas and extra spaces.
    """
    if not prompt:
        return ""

    prompt = prompt.replace("\n", " ")
    prompt = " ".join(prompt.split())

    while ", ," in prompt:
        prompt = prompt.replace(", ,", ",")

    return prompt.strip(" ,")

def _fallback_scene(
    analysis: PoemAnalysis,
) -> SceneFrame:
    """
    Educational fallback scene.
    Used whenever Gemini cannot produce scenes.
    """

    landscape = THINAI_LANDSCAPE.get(
        analysis.thinai,
        THINAI_LANDSCAPE[Thinai.UNKNOWN],
    )

    lighting = MOOD_LIGHTING.get(
        analysis.mood,
        MOOD_LIGHTING[Mood.UNKNOWN],
    )

    title = (
        analysis.thinai.value
        if analysis.thinai != Thinai.UNKNOWN
        else "Sangam Landscape"
    )

    description = (
        analysis.summary
        or analysis.summary_tamil
        or "A poetic moment from Sangam literature."
    )

    prompt = (
        f"{landscape}, "
        f"{lighting}, "
        f"{analysis.uri_porul}, "
        f"{analysis.flora_fauna}, "
        f"ancient Tamil Sangam era, "
        f"historically accurate, "
        f"educational illustration style, "
        f"{NEGATIVE_PROMPT}"
    )

    return SceneFrame(
        scene_id=1,
        title=title,
        description=description,
        mood=analysis.mood,
        thinai=analysis.thinai,
        visual_prompt=_sanitize_prompt(prompt),
        characters=[
            c.role or c.name
            for c in analysis.characters
        ],
        environment=landscape,
        lighting=lighting,
        color_palette="Earth tones",
    )





def _generate_educational_scenes(
    analysis: PoemAnalysis,
) -> list[SceneFrame]:
    """
    Generate Sangam educational scenes
    without LLM assistance.
    """

    scenes = []

    primary = _fallback_scene(analysis)

    scenes.append(primary)

    note = THINAI_NOTES.get(
        analysis.thinai,
        THINAI_NOTES[Thinai.UNKNOWN],
    )

    scenes.append(
        SceneFrame(
            scene_id=2,
            title="Thinai Learning Card",
            description=note,
            mood=analysis.mood or Mood.UNKNOWN,
            thinai=analysis.thinai,
            visual_prompt=(
                f"{analysis.thinai.value} Thinai educational illustration, "
                f"{THINAI_LANDSCAPE.get(analysis.thinai)}, "
                f"traditional Sangam visual teaching aid, "
                f"{NEGATIVE_PROMPT}"
            ),
            environment=THINAI_LANDSCAPE.get(
                analysis.thinai,
                THINAI_LANDSCAPE[Thinai.UNKNOWN],
            ),
            lighting=MOOD_LIGHTING.get(
                analysis.mood,
                MOOD_LIGHTING[Mood.UNKNOWN],
            ),
            color_palette="Traditional Tamil manuscript colors",
        )
    )

    return scenes

# ─────────────────────────────────────────────
# ENRICHMENT HELPERS
# ─────────────────────────────────────────────

def _enrich_visual_prompt(scene: SceneFrame, analysis: PoemAnalysis) -> SceneFrame:
    """
    Add Thinai landscape and mood lighting to visual prompts
    if the LLM didn't include them.
    """
    landscape = THINAI_LANDSCAPE.get(analysis.thinai, THINAI_LANDSCAPE[Thinai.UNKNOWN])
    lighting = MOOD_LIGHTING.get(analysis.mood, MOOD_LIGHTING[Mood.UNKNOWN])

    enrichment = (
    f", {landscape}, "
    f"{lighting}, "
    f"ancient Tamil Sangam era, "
    f"historically accurate, "
    f"cinematic composition, "
    f"highly detailed, "
    f"{NEGATIVE_PROMPT}"
)

    if enrichment.lower() not in scene.visual_prompt.lower():
        scene = scene.model_copy(
            update={"visual_prompt": scene.visual_prompt.rstrip(".") + enrichment}
        )

    if not scene.environment:
        scene = scene.model_copy(update={"environment": landscape})

    if not scene.lighting:
        scene = scene.model_copy(update={"lighting": lighting})

    return scene


# ─────────────────────────────────────────────
# MAIN FUNCTION
# ─────────────────────────────────────────────

def extract_scene_frames(
    analysis: PoemAnalysis,
) -> list[SceneFrame]:
    """
    Convert PoemAnalysis → SceneFrames.

    Never raises.
    Never returns an empty list.
    """

    if not analysis:
        return [SceneFrame.empty()]

    if not analysis.summary:
        analysis = PoemAnalysis.empty()

    template = (
        load_prompt(SCENE_PROMPT_PATH)
        or DEFAULT_SCENE_PROMPT
    )

    try:
        prompt = build_scene_prompt(
            analysis,
            template,
        )

    except Exception as e:

        print(
            f"[scene_weaver] Prompt build failed: {e}"
        )

        return _generate_educational_scenes(
            analysis
        )

    try:
        model = _get_gemini_model()

        response = model.generate_content(
            prompt
        )

        raw_text = response.text

    except Exception as e:

        print(
            f"[scene_weaver] LLM failed: {e}"
        )

        return _generate_educational_scenes(
            analysis
        )

    try:
        scenes = parse_scenes_response(
            raw_text,
            analysis
        )

    except Exception as e:

        print(
            f"[scene_weaver] Parse failed: {e}"
        )

        return _generate_educational_scenes(
            analysis
        )

    if not scenes:

        return _generate_educational_scenes(
            analysis
        )

    enriched = []

    for scene in scenes:
        enriched.append(
            _enrich_visual_prompt(
                scene,
                analysis,
            )
        )

    return enriched
    
