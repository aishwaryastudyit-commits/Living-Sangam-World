import streamlit as st
import json
import os
import hashlib
from pathlib import Path
from dotenv import load_dotenv


SCENE_CACHE_DIR = Path("assets/images/scene_cache")

def _build_scene_cache() -> dict[str, str]:
    cache: dict[str, str] = {}

    # Load top-level cache assets first, then nested Kurinji assets.
    for image_path in sorted(SCENE_CACHE_DIR.glob("*.*")):
        if image_path.is_file() and image_path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            cache[image_path.stem.lower().replace(" ", "_")] = str(image_path)

    for image_path in sorted(SCENE_CACHE_DIR.rglob("*.*")):
        if (
            image_path.is_file()
            and image_path.suffix.lower() in {".jpg", ".jpeg", ".png"}
            and image_path.parent != SCENE_CACHE_DIR
        ):
            cache[image_path.stem.lower().replace(" ", "_")] = str(image_path)

    return cache

SCENE_CACHE = _build_scene_cache()

load_dotenv()

st.set_page_config(
    page_title="Living Sangam World: AI-Powered Immersive Tamil Poetry Experience",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded",
)

from schemas import (
    PipelineResult, PoemAnalysis, SceneFrame, Poem, Thinai, Mood, MuthalPorul,
    GrammarNote, MeaningLine, Character,
    THINAI_TAMIL, THINAI_MEANING, MOOD_TAMIL,
    GeneratedImage, NarrationResult, VideoExperience, VideoStatus, SubtitleFormat,
    THINAI_COLOR_PALETTE,
)
import pulavar_ai
import scene_weaver
import scene_generator
import sangam_voice
import ocr_engine
import language_engine
from scene_weaver import KURINJI_CACHE_KEYS, MULLAI_CACHE_KEYS, MARUTHAM_CACHE_KEYS

# video_engine is optional — gracefully degrade if not yet implemented
try:
    import video_engine
    _VIDEO_ENGINE_AVAILABLE = True
except ImportError:
    _VIDEO_ENGINE_AVAILABLE = False

_api_key_missing = not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))

# ── STYLES ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Crimson+Pro:ital,wght@0,300;0,400;1,300&display=swap');
:root {
    --sangam-bg:#F7F7F4;
    --sangam-panel:#FFFFFF;
    --sangam-panel-soft:#F1F3EF;
    --sangam-panel-ai:#FAFAF8;
    --sangam-panel-scene:#F3F1EC;
    --sangam-terracotta:#9A6B55;
    --sangam-terracotta-deep:#5F4A40;
    --sangam-green:#78866B;
    --sangam-bronze:#A58B68;
    --sangam-ink:#262626;
    --sangam-muted:#6B7280;
    --sangam-border:#D9D7D1;
    --thinai-kurinji:#B9B7E5;
    --thinai-mullai:#C6D3B8;
    --thinai-marutham:#E1CFA3;
    --thinai-neytal:#B8D4DF;
    --thinai-palai:#E3B9A6;
    --sangam-dark:var(--sangam-ink);
    --sangam-gold:var(--sangam-bronze);
    --sangam-earth:var(--sangam-terracotta);
}
html,body,[class*="css"]{
    font-family:'Crimson Pro',Georgia,serif;
    background:var(--sangam-bg);
    color:var(--sangam-ink);
}
.stApp{
    background:var(--sangam-bg);
}
h1,h2,h3{font-family:'Playfair Display',Georgia,serif;color:var(--sangam-terracotta-deep);}
h2,h3{
    border-left:4px solid #C8B7A6;
    background:transparent;
    padding:0.25rem 0 0.25rem 0.7rem;
}
.stTextArea textarea{
    background-color:var(--sangam-panel)!important;
    color:var(--sangam-ink)!important;
    border:1px solid var(--sangam-border)!important;
    border-radius:8px!important;
    font-family:'Crimson Pro',Georgia,serif!important;
    font-size:1.1rem!important;
}
.stTextArea textarea:focus{border-color:#A7B29A!important;box-shadow:0 0 0 1px rgba(120,134,107,0.18)!important;}
.stButton>button{
    background:#FFFFFF!important;
    color:var(--sangam-ink)!important;
    font-family:'Playfair Display',Georgia,serif!important;
    font-weight:700!important;
    border:1px solid var(--sangam-border)!important;
    border-radius:8px!important;
    padding:0.6rem 2rem!important;
    letter-spacing:0.02em!important;
    box-shadow:0 1px 3px rgba(15,23,42,0.08)!important;
}
.stButton>button:hover{background:#F1F3EF!important;border-color:#BFC4BA!important;color:#1F2937!important;}
.poem-card{
    background:#FFFDF7;
    border:1px solid #E6D7C6;
    border-radius:10px;
    padding:1.5rem 2rem;
    margin:1rem 0;
    font-style:italic;
    font-size:1.15rem;
    line-height:1.9;
    color:var(--sangam-ink);
    box-shadow:0 4px 14px rgba(95,74,64,0.08);
}
.analysis-card{
    background:#FFFBF3;
    border-left:4px solid #D8BFA5;
    border-top:1px solid #E6D7C6;
    border-right:1px solid #E6D7C6;
    border-bottom:1px solid #E6D7C6;
    padding:1rem 1.5rem;
    margin:0.7rem 0;
    border-radius:0 8px 8px 0;
    box-shadow:0 4px 12px rgba(95,74,64,0.06);
}
.thinai-badge{display:inline-block;background:#F1F6EA;color:#46513E;font-family:'Playfair Display',serif;font-weight:700;padding:0.2rem 0.8rem;border-radius:20px;font-size:0.9rem;letter-spacing:0.03em;border:1px solid #C9D3BF;}
.poetics-box{background:#FFFDF7;border:1px solid #E6D7C6;border-radius:8px;padding:1rem 1.2rem;margin:0.4rem 0;}
.poetics-label{color:var(--sangam-terracotta-deep);font-family:'Playfair Display',serif;font-weight:700;font-size:0.9rem;letter-spacing:0.06em;text-transform:uppercase;}
.poetics-value{color:var(--sangam-dark);margin-top:0.2rem;}
.poetics-value-ta{color:var(--sangam-muted);font-style:italic;font-size:0.95rem;}
.scene-header{font-family:'Playfair Display',serif;color:var(--sangam-terracotta-deep);font-size:1.2rem;border-left:4px solid #C8B7A6;background:var(--sangam-panel-scene);padding:0.5rem 0.8rem;margin-bottom:0.8rem;border-radius:0 8px 8px 0;}
.character-entry{background:#FFFDF7;border:1px solid #E6D7C6;border-radius:8px;padding:0.75rem 1rem;margin:0.4rem 0;}
.meaning-entry{background:#FFFDF7;border-left:3px solid #C9D3BF;padding:0.75rem 1rem;margin:0.5rem 0;}
.meaning-original{font-style:italic;color:#5F4A40;font-size:1.05rem;}
.meaning-translation{color:var(--sangam-dark);margin:0.3rem 0;}
.meaning-interpretation{color:var(--sangam-muted);font-size:0.95rem;}
.word-entry{background:#FBF7EF;border:1px solid #E6D7C6;border-radius:6px;padding:0.4rem 0.8rem;margin:0.2rem 0;display:flex;gap:0.8rem;align-items:baseline;}
.word-ta{color:#5F4A40;font-weight:700;min-width:140px;}
.word-en{color:var(--sangam-dark);font-size:0.95rem;}
.error-card{background:#FCE8E8;border:1px solid #E7A0A0;border-radius:6px;padding:1rem;color:#8A3030;}
.sidebar-title{font-family:'Playfair Display',serif;color:var(--sangam-terracotta-deep);font-size:1.25rem;text-align:center;padding:1rem 0;border-bottom:1px solid var(--sangam-border);line-height:1.25;}
div[data-testid="stSidebar"]{background:#FFFFFF!important;border-right:1px solid var(--sangam-border);}
.stSelectbox>div>div{background-color:var(--sangam-panel)!important;color:var(--sangam-dark)!important;border-color:var(--sangam-border)!important;}
.stTabs [data-baseweb="tab-list"]{background-color:rgba(255,249,240,0.82);border-bottom:1px solid var(--sangam-border);}
.stTabs [data-baseweb="tab"]{color:var(--sangam-muted);font-family:'Playfair Display',serif;}
.stTabs [aria-selected="true"]{color:var(--sangam-ink)!important;border-bottom-color:#C8B7A6!important;}
hr{border-color:var(--sangam-border);}

/* ── VideoExperience styles ── */
.video-header{
    font-family:'Playfair Display',serif;
    color:var(--sangam-terracotta-deep);
    font-size:1.5rem;
    text-align:center;
    letter-spacing:0.1em;
    margin-bottom:0.3rem;
}
.video-subheader{
    text-align:center;
    color:var(--sangam-muted);
    font-style:italic;
    font-size:1rem;
    margin-bottom:1.5rem;
}
.video-status-badge{
    display:inline-block;
    padding:0.2rem 0.9rem;
    border-radius:20px;
    font-family:'Playfair Display',serif;
    font-size:0.85rem;
    font-weight:700;
    letter-spacing:0.06em;
}
.status-pending   { background:#F6F1E8; color:#5F4A40; border:1px solid #D8C8B5; }
.status-composing { background:#EEF5F7; color:#4E6670; border:1px solid #C8DCE3; }
.status-rendering { background:#F1F0FA; color:#5B5A7A; border:1px solid #D8D6EE; }
.status-complete  { background:#EEF2EA; color:#46513E; border:1px solid #C9D3BF; }
.status-failed    { background:#FCE8E8; color:#8A3030; border:1px solid #E7A0A0; }
.subtitle-cue{
    background:var(--sangam-panel);
    border-left:3px solid var(--sangam-gold);
    border-radius:0 6px 6px 0;
    padding:0.5rem 1rem;
    margin:0.3rem 0;
    font-size:0.95rem;
}
.subtitle-time{
    color:var(--sangam-muted);
    font-size:0.8rem;
    font-family:monospace;
    margin-bottom:0.2rem;
}
.subtitle-en{ color:var(--sangam-dark); }
.subtitle-ta{ color:var(--sangam-terracotta); font-style:italic; }
.track-card{
    background:var(--sangam-panel);
    border:1px solid var(--sangam-border);
    border-radius:8px;
    padding:0.75rem 1rem;
    margin:0.4rem 0;
    display:flex;
    align-items:center;
    gap:1rem;
}
.track-scene-num{
    background:#E4E8D7;
    color:var(--sangam-dark);
    border-radius:50%;
    width:28px;
    height:28px;
    display:flex;
    align-items:center;
    justify-content:center;
    font-weight:700;
    font-size:0.85rem;
    flex-shrink:0;
}
.video-asset-row{
    display:flex;
    gap:0.5rem;
    flex-wrap:wrap;
    margin:0.5rem 0;
}
.asset-pill{
    background:var(--sangam-panel-soft);
    border:1px solid var(--sangam-border);
    border-radius:20px;
    padding:0.2rem 0.7rem;
    font-size:0.82rem;
    color:var(--sangam-muted);
}
.asset-pill.ready{ border-color:var(--sangam-green); color:#43502F; }
.asset-pill.missing{ border-color:#E7A0A0; color:#8A3030; }
@media (prefers-color-scheme: dark) {
    :root {
        --sangam-bg:#111827;
        --sangam-panel:#1F2937;
        --sangam-panel-soft:#263241;
        --sangam-panel-ai:#1B2430;
        --sangam-panel-scene:#263241;
        --sangam-terracotta:#C8B7A6;
        --sangam-terracotta-deep:#E5E7EB;
        --sangam-green:#A7B29A;
        --sangam-bronze:#C8B7A6;
        --sangam-ink:#F9FAFB;
        --sangam-muted:#CBD5E1;
        --sangam-border:#374151;
    }
    .stApp{background:var(--sangam-bg);}
    div[data-testid="stSidebar"]{background:#1F2937!important;}
    .stButton>button{color:#F9FAFB!important;background:#1F2937!important;border-color:#374151!important;}
    .stButton>button:hover{background:#263241!important;border-color:#4B5563!important;}
    .thinai-badge,.word-entry,.track-scene-num{background:#263241;color:#F9FAFB;}
    .asset-pill.ready{color:#DDE7CD;}
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
:root {
    --sangam-bg:#0D1016;
    --sangam-sidebar:#292A33;
    --sangam-panel:#180700;
    --sangam-panel-soft:#20100A;
    --sangam-panel-ai:#120600;
    --sangam-panel-scene:#171B22;
    --sangam-terracotta:#A66F3F;
    --sangam-terracotta-deep:#D8A057;
    --sangam-green:#A58F4C;
    --sangam-bronze:#8D6236;
    --sangam-ink:#F7F4EE;
    --sangam-dark:#FFFFFF;
    --sangam-muted:#A4794B;
    --sangam-border:#4B321F;
    --sangam-gold:#D3A006;
    --sangam-gold-soft:#E4BE43;
    --sangam-earth:#5B2A12;
    --sangam-accent:#FF4B5C;
}
html,body,[class*="css"],.stApp{
    background:var(--sangam-bg)!important;
    color:var(--sangam-ink)!important;
}
h1,h2,h3{
    color:var(--sangam-ink)!important;
    border-left:0!important;
    background:transparent!important;
    padding-left:0!important;
}
.stButton>button{
    background:var(--sangam-gold)!important;
    color:#05070B!important;
    border:1px solid var(--sangam-gold)!important;
    border-radius:6px!important;
    box-shadow:none!important;
}
.stButton>button:hover{
    background:var(--sangam-gold-soft)!important;
    color:#05070B!important;
    border-color:var(--sangam-gold-soft)!important;
}
.stTextArea textarea,
.stSelectbox>div>div{
    background:var(--sangam-panel)!important;
    color:var(--sangam-ink)!important;
    border-color:var(--sangam-border)!important;
}
.stTextArea textarea:focus{
    border-color:var(--sangam-gold)!important;
    box-shadow:0 0 0 1px rgba(211,160,6,0.35)!important;
}
div[data-testid="stSidebar"]{
    background:var(--sangam-sidebar)!important;
    border-right:1px solid #343541!important;
}
div[data-testid="stSidebar"] *{
    color:var(--sangam-ink)!important;
}
.sidebar-title{
    color:var(--sangam-gold-soft)!important;
    border-bottom:1px solid #50515A!important;
    letter-spacing:0.08em!important;
}
.sidebar-title small{
    color:#B9B1A7!important;
    letter-spacing:0!important;
}
.poetics-box,
.character-entry,
.meaning-entry,
.track-card,
.subtitle-cue{
    background:var(--sangam-panel)!important;
    color:var(--sangam-ink)!important;
    border:1px solid var(--sangam-border)!important;
    border-radius:6px!important;
    box-shadow:none!important;
}
.poem-card{
    background:var(--sangam-panel)!important;
    color:var(--sangam-ink)!important;
    border:1px solid var(--sangam-gold)!important;
    border-radius:8px!important;
    box-shadow:none!important;
}
.analysis-card{
    background:var(--sangam-panel)!important;
    color:var(--sangam-ink)!important;
    border:1px solid #211006!important;
    border-left:4px solid var(--sangam-gold)!important;
    border-radius:0 6px 6px 0!important;
    box-shadow:none!important;
}
.scene-header{
    background:var(--sangam-panel-scene)!important;
    color:var(--sangam-ink)!important;
    border-left:4px solid var(--sangam-gold)!important;
    border-bottom:1px solid var(--sangam-border)!important;
    border-radius:0 6px 6px 0!important;
    padding:0.45rem 0.75rem!important;
}
.thinai-badge,
.word-entry,
.track-scene-num,
.asset-pill,
.video-status-badge{
    background:var(--sangam-gold)!important;
    color:#120E05!important;
    border:1px solid var(--sangam-gold)!important;
}
.poetics-label,
.meaning-original,
.word-ta,
.video-header,
.subtitle-ta,
.asset-pill.ready{
    color:var(--sangam-gold-soft)!important;
}
.meaning-interpretation,
.poetics-value-ta,
.video-subheader,
.subtitle-time,
.asset-pill{
    color:var(--sangam-muted)!important;
}
.stTabs [data-baseweb="tab-list"]{
    background:#100700!important;
    border-bottom:1px solid var(--sangam-border)!important;
}
.stTabs [data-baseweb="tab"]{
    color:var(--sangam-muted)!important;
}
.stTabs [aria-selected="true"]{
    color:var(--sangam-gold-soft)!important;
    border-bottom-color:var(--sangam-accent)!important;
}
.stRadio label,
.stCheckbox label,
.stToggle label,
.stSelectbox label,
.stTextArea label,
.stFileUploader label,
.stCameraInput label{
    color:var(--sangam-ink)!important;
}
div[data-testid="stExpander"]{
    background:var(--sangam-panel-soft)!important;
    border:1px solid var(--sangam-border)!important;
}
div[data-testid="stChatMessage"]{
    background:var(--sangam-panel-soft)!important;
    color:var(--sangam-ink)!important;
}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span{
    color:inherit;
}
hr{border-color:var(--sangam-border)!important;}
</style>
""", unsafe_allow_html=True)


# ── HELPERS ──────────────────────────────────────────────────────────────────

@st.cache_data
def load_poems() -> list[Poem]:
    try:
        with open("poems.json", "r", encoding="utf-8") as f:
            return [Poem(**p) for p in json.load(f)]
    except Exception as e:
        st.warning(f"Could not load poems.json: {e}")
        return []


def find_library_poem(poem_id: int) -> Poem | None:
    if not poem_id:
        return None
    return next((poem for poem in load_poems() if poem.id == poem_id), None)


def analysis_from_poem(poem: Poem | None, poem_text: str = "") -> PoemAnalysis:
    if poem is None:
        fallback_lines = _meaning_breakdown_from_text(poem_text)
        return PoemAnalysis(
            summary="A compact Sangam-style reading is available in demo mode.",
            emotion="Reflective longing",
            thinai=Thinai.UNKNOWN,
            mood=Mood.LONGING,
            cultural_context="The poem is presented through the Sangam lens of landscape, emotion, and dramatic situation.",
            grammar_notes=_default_grammar_notes(Thinai.UNKNOWN),
            meaning_breakdown=fallback_lines,
        )

    mp = poem.muthal_porul
    muthal = MuthalPorul(
        landscape=mp.landscape if mp else "",
        season=mp.season if mp else "",
        time=mp.time if mp else "",
    ) if mp else None

    return PoemAnalysis(
        summary=(
            poem.cultural_context
            or "This poem binds landscape and emotion in the classical Sangam style."
        ),
        summary_tamil=poem.poem_ta,
        emotion=poem.meyppadu or "Longing",
        thinai=poem.thinai,
        mood=_mood_from_poem(poem),
        poet=poem.author,
        poet_tamil=poem.author_ta,
        collection=poem.collection,
        collection_tamil=poem.collection_ta,
        period=poem.period,
        akam_puram=poem.akam_puram,
        thurai=poem.thurai,
        speaker=poem.speaker,
        listener=poem.listener,
        muthal_porul=muthal,
        karu_porul=poem.karu_porul,
        uri_porul=poem.uri_porul,
        meyppadu=poem.meyppadu,
        cultural_context=poem.cultural_context,
        literary_devices="Thinai imagery, nature-symbolism, and implied emotional parallelism.",
        word_meanings=poem.word_meanings,
        grammar_notes=_grammar_notes_from_poem(poem),
        characters=_characters_from_poem(poem),
        meaning_breakdown=_meaning_breakdown_from_poem(poem),
    )


def _default_grammar_notes(thinai: Thinai) -> list[GrammarNote]:
    thinai_name = thinai.value if thinai != Thinai.UNKNOWN else "the poem"
    return [
        GrammarNote(
            term="Muthal",
            term_tamil="முதல்",
            definition="The time and place frame of a Sangam poem.",
            example=f"In {thinai_name}, landscape is not decoration; it sets the emotional world.",
        ),
        GrammarNote(
            term="Karu",
            term_tamil="கரு",
            definition="The living scene: flowers, animals, occupations, objects, and weather.",
            example="Natural details help the reader infer the speaker's inner state.",
        ),
        GrammarNote(
            term="Uri",
            term_tamil="உரி",
            definition="The central human situation or emotional action.",
            example="The poem's outer image points toward an inner experience of love, waiting, union, or separation.",
        ),
        GrammarNote(
            term="Ullurai",
            term_tamil="உள்ளுறை",
            definition="An embedded inner meaning carried through nature imagery.",
            example="The visible landscape quietly decodes the hidden feeling of the speaker.",
        ),
    ]


def _grammar_notes_from_poem(poem: Poem) -> list[GrammarNote]:
    notes = _default_grammar_notes(poem.thinai)
    if poem.thurai:
        notes.append(
            GrammarNote(
                term="Thurai",
                term_tamil="துறை",
                definition="The specific dramatic situation within a Thinai.",
                example=poem.thurai,
            )
        )
    if poem.meyppadu:
        notes.append(
            GrammarNote(
                term="Meyppadu",
                term_tamil="மெய்ப்பாடு",
                definition="The felt emotional expression made visible in the poem.",
                example=poem.meyppadu,
            )
        )
    return notes


def _characters_from_poem(poem: Poem) -> list[Character]:
    characters: list[Character] = []
    if poem.speaker:
        characters.append(
            Character(
                name=poem.speaker,
                role="Speaker",
                description="The voice through which the poem's emotional situation is revealed.",
            )
        )
    if poem.listener:
        characters.append(
            Character(
                name=poem.listener,
                role="Listener",
                description="The addressed presence who helps frame the poem's dramatic moment.",
            )
        )
    return characters


def _meaning_breakdown_from_text(poem_text: str) -> list[MeaningLine]:
    lines = [line.strip() for line in (poem_text or "").splitlines() if line.strip()]
    return [
        MeaningLine(
            original=line,
            translation=line,
            interpretation="This line contributes to the poem's emotional movement and image pattern.",
            literary_device="Line image",
        )
        for line in lines
    ]


def _meaning_breakdown_from_poem(poem: Poem) -> list[MeaningLine]:
    en_lines = [line.strip() for line in (poem.poem_en or "").splitlines() if line.strip()]
    ta_lines = [line.strip() for line in (poem.poem_ta or "").splitlines() if line.strip()]
    decoded: list[MeaningLine] = []

    for index, line in enumerate(en_lines):
        original = ta_lines[index] if index < len(ta_lines) else line
        decoded.append(
            MeaningLine(
                original=original,
                translation=line,
                interpretation=_line_interpretation(poem, line, index),
                literary_device=_line_device(poem, line),
            )
        )

    return decoded or _meaning_breakdown_from_text(poem.poem_ta or poem.poem_en)


def _line_interpretation(poem: Poem, line: str, index: int) -> str:
    lowered = line.lower()
    if index == 0:
        return f"The opening image establishes {poem.thinai.value} Thinai and prepares the emotional field."
    if any(word in lowered for word in ("like", "as ", "as i", "as my")):
        return "The comparison turns an outer image into a decoded inner feeling."
    if any(word in lowered for word in ("heart", "beloved", "lover", "longing", "waiting", "alone")):
        return "The human emotion comes forward here, revealing the poem's Uri Porul."
    if any(word in lowered for word in ("flower", "wave", "forest", "mountain", "shore", "rain", "sand", "road")):
        return "A natural detail functions as Karu Porul, carrying emotional meaning through landscape."
    return "This sentence advances the poem's dramatic situation and deepens its implied feeling."


def _line_device(poem: Poem, line: str) -> str:
    lowered = line.lower()
    if any(word in lowered for word in ("like", "as ")):
        return "Uvamai / simile"
    if any(word in lowered for word in ("flower", "wave", "forest", "mountain", "shore", "rain", "sand", "road", "heron", "peacock")):
        return "Ullurai / nature-symbolism"
    if poem.thinai != Thinai.UNKNOWN:
        return f"{poem.thinai.value} Thinai imagery"
    return "Poetic image"


def _ensure_deep_analysis_sections(
    analysis: PoemAnalysis,
    poem_text: str = "",
    library_poem: Poem | None = None,
) -> PoemAnalysis:
    """Keep the old rich analysis sections visible even when AI output is sparse."""
    if library_poem:
        if not analysis.grammar_notes:
            analysis.grammar_notes = _grammar_notes_from_poem(library_poem)
        if not analysis.characters:
            analysis.characters = _characters_from_poem(library_poem)
        if not analysis.meaning_breakdown:
            analysis.meaning_breakdown = _meaning_breakdown_from_poem(library_poem)
    else:
        if not analysis.grammar_notes:
            analysis.grammar_notes = _default_grammar_notes(analysis.thinai)
        if not analysis.meaning_breakdown:
            analysis.meaning_breakdown = _meaning_breakdown_from_text(poem_text)

    return analysis


def _mood_from_poem(poem: Poem) -> Mood:
    text = " ".join([poem.uri_porul, poem.meyppadu, poem.cultural_context]).lower()
    if any(word in text for word in ("joy", "union", "secret")):
        return Mood.JOY
    if any(word in text for word in ("waiting", "longing", "separation", "lament")):
        return Mood.LONGING
    if any(word in text for word in ("quarrel", "infidelity", "anger")):
        return Mood.ANGER
    if any(word in text for word in ("desert", "travel", "sorrow")):
        return Mood.SORROW
    return Mood.SERENITY


def demo_scene_frames(analysis: PoemAnalysis) -> list[SceneFrame]:
    thinai = analysis.thinai
    landscape = {
        Thinai.KURINJI: "misty mountain slopes, kurinji flowers, waterfall stone paths",
        Thinai.MULLAI: "rain-washed forest, jasmine vines, mango grove at dusk",
        Thinai.MARUTHAM: "fertile paddy fields, lotus ponds, village courtyards at dawn",
        Thinai.NEYTAL: "windy seashore, fishing boats, waves under a pale sky",
        Thinai.PALAI: "sun-struck wilderness, dry paths, lonely travel roads",
    }.get(thinai, "ancient Tamil landscape")
    color = ", ".join(THINAI_COLOR_PALETTE.get(thinai, THINAI_COLOR_PALETTE[Thinai.UNKNOWN]))

    return [
        SceneFrame(
            scene_id=1,
            title=f"{thinai.value} Landscape",
            description=f"The poem opens in a {landscape}. Nature establishes the emotional field before any character speaks.",
            mood=analysis.mood,
            thinai=thinai,
            visual_prompt=f"Ancient Tamil Sangam era {landscape}, cinematic painting, historically grounded clothing, soft atmospheric depth",
            characters=[],
            environment=landscape,
            lighting="soft dawn or dusk light",
            color_palette=color,
        ),
        SceneFrame(
            scene_id=2,
            title="Human Feeling",
            description=f"The {analysis.speaker or 'speaker'} carries the poem's emotion while the surrounding landscape quietly mirrors it.",
            mood=analysis.mood,
            thinai=thinai,
            visual_prompt=f"Sangam-era figure in {landscape}, expressive but restrained emotion, classical Tamil poetic atmosphere",
            characters=[analysis.speaker or "speaker"],
            environment=landscape,
            lighting="warm side light",
            color_palette=color,
        ),
        SceneFrame(
            scene_id=3,
            title="Poetic Resolution",
            description="The scene closes on the natural symbol that holds the poem's meaning: landscape, memory, and feeling become one image.",
            mood=analysis.mood,
            thinai=thinai,
            visual_prompt=f"Symbolic final frame of {landscape}, ancient Tamil Sangam mood, elegant cinematic composition",
            characters=[],
            environment=landscape,
            lighting="gentle fading light",
            color_palette=color,
        ),
    ]


def experience_scene_frames(
    base_scenes: list[SceneFrame],
    analysis: PoemAnalysis,
) -> list[SceneFrame]:
    """Build a richer visual sequence for the video experience."""
    thinai = analysis.thinai
    color = ", ".join(THINAI_COLOR_PALETTE.get(thinai, THINAI_COLOR_PALETTE[Thinai.UNKNOWN]))
    mood = analysis.mood

    beat_map: dict[Thinai, list[tuple[str, str, str]]] = {
        Thinai.KURINJI: [
            ("Mountain Opening", "Misty Kurinji hills and stone paths prepare the hidden meeting.", "kurinji hills waterfall mountain path"),
            ("Flowered Slope", "Kurinji flowers and mountain pools hold the freshness of secret love.", "kurinji flower mountain pool"),
            ("First Meeting", "The lovers come into the frame with restrained joy.", "lovers first meeting"),
            ("Moonlit Visit", "Night folds the hills into a private world.", "moonlit night visit"),
            ("Poetic Echo", "Water, flowers, and silence carry the poem's final feeling.", "waterfall kurinji landscape"),
        ],
        Thinai.MULLAI: [
            ("Forest Dusk", "Rain-washed Mullai forest settles into patient waiting.", "mullai forest monsoon"),
            ("Ayar Settlement", "Cattle paths and homes show the slow rhythm of return.", "ayar settlement cattle"),
            ("Waiting Path", "The heroine watches the forest path with quiet trust.", "heroine waiting forest path"),
            ("Twilight Return", "The returning figure nears the village under soft evening light.", "hero returns twilight"),
            ("Jasmine Rest", "Jasmine, deer, and dusk close the waiting with calm.", "jasmine deer mullai"),
        ],
        Thinai.MARUTHAM: [
            ("Paddy Dawn", "Fertile paddy fields open the Marutham world before the human conflict appears.", "marutham paddy fields"),
            ("Lotus Pond", "Lotus water and cranes mirror the poem's tenderness beneath tension.", "lotus pond crane dawn"),
            ("Village Courtyard", "The village courtyard brings the private quarrel into lived domestic space.", "marutham village courtyard home"),
            ("Domestic Quarrel", "The heroine's hurt is held in a restrained, Sangam-era domestic scene.", "domestic quarrel heroine"),
            ("Return Home", "The hero's return shifts the frame from accusation toward recognition.", "hero returning home"),
            ("Sugarcane Edge", "Fields and sugarcane keep the landscape alive between voices.", "sugarcane harvest field"),
            ("Reconciliation", "The landscape softens as memory and feeling settle into one image.", "marutham reconciliation lotus"),
        ],
        Thinai.NEYTAL: [
            ("Seashore Wind", "The shore opens with boats, waves, and pale distance.", "neytal seashore boats waves"),
            ("Waiting Tide", "The horizon carries separation and longing.", "shore longing waves"),
            ("Fishing Boats", "Life continues on the water while the heart remains unsettled.", "fishing boats sea"),
            ("Pale Horizon", "The far line of the sea becomes the poem's ache.", "neytal landscape horizon"),
            ("Wave Memory", "The waves close the scene with a returning emotional pulse.", "waves shore"),
        ],
        Thinai.PALAI: [
            ("Dry Road", "The Palai road opens under hard light and separation.", "palai dry road wilderness"),
            ("Travel Heat", "The journey stretches through sun and thorn.", "desert travel hardship"),
            ("Lonely Pause", "A single pause on the road carries fear and resolve.", "wilderness lonely path"),
            ("Distant Figure", "The traveller becomes small inside the harsh land.", "palai journey"),
            ("Heat Haze", "The final image leaves longing suspended in the hot distance.", "palai landscape"),
        ],
    }

    beats = beat_map.get(thinai)
    if not beats:
        return base_scenes or demo_scene_frames(analysis)

    scenes: list[SceneFrame] = []
    for index, (title, description, keywords) in enumerate(beats, start=1):
        scenes.append(
            SceneFrame(
                scene_id=index,
                title=title,
                description=description,
                mood=mood,
                thinai=thinai,
                visual_prompt=(
                    f"Ancient Tamil Sangam era {thinai.value} scene, {keywords}, "
                    "cinematic natural light, historically grounded clothing and landscape"
                ),
                characters=[analysis.speaker] if analysis.speaker and index in (3, 4, 5) else [],
                environment=keywords,
                lighting="cinematic dawn, dusk, or soft natural light",
                color_palette=color,
            )
        )

    return scenes


def demo_narration() -> NarrationResult | None:
    path = Path("assets/audio/analysis_narration.mp3")
    if not path.exists():
        return None
    return NarrationResult(
        audio_path=str(path),
        duration_seconds=18.0,
        language="en",
        success=True,
    )


def run_pipeline(
    poem_text: str,
    include_images: bool,
    include_audio: bool,
    include_video: bool,
    poem_id: int = 0,
    demo_mode: bool = False,
    target_language: str = "en",
) -> PipelineResult:
    result = PipelineResult(poem_text=poem_text)
    errors = []
    library_poem = find_library_poem(poem_id)

    if demo_mode:
        result.analysis = analysis_from_poem(library_poem, poem_text)
    else:
        with st.spinner("🧠 Pulavar is reading the poem..."):
            try:
                result.analysis = pulavar_ai.analyze_poem(poem_text)
                if not result.analysis or result.analysis.thinai == Thinai.UNKNOWN:
                    fallback = analysis_from_poem(library_poem, poem_text)
                    if fallback.thinai != Thinai.UNKNOWN:
                        result.analysis = fallback
            except Exception:
                errors.append("Analysis unavailable: using a reliable library reading for this poem.")
                result.analysis = analysis_from_poem(library_poem, poem_text)

    result.analysis = language_engine.improve_analysis_accuracy(
        result.analysis,
        poem_text=poem_text,
        library_poem=library_poem,
    )
    result.analysis = _ensure_deep_analysis_sections(
        result.analysis,
        poem_text=poem_text,
        library_poem=library_poem,
    )

    if demo_mode:
        result.scenes = demo_scene_frames(result.analysis)
    else:
        with st.spinner("🎬 Scene Weaver is composing scenes..."):
            try:
                result.scenes = scene_weaver.extract_scene_frames(result.analysis)
            except Exception:
                errors.append("Scene breakdown unavailable: showing curated Sangam scene frames.")
                result.scenes = demo_scene_frames(result.analysis)

    if not result.scenes:
        result.scenes = demo_scene_frames(result.analysis)

    narration_scenes = (
        experience_scene_frames(result.scenes, result.analysis)[:3]
        if include_video
        else result.scenes
    )

    if include_images and result.scenes:
        if demo_mode:
            result.images = resolve_video_images(result.scenes, [], result.analysis)
        else:
            with st.spinner("🖼️ Generating visual scenes..."):
                try:
                    result.images = scene_generator.generate_all_scenes(result.scenes)
                except Exception:
                    errors.append("Scene image generation unavailable: using curated image cache.")
                    result.images = resolve_video_images(result.scenes, [], result.analysis)

    if include_audio:
        if (
            demo_mode
            and target_language == "en"
            and os.getenv("DTEC_USE_BUNDLED_NARRATION") == "1"
        ):
            result.narration = demo_narration()
        else:
            with st.spinner("🔊 Sangam Voice is narrating..."):
                try:
                    narrate_fn = getattr(sangam_voice, "narrate_analysis", None)
                    if not narrate_fn:
                        raise AttributeError("narrate_analysis missing in sangam_voice.py")
                    result.narration = narrate_fn(
                        result.analysis,
                        narration_scenes,
                        target_language=target_language,
                    )
                    if result.narration and not result.narration.success:
                        result.narration = demo_narration() or result.narration
                except Exception:
                    errors.append("Narration unavailable: the text and scene experience are still ready.")
                    result.narration = demo_narration()

    # ── Video Experience ─────────────────────────────────────────────────────
    if include_video and _VIDEO_ENGINE_AVAILABLE:
        video_scenes = narration_scenes
        video_images = resolve_video_images(video_scenes, [], result.analysis)

        if not video_images:
            errors.append("Video skipped: no scene images were generated.")
        elif not result.narration or not result.narration.success:
            errors.append("Video skipped: narration is required. Enable voice narration in the sidebar.")
        else:
            with st.spinner("🎥 Composing Sangam Experience video..."):
                try:
                    result.video = video_engine.compose(
                        poem_id=poem_id,
                        title_en=getattr(result.analysis, "collection", "") or "Sangam Poem",
                        title_ta=getattr(result.analysis, "collection_tamil", "") or "",
                        thinai=result.analysis.thinai,
                        scenes=video_scenes,
                        images=video_images,
                        image_paths=[img.image_path for img in video_images],
                        narration=result.narration,
                        analysis=result.analysis,
                        target_language=target_language,
                    )
                    if result.video and not result.video.success:
                        errors.append(f"Video composition failed: {result.video.error}")
                except Exception as e:
                    errors.append(f"Video composition failed: {e}")
                    result.video = VideoExperience.failed(poem_id=poem_id, error=str(e))
    elif include_video and not _VIDEO_ENGINE_AVAILABLE:
        # Build the skeleton so the tab can show a "ready to render" state
        # even before video_engine.py is implemented.
        if result.images and result.narration and result.narration.success:
            result.video = VideoExperience.from_pipeline(
                poem_id=poem_id,
                title_en=getattr(result.analysis, "collection", "") or "Sangam Poem",
                title_ta=getattr(result.analysis, "collection_tamil", "") or "",
                thinai=result.analysis.thinai,
                images=resolve_video_images(narration_scenes, [], result.analysis),
                narration=result.narration,
                scenes=narration_scenes,
            )
            errors.append(
                "video_engine.py not found — VideoExperience skeleton built. "
                "Implement video_engine.compose() to enable ffmpeg rendering."
            )

    result.errors = errors
    result.success = len(errors) == 0
    return result


# ── DISPLAY: HELPERS ─────────────────────────────────────────────────────────

def _box(label: str, value_en: str, value_ta: str = "") -> str:
    ta_part = f'<div class="poetics-value-ta">{value_ta}</div>' if value_ta else ""
    return (
        f'<div class="poetics-box">'
        f'<div class="poetics-label">{label}</div>'
        f'<div class="poetics-value">{value_en}</div>'
        f'{ta_part}</div>'
    )


def get_cached_scene_image(scene: SceneFrame, analysis: PoemAnalysis | None = None) -> str | None:
    cache_keys = scene_weaver.select_cache_scene(scene, analysis)
    unique_keys = []
    seen = set()

    for cache_key in cache_keys:
        normalized = cache_key.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_keys.append(normalized)

    if not unique_keys:
        return None

    thinai_priority: list[str] = []
    if analysis and analysis.thinai == Thinai.KURINJI:
        thinai_priority = ["kurinji", "mullai", "marutham", "neytal", "palai"]
    elif analysis and analysis.thinai == Thinai.MULLAI:
        thinai_priority = ["mullai", "kurinji", "marutham", "neytal", "palai"]
    elif analysis and analysis.thinai == Thinai.MARUTHAM:
        thinai_priority = ["marutham", "mullai", "kurinji", "neytal", "palai"]
    elif analysis and analysis.thinai == Thinai.NEYTAL:
        thinai_priority = ["neytal", "kurinji", "mullai", "marutham", "palai"]
    elif analysis and analysis.thinai == Thinai.PALAI:
        thinai_priority = ["palai", "kurinji", "mullai", "marutham", "neytal"]

    thinai_pools = {
        "kurinji": set(KURINJI_CACHE_KEYS),
        "mullai": set(MULLAI_CACHE_KEYS),
        "marutham": set(MARUTHAM_CACHE_KEYS),
        "neytal": set(scene_weaver.NEYTAL_CACHE_KEYS),
        "palai": set(scene_weaver.PALAI_CACHE_KEYS),
    }

    available_images: list[str] = []
    checked_paths = set()

    def add_variants_for_key(key: str):
        for suffix in ("", "2", "3", "4"):
            variant = f"{key}{suffix}"
            if variant in SCENE_CACHE:
                path = SCENE_CACHE[variant]
                if path not in checked_paths and Path(path).exists():
                    available_images.append(path)
                    checked_paths.add(path)

    # First pass: exact scene / character / nature context matches.
    for key in unique_keys:
        add_variants_for_key(key)

    # Second pass: prefer same thinai pool if no exact image found yet.
    if not available_images and thinai_priority:
        for priority in thinai_priority:
            pool = thinai_pools.get(priority, set())
            for key in unique_keys:
                if key in pool:
                    add_variants_for_key(key)
            if available_images:
                break

    # Third pass: fallback to any candidate image built from the scene description.
    if not available_images:
        for key in unique_keys:
            if key in SCENE_CACHE:
                add_variants_for_key(key)

    # Final fallback: generic landscape images only if no scene-specific image exists.
    if not available_images:
        for key in ("kurinji_landscape", "mullai_landscape", "marutham_landscape", "neytal_landscape", "palai_landscape"):
            if key in SCENE_CACHE:
                add_variants_for_key(key)

    if not available_images:
        return None

    if len(available_images) == 1:
        return available_images[0]

    hash_input = (
        f"{scene.scene_id}|{scene.title}|{scene.description}|{scene.visual_prompt}"
    ).encode("utf-8")
    index = int(hashlib.md5(hash_input).hexdigest(), 16) % len(available_images)
    return available_images[index]


def resolve_video_images(
    scenes: list[SceneFrame],
    images: list[GeneratedImage],
    analysis: PoemAnalysis | None = None,
) -> list[GeneratedImage]:
    image_map = {
        img.scene_id: img
        for img in images
        if img.success and img.exists_on_disk()
    }
    video_images: list[GeneratedImage] = []

    for scene in scenes:
        image = image_map.get(scene.scene_id)
        if image:
            video_images.append(image)
            continue

        cached_path = get_cached_scene_image(scene, analysis)
        if cached_path:
            video_images.append(
                GeneratedImage(
                    scene_id=scene.scene_id,
                    image_path=cached_path,
                    prompt_used=scene.visual_prompt,
                    backend="scene-cache",
                )
            )

    return video_images


def stage_notices(result: PipelineResult, stage: str) -> list[str]:
    prefixes = {
        "analysis": ("Analysis unavailable",),
        "scenes": ("Scene breakdown unavailable", "Scene image generation unavailable"),
        "voice": ("Narration unavailable",),
        "video": ("Video skipped", "Video composition failed", "video_engine.py not found"),
    }
    wanted = prefixes.get(stage, ())
    return [err for err in result.errors if err.startswith(wanted)]


def render_stage_notices(result: PipelineResult, stage: str):
    for notice in stage_notices(result, stage):
        message = notice.split(":", 1)[0] if stage == "video" and "failed" in notice.lower() else notice
        st.caption(f"Note: {message}")


# ── DISPLAY: ANALYSIS ────────────────────────────────────────────────────────

def display_analysis(analysis: PoemAnalysis):
    st.markdown("## 🧠 Literary Analysis · இலக்கிய ஆய்வு")

    # OCR source badge
    if analysis.ocr_source:
        lang_label = {"tamil": "🇮🇳 Tamil", "english": "🇬🇧 English", "mixed": "🌐 Tamil + English"}.get(analysis.ocr_language, "")
        st.caption(f"📷 Analyzed from {analysis.ocr_source} image · {lang_label}")

    # Poet / Collection / Period
    if analysis.poet or analysis.collection:
        c1, c2, c3 = st.columns(3)
        with c1:
            if analysis.poet:
                st.markdown(_box("✍️ Poet / புலவர்", analysis.poet, analysis.poet_tamil), unsafe_allow_html=True)
        with c2:
            if analysis.collection:
                st.markdown(_box("📚 Collection / தொகை", analysis.collection, analysis.collection_tamil), unsafe_allow_html=True)
        with c3:
            parts = []
            if analysis.period:
                parts.append(analysis.period)
            if analysis.akam_puram:
                ta = "அகம்" if analysis.akam_puram == "Akam" else "புறம்"
                parts.append(f"{ta} ({analysis.akam_puram})")
            if parts:
                st.markdown(_box("🕰️ Period · காலம்", " · ".join(parts)), unsafe_allow_html=True)

    st.divider()

    # Thinai / Emotion / Mood
    c1, c2, c3 = st.columns(3)
    with c1:
        thinai_ta = THINAI_TAMIL.get(analysis.thinai, "")
        thinai_meaning = THINAI_MEANING.get(analysis.thinai, "")
        st.markdown(
            f"**தினை / Thinai:**<br>"
            f"<span class='thinai-badge'>{analysis.thinai.value} · {thinai_ta}</span><br>"
            f"<small style='color:var(--sangam-muted)'>{thinai_meaning}</small>",
            unsafe_allow_html=True
        )
    with c2:
        emo = analysis.emotion + (f" · {analysis.emotion_tamil}" if analysis.emotion_tamil else "")
        st.markdown(_box("உணர்வு / Emotion", emo), unsafe_allow_html=True)
    with c3:
        mood_ta = MOOD_TAMIL.get(analysis.mood, "")
        st.markdown(_box("மனநிலை / Mood", analysis.mood.value.capitalize(), mood_ta), unsafe_allow_html=True)

    st.divider()

    # Thurai / Speaker / Listener
    if analysis.thurai or analysis.speaker or analysis.listener:
        c1, c2, c3 = st.columns(3)
        with c1:
            if analysis.thurai:
                st.markdown(_box("துறை / Thurai", analysis.thurai, analysis.thurai_tamil), unsafe_allow_html=True)
        with c2:
            if analysis.speaker:
                st.markdown(_box("பேசுவோர் / Speaker", analysis.speaker), unsafe_allow_html=True)
        with c3:
            if analysis.listener:
                st.markdown(_box("கேட்போர் / Listener", analysis.listener), unsafe_allow_html=True)

    # Summary
    if analysis.summary:
        ta_part = f'<br><br><em style="color:var(--sangam-muted)">{analysis.summary_tamil}</em>' if analysis.summary_tamil else ""
        st.markdown(f'<div class="analysis-card"><strong>📖 Summary / சுருக்கம்</strong><br>{analysis.summary}{ta_part}</div>', unsafe_allow_html=True)

    target_language = st.session_state.get("target_language", "en")
    if target_language not in ("en", "ta"):
        learner_note = language_engine.learning_bridge_text(analysis, target_language)
        st.markdown(
            f'<div class="analysis-card"><strong>🌐 {language_engine.language_label(target_language)} Learner Guide</strong><br>{learner_note}</div>',
            unsafe_allow_html=True,
        )

    # Three-fold Poetics
    st.markdown("### 🌿 Sangam Poetics · முப்பொருள்")
    p1, p2, p3 = st.columns(3)

    with p1:
        st.markdown("**முதற்பொருள் · Muthal Porul**")
        st.caption("Time & Place")
        if analysis.muthal_porul:
            mp = analysis.muthal_porul
            if mp.landscape:
                st.markdown(f"🗻 **Landscape:** {mp.landscape}" + (f" · {mp.landscape_tamil}" if mp.landscape_tamil else ""))
            if mp.season:
                st.markdown(f"🌦️ **Season:** {mp.season}" + (f" · {mp.season_tamil}" if mp.season_tamil else ""))
            if mp.time:
                st.markdown(f"🕐 **Time:** {mp.time}" + (f" · {mp.time_tamil}" if mp.time_tamil else ""))

    with p2:
        st.markdown("**கருப்பொருள் · Karu Porul**")
        st.caption("Flora, Fauna & Objects")
        for item in analysis.karu_porul:
            st.markdown(f"• {item}")

    with p3:
        st.markdown("**உரிப்பொருள் · Uri Porul**")
        st.caption("Central Emotion/Action")
        if analysis.uri_porul:
            uri = analysis.uri_porul + (f"\n\n*{analysis.uri_porul_tamil}*" if analysis.uri_porul_tamil else "")
            st.info(uri)
        if analysis.meyppadu:
            st.markdown(f"**மெய்ப்பாடு:** {analysis.meyppadu}" + (f" · {analysis.meyppadu_tamil}" if analysis.meyppadu_tamil else ""))

    st.divider()

    # Cultural Context
    if analysis.cultural_context:
        ta_part = f'<br><br><em style="color:var(--sangam-muted)">{analysis.cultural_context_tamil}</em>' if analysis.cultural_context_tamil else ""
        st.markdown(f'<div class="analysis-card"><strong>🏛️ Cultural Context / பண்பாட்டு சூழல்</strong><br>{analysis.cultural_context}{ta_part}</div>', unsafe_allow_html=True)

    # Literary Devices
    if analysis.literary_devices:
        st.markdown(f'<div class="analysis-card"><strong>✦ Literary Devices / இலக்கண கோட்பாடுகள்</strong><br>{analysis.literary_devices}</div>', unsafe_allow_html=True)

    # Grammar Notes
    if analysis.grammar_notes:
        st.markdown("### 📐 Grammar Notes · இலக்கணக் குறிப்புகள்")
        for note in analysis.grammar_notes:
            term = note.term + (f" · {note.term_tamil}" if note.term_tamil else "")
            st.markdown(f'<div class="character-entry"><strong>{term}</strong><br><span style="color:var(--sangam-ink)">{note.definition}</span><br><span style="color:var(--sangam-muted)"><em>In this poem: {note.example}</em></span></div>', unsafe_allow_html=True)

    # Word Meanings
    if analysis.word_meanings:
        st.markdown("### 🔤 Word Meanings · சொற்பொருள்")
        for word, meaning in analysis.word_meanings.items():
            st.markdown(f'<div class="word-entry"><span class="word-ta">{word}</span><span class="word-en">{meaning}</span></div>', unsafe_allow_html=True)

    # Characters
    if analysis.characters:
        st.markdown("### 👤 Characters · கதாபாத்திரங்கள்")
        for char in analysis.characters:
            name = char.name + (f" · {char.name_tamil}" if char.name_tamil else "")
            role = char.role + (f" · {char.role_tamil}" if char.role_tamil else "")
            st.markdown(f'<div class="character-entry"><strong>{name}</strong> — <em>{role}</em><br><span style="color:var(--sangam-muted)">{char.description}</span></div>', unsafe_allow_html=True)

    # Meaning Breakdown
    if analysis.meaning_breakdown:
        st.markdown("### 📜 Meaning Breakdown · பொருள் விளக்கம்")
        for entry in analysis.meaning_breakdown:
            device = f' <span style="color:var(--sangam-muted);font-size:0.85rem">[{entry.literary_device}]</span>' if entry.literary_device else ""
            st.markdown(f'<div class="meaning-entry"><div class="meaning-original">"{entry.original}"{device}</div><div class="meaning-translation">→ {entry.translation}</div><div class="meaning-interpretation">✦ {entry.interpretation}</div></div>', unsafe_allow_html=True)


# ── DISPLAY: SCENES ──────────────────────────────────────────────────────────

def display_scenes(
    scenes: list[SceneFrame],
    images: list,
    analysis: PoemAnalysis
):
    st.markdown("## 🎬 Scene Breakdown")
    image_map = {img.scene_id: img for img in images} if images else {}

    for scene in scenes:
        with st.expander(f"Scene {scene.scene_id}: {scene.title or scene.description[:50]}...", expanded=True):
            c1, c2 = st.columns([3, 2])
            with c1:
                st.markdown(f'<div class="scene-header">Scene {scene.scene_id} · {scene.mood.value.capitalize()}</div>', unsafe_allow_html=True)
                st.write(scene.description)
                with st.expander("🔍 Advanced Details", expanded=False):
                    st.markdown(f"🌿 Environment: {scene.environment}")
                    st.markdown(f"☀️ Lighting: {scene.lighting}")
                    st.markdown(f"🎨 Palette: {scene.color_palette}")

                    if scene.characters:
                        st.markdown(
                            f"👤 Characters: {', '.join(scene.characters)}"
                        )

                    st.code(scene.visual_prompt)
            with c2:
                img = image_map.get(scene.scene_id)
                image_path = None

                if img and img.success and img.image_path and Path(img.image_path).exists():
                    if getattr(img, "backend", "") == "placeholder":
                        image_path = get_cached_scene_image(scene, analysis) or img.image_path
                    else:
                        image_path = img.image_path

                if not image_path or not Path(image_path).exists():
                    image_path = get_cached_scene_image(scene, analysis)

                if image_path and Path(image_path).exists():
                    try:
                        st.image(
                            image_path,
                            use_container_width=True,
                            caption=f"Scene {scene.scene_id} · {Path(image_path).name}"
                        )
                    except Exception:
                        st.info("Image unavailable.")
                else:
                    st.markdown(
                            '''
                            <div style="
                                background:var(--sangam-panel);
                                border:1px dashed var(--sangam-border);
                                border-radius:8px;
                                padding:3rem;
                                text-align:center;
                                color:var(--sangam-muted);
                            ">
                                🖼️<br>
                                Illustration unavailable
                            </div>
                            ''',
                            unsafe_allow_html=True
                        )

# ── DISPLAY: NARRATION ───────────────────────────────────────────────────────

def display_narration(narration):
    st.markdown("## 🔊 Sangam Voice")
    if narration and narration.success and narration.audio_path:
        try:
            audio_path = Path(narration.audio_path)
            if audio_path.exists():
                with open(audio_path, "rb") as f:
                    st.audio(f.read(), format="audio/mp3")
            else:
                st.info("Narration audio is being prepared for this poem.")
        except Exception:
            st.info("Narration audio could not be played here, but the analysis remains available.")
    elif narration and not narration.success:
        st.markdown(
            '<div class="error-card">🔇 Narration is unavailable for this run.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("Enable narration in the sidebar to hear the poem.")


# ── DISPLAY: VIDEO EXPERIENCE ────────────────────────────────────────────────

def _status_badge(status: VideoStatus) -> str:
    label = status.value.upper()
    css   = f"status-{status.value}"
    return f'<span class="video-status-badge {css}">{label}</span>'


def _asset_pill(label: str, ready: bool) -> str:
    cls = "ready" if ready else "missing"
    icon = "✓" if ready else "✗"
    return f'<span class="asset-pill {cls}">{icon} {label}</span>'


def display_video_experience(result: PipelineResult):
    """
    Renders the 🎥 Sangam Experience tab.

    States handled:
      1. Video disabled in sidebar   → prompt to enable
      2. video_engine not available  → show skeleton + instructions
      3. Video failed                → show error card
      4. Video complete              → play video + subtitles + downloads
      5. Video pending/composing     → show progress info
    """
    st.markdown(
        '<div class="video-header">🎥 Sangam Experience · சங்க அனுபவம்</div>'
        '<div class="video-subheader">All scenes · narration · subtitles — woven into one cinematic poem</div>',
        unsafe_allow_html=True,
    )

    # ── State 1: disabled ────────────────────────────────────────────────────
    if result.video is None:
        st.markdown("""
        <div style='text-align:center;padding:3rem 2rem;background:var(--sangam-panel);
        border:1px dashed var(--sangam-border);border-radius:10px;'>
            <div style='font-size:3rem;margin-bottom:1rem;'>🎥</div>
            <div style='font-family:"Playfair Display",serif;color:var(--sangam-ink);font-size:1.2rem;margin-bottom:0.5rem;'>
                Experience not generated
            </div>
            <div style='color:var(--sangam-muted);font-size:0.95rem;max-width:420px;margin:0 auto;'>
                Enable <strong style='color:var(--sangam-ink)'>Generate Experience video</strong>,
                <strong style='color:var(--sangam-ink)'>Generate scene images</strong>, and
                <strong style='color:var(--sangam-ink)'>Generate voice narration</strong>
                in the sidebar, then re-analyze the poem.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    exp = result.video

    # ── Header row: title + status badge ─────────────────────────────────────
    h_col, s_col = st.columns([4, 1])
    with h_col:
        title = exp.poem_title_en or "Sangam Poem"
        thinai_ta = THINAI_TAMIL.get(exp.thinai, "")
        st.markdown(
            f"**{title}** &nbsp;·&nbsp; "
            f"<span class='thinai-badge'>{exp.thinai.value} · {thinai_ta}</span>",
            unsafe_allow_html=True,
        )
    with s_col:
        st.markdown(_status_badge(exp.status), unsafe_allow_html=True)

    # Asset availability pills
    images_ready  = any(t.image_path and Path(t.image_path).exists() for t in exp.tracks)
    audio_ready   = bool(exp.audio_path) and Path(exp.audio_path).exists()
    subs_ready    = len(exp.subtitles) > 0
    video_ready   = exp.exists_on_disk()

    st.markdown(
        '<div class="video-asset-row">'
        + _asset_pill(f"{len(exp.tracks)} scenes", images_ready)
        + _asset_pill("narration audio", audio_ready)
        + _asset_pill("subtitles", subs_ready)
        + _asset_pill("video file", video_ready)
        + "</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    # ── State 3: failed ───────────────────────────────────────────────────────
    if exp.status == VideoStatus.FAILED or not exp.success:
        st.markdown("""
        <div style="
            background:var(--sangam-panel);
            border:1px solid var(--sangam-border);
            border-radius:12px;
            padding:2rem;
            text-align:center;
            color:var(--sangam-muted);
            margin-top:1rem;
        ">
            <div style="font-size:2rem;">🎞️</div>
            <h3>Experience Unavailable</h3>
            <p>
                Scene images could not be assembled into a video for this poem.
            </p>
            <small>
                Analysis, scenes, and narration remain fully available.
            </small>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── State 4: complete — play video ───────────────────────────────────────
    if exp.status == VideoStatus.COMPLETE and video_ready:
        vid_col, sub_col = st.columns([3, 2])

        with vid_col:
            st.markdown("### ▶ Play")
            with open(exp.video_path, "rb") as vf:
                st.video(vf.read())

            # Thinai color palette swatch
            palette = THINAI_COLOR_PALETTE.get(exp.thinai, [])
            if palette:
                swatches = "".join(
                    f'<span style="display:inline-block;width:24px;height:24px;'
                    f'border-radius:4px;background:{c};margin-right:4px;"></span>'
                    for c in palette
                )
                st.markdown(
                    f'<div style="margin-top:0.5rem;">'
                    f'<small style="color:var(--sangam-muted)">Thinai palette &nbsp;</small>{swatches}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Video metadata
            meta_cols = st.columns(4)
            meta_cols[0].metric("Scenes",      len(exp.tracks))
            meta_cols[1].metric("Duration",    f"{exp.total_duration:.0f}s")
            meta_cols[2].metric("Resolution",  exp.resolution)
            meta_cols[3].metric("Render time", f"{exp.render_time_sec:.1f}s")

        with sub_col:
            _render_subtitles_panel(exp)

        st.divider()
        _render_download_row(exp)
        _render_video_scene_strip(exp, result)
        return

    # ── State 2 / 5: skeleton or in-progress ─────────────────────────────────
    if not _VIDEO_ENGINE_AVAILABLE:
        st.info(
            "**video_engine.py not found.** "
            "The VideoExperience skeleton is built — implement `video_engine.compose()` "
            "to enable ffmpeg rendering. See `schemas.VideoExperience` for the full spec."
        )
    else:
        st.info(f"Video status: **{exp.status.value}** — {exp.progress_summary()}")

    # Show scene strip even without a rendered video
    _render_video_scene_strip(exp, result)

    # Show timeline even without a rendered video
    if exp.tracks:
        st.markdown("### 🎞 Track Timeline")
        for track in exp.tracks:
            scene_title = track.overlay_text or f"Scene {track.scene_id}"
            bar_width   = max(int((track.duration_seconds / max(exp.total_duration, 1)) * 100), 4)
            st.markdown(
                f'<div class="track-card">'
                f'<div class="track-scene-num">{track.scene_id}</div>'
                f'<div style="flex:1;">'
                f'<div style="font-size:0.9rem;color:var(--sangam-dark);margin-bottom:0.3rem;">{scene_title}</div>'
                f'<div style="background:var(--sangam-border);border-radius:4px;height:8px;width:100%;">'
                f'<div style="background:var(--sangam-gold);border-radius:4px;height:8px;width:{bar_width}%;"></div>'
                f'</div>'
                f'<div style="font-size:0.78rem;color:var(--sangam-muted);margin-top:0.2rem;">'
                f'{track.start_seconds:.1f}s → {track.end_seconds:.1f}s &nbsp;·&nbsp; '
                f'{track.transition} &nbsp;·&nbsp; '
                f'{"Ken Burns ✓" if track.ken_burns else "static"}'
                f'</div></div></div>',
                unsafe_allow_html=True,
            )

    # SRT preview even without rendered video
    if exp.subtitles:
        _render_subtitles_panel(exp)


def _render_subtitles_panel(exp: VideoExperience):
    """Subtitle viewer with SRT / VTT export tabs."""
    st.markdown("### 📝 Subtitles · வசனங்கள்")

    if not exp.subtitles:
        st.caption("No subtitle cues yet.")
        return

    view_tab, srt_tab, vtt_tab = st.tabs(["👁 Preview", "📄 SRT", "🌐 VTT"])

    with view_tab:
        for cue in exp.subtitles:
            def fmt_ts(s: float) -> str:
                m, sec = divmod(int(s), 60)
                return f"{m:02d}:{sec:02d}.{int((s % 1) * 10)}"

            lines = []
            if cue.text_en: lines.append(f'<div class="subtitle-en">{cue.text_en}</div>')
            if cue.text_ta: lines.append(f'<div class="subtitle-ta">{cue.text_ta}</div>')
            speaker_badge = (
                f'<span style="color:var(--sangam-muted);font-size:0.78rem;">{cue.speaker}</span> &nbsp;'
                if cue.speaker else ""
            )
            st.markdown(
                f'<div class="subtitle-cue">'
                f'<div class="subtitle-time">{speaker_badge}'
                f'{fmt_ts(cue.start_seconds)} → {fmt_ts(cue.end_seconds)}</div>'
                + "".join(lines)
                + "</div>",
                unsafe_allow_html=True,
            )

    with srt_tab:
        srt_content = exp.export_srt()
        st.text_area("SRT content", srt_content, height=300, label_visibility="collapsed")

    with vtt_tab:
        vtt_content = exp.export_vtt()
        st.text_area("VTT content", vtt_content, height=300, label_visibility="collapsed")


def _render_download_row(exp: VideoExperience):
    """Download buttons for video + subtitle files."""
    st.markdown("### ⬇ Downloads")
    dl_cols = st.columns(4)

    with dl_cols[0]:
        if exp.exists_on_disk():
            with open(exp.video_path, "rb") as vf:
                st.download_button(
                    "🎥 Video (.mp4)",
                    data=vf.read(),
                    file_name=Path(exp.video_path).name,
                    mime="video/mp4",
                    use_container_width=True,
                )

    with dl_cols[1]:
        if exp.subtitle_path_srt and Path(exp.subtitle_path_srt).exists():
            with open(exp.subtitle_path_srt, "rb") as sf:
                st.download_button(
                    "📄 Subtitles (.srt)",
                    data=sf.read(),
                    file_name=Path(exp.subtitle_path_srt).name,
                    mime="text/plain",
                    use_container_width=True,
                )
        elif exp.subtitles:
            st.download_button(
                "📄 Subtitles (.srt)",
                data=exp.export_srt().encode("utf-8"),
                file_name=f"poem_{exp.poem_id}.srt",
                mime="text/plain",
                use_container_width=True,
            )

    with dl_cols[2]:
        if exp.subtitle_path_vtt and Path(exp.subtitle_path_vtt).exists():
            with open(exp.subtitle_path_vtt, "rb") as vf:
                st.download_button(
                    "🌐 Subtitles (.vtt)",
                    data=vf.read(),
                    file_name=Path(exp.subtitle_path_vtt).name,
                    mime="text/vtt",
                    use_container_width=True,
                )
        elif exp.subtitles:
            st.download_button(
                "🌐 Subtitles (.vtt)",
                data=exp.export_vtt().encode("utf-8"),
                file_name=f"poem_{exp.poem_id}.vtt",
                mime="text/vtt",
                use_container_width=True,
            )

    with dl_cols[3]:
        if exp.thumbnail_path and Path(exp.thumbnail_path).exists():
            with open(exp.thumbnail_path, "rb") as tf:
                st.download_button(
                    "🖼 Thumbnail",
                    data=tf.read(),
                    file_name=Path(exp.thumbnail_path).name,
                    mime="image/jpeg",
                    use_container_width=True,
                )


def _render_video_scene_strip(exp: VideoExperience, result: PipelineResult):
    """
    Horizontal filmstrip of scene thumbnails with track timing labels.
    Shown regardless of whether the video is rendered.
    """
    if not exp.tracks:
        return

    st.markdown("### 🎞 Scene Strip")
    image_map = {img.scene_id: img for img in result.images} if result.images else {}
    scene_map = {s.scene_id: s for s in result.scenes} if result.scenes else {}

    cols = st.columns(len(exp.tracks))
    for col, track in zip(cols, exp.tracks):
        with col:
            # Resolve image: prefer track path → generated image → cached fallback
            img_path = None
            if track.image_path and Path(track.image_path).exists():
                img_path = track.image_path
            else:
                gen_img = image_map.get(track.scene_id)
                if gen_img and gen_img.success and gen_img.image_path and Path(gen_img.image_path).exists():
                    img_path = gen_img.image_path
                else:
                    scene = scene_map.get(track.scene_id)
                    if scene:
                        img_path = get_cached_scene_image(scene, result.analysis)

            if img_path and Path(img_path).exists():
                st.image(img_path, use_container_width=True)
            else:
                st.markdown(
                    '<div style="background:var(--sangam-panel);border:1px dashed var(--sangam-border);'
                    'border-radius:6px;padding:1.5rem;text-align:center;'
                    'color:var(--sangam-muted);font-size:0.8rem;">🖼️</div>',
                    unsafe_allow_html=True,
                )

            label = track.overlay_text or f"Scene {track.scene_id}"
            st.caption(f"{label}\n{track.start_seconds:.0f}s–{track.end_seconds:.0f}s")


# ── DISPLAY: CHATBOT ─────────────────────────────────────────────────────────

def display_chatbot(analysis: PoemAnalysis | None):
    st.markdown("## 🗣️ Ask Pulavar")
    st.caption("Ask the ancient scholar anything about Sangam poetry, culture, or this poem.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("Ask Pulavar a question...")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)
        with st.chat_message("assistant"):
            with st.spinner("Pulavar reflects..."):
                response = pulavar_ai.ask_pulavar(user_input, context=analysis)
            st.write(response)
        st.session_state.chat_history.append({"role": "assistant", "content": response})


# ── SIDEBAR ──────────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.markdown(
            "<div class='sidebar-title'>Living Sangam World<br><small>AI-Powered Immersive Tamil Poetry Experience</small></div>",
            unsafe_allow_html=True,
        )
        st.markdown("")

        poem_source = st.radio(
            "Poem source",
            ["✍️ Type / Paste", "📚 Library", "📷 Camera / Image"],
            index=1,
            horizontal=False,
        )

        poem_text = ""
        poem_id   = 0   # track selected poem id for output file naming

        # ── MODE 1: Type / Paste ─────────────────────────────
        if poem_source == "✍️ Type / Paste":
            poem_text = st.text_area(
                "Enter Sangam poem", height=200,
                placeholder="Paste Tamil or English poem here...",
            )

        # ── MODE 2: Library ──────────────────────────────────
        elif poem_source == "📚 Library":
            poems = load_poems()
            if poems:
                titles = [f"{p.id}. {p.title_en} · {p.title_ta} ({p.thinai.value})" for p in poems]
                idx = st.selectbox("Select a poem", range(len(poems)), format_func=lambda i: titles[i])
                p = poems[idx]
                poem_text = p.poem_en
                poem_id   = p.id

                show_tamil = st.toggle("Show Tamil version", value=False)
                display_poem = p.poem_ta if (show_tamil and p.poem_ta) else p.poem_en
                st.markdown(f'<div class="poem-card">{display_poem.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)

                meta = []
                if p.author_ta:    meta.append(f"✍️ {p.author} · {p.author_ta}")
                if p.collection_ta: meta.append(f"📚 {p.collection} · {p.collection_ta}")
                if meta: st.caption(" | ".join(meta))

                with st.expander("📐 Poetic Structure"):
                    if p.thurai:   st.markdown(f"**துறை / Thurai:** {p.thurai}")
                    if p.speaker:  st.markdown(f"**Speaker:** {p.speaker}  |  **Listener:** {p.listener}")
                    if p.muthal_porul:
                        mp = p.muthal_porul
                        st.markdown(f"**முதல்:** {mp.landscape}, {mp.season}, {mp.time}")
                    if p.karu_porul: st.markdown(f"**கரு:** {', '.join(p.karu_porul[:3])}")
                    if p.uri_porul:  st.markdown(f"**உரி:** {p.uri_porul}")
                    if p.meyppadu:   st.markdown(f"**மெய்ப்பாடு:** {p.meyppadu}")

                if p.word_meanings:
                    with st.expander("🔤 Word Meanings"):
                        for word, meaning in p.word_meanings.items():
                            st.markdown(f"**{word}** — {meaning}")
            else:
                st.warning("No poems found in poems.json")

        # ── MODE 3: Camera / Image OCR ───────────────────────
        elif poem_source == "📷 Camera / Image":
            st.markdown(
                "<small style='color:var(--sangam-muted)'>Take a photo of a poem — from a book, "
                "manuscript, or handwritten note — and we'll read the text for you.</small>",
                unsafe_allow_html=True
            )
            st.markdown("")

            camera_image = st.camera_input("📸 Take a photo")
            st.markdown("<div style='text-align:center;color:var(--sangam-muted);font-size:0.85rem'>— or —</div>", unsafe_allow_html=True)
            uploaded_file = st.file_uploader(
                "📁 Upload an image", type=["jpg", "jpeg", "png", "webp"],
                label_visibility="collapsed"
            )

            image_source = camera_image or uploaded_file

            if image_source is not None:
                st.image(image_source, caption="Image to scan", use_container_width=True)

                if st.button("🔍 Extract Poem Text", use_container_width=True):
                    with st.spinner("📖 Reading the image with Gemini Vision..."):
                        try:
                            img_bytes, mime_type = ocr_engine.image_bytes_from_upload(image_source)
                            extracted, lang = ocr_engine.extract_text_from_image(img_bytes, mime_type)
                            if extracted.strip():
                                st.session_state["ocr_text"] = extracted
                                st.session_state["ocr_lang"] = lang
                                st.session_state["ocr_source"] = "camera" if camera_image else "upload"
                                st.success(f"✅ Text extracted! ({lang.capitalize()} detected)")
                            else:
                                st.warning("No text found. Try a clearer photo.")
                        except Exception as exc:
                            reason = str(exc) or exc.__class__.__name__
                            if "GEMINI_API_KEY" in reason or "GOOGLE_API_KEY" in reason:
                                st.error("OCR is not configured yet. Add GEMINI_API_KEY to your .env file, then restart the app.")
                            elif "empty" in reason.lower() or "readable image" in reason.lower():
                                st.error("OCR could not read this image file. Try uploading a JPG/PNG photo again.")
                            else:
                                st.error("OCR could not read this image. Try a clearer photo or paste the poem text.")
                                st.caption(f"OCR detail: {reason[:240]}")

            if st.session_state.get("ocr_text"):
                lang = st.session_state.get("ocr_lang", "unknown")
                lang_label = {"tamil": "🇮🇳 Tamil", "english": "🇬🇧 English", "mixed": "🌐 Tamil + English"}.get(lang, "")
                st.markdown(f"**Extracted text** {lang_label}")
                edited = st.text_area(
                    "Edit if needed",
                    value=st.session_state["ocr_text"],
                    height=180, label_visibility="collapsed",
                )
                poem_text = edited
                if st.button("🗑️ Clear", use_container_width=False):
                    for key in ["ocr_text", "ocr_lang", "ocr_source"]:
                        st.session_state.pop(key, None)
                    st.rerun()
            else:
                st.markdown(
                    "<div style='background:var(--sangam-panel);border:1px dashed var(--sangam-border);border-radius:8px;"
                    "padding:1.5rem;text-align:center;color:var(--sangam-muted);margin-top:0.5rem;'>"
                    "📷 Take or upload a photo above<br>"
                    "<small>Works with books, screens, or handwritten poems</small></div>",
                    unsafe_allow_html=True
                )

        # ── Options & Run ────────────────────────────────────
        st.divider()
        st.markdown("### ⚙️ Options")
        demo_mode = st.toggle(
            "Demo judging mode",
            value=True,
            help="Uses curated library analysis, cached scene images, and bundled narration for a reliable live demo.",
        )
        st.markdown("### Learning")
        language_options = language_engine.language_choices()
        target_language = st.selectbox(
            "Narration and subtitle language",
            options=[code for code, _ in language_options],
            index=1,
            format_func=language_engine.language_label,
            help="Tamil terms stay visible; narration and learner captions follow this language.",
        )
        include_images = st.toggle("Generate scene images",    value=True)
        include_audio  = st.toggle("Generate voice narration", value=demo_mode)

        # Video toggle — only shown when both images and audio can be active
        include_video  = st.toggle(
            "Generate Experience video 🎥",
            value=False,
            help=(
                "Composes all scene images + narration + subtitles into a single .mp4 per poem. "
                "Requires scene images AND voice narration to be enabled. "
                "Uses ffmpeg via video_engine.py."
            ),
        )

        if include_video and not include_images:
            st.caption("⚠️ Scene images must be enabled for video.")
        if include_video and not include_audio:
            st.caption("⚠️ Voice narration must be enabled for video.")

        st.divider()
        run_btn = st.button("✦ Analyze Poem", use_container_width=True)
        st.caption("Living Sangam World: AI-Powered Immersive Tamil Poetry Experience")

    return poem_text, poem_id, include_images, include_audio, include_video, demo_mode, target_language, run_btn


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    st.markdown("""
        <h1 style='text-align:center;font-size:2.6rem;letter-spacing:0;
        color:var(--sangam-gold-soft);padding:1rem 0 0.2rem;'>
            Living Sangam World
        </h1>
        <p style='text-align:center;color:var(--sangam-muted);font-family:"Playfair Display",serif;
        font-size:1rem;letter-spacing:0.35em;margin-bottom:2rem;text-transform:uppercase;'>
            AI-Powered Immersive Tamil Poetry Experience
        </p>
    """, unsafe_allow_html=True)

    if _api_key_missing:
        st.error("⚠️ **GEMINI_API_KEY not found.** Add it to your `.env` file.")

    poem_text, poem_id, include_images, include_audio, include_video, demo_mode, target_language, run_btn = render_sidebar()

    if "pipeline_result" not in st.session_state:
        st.session_state.pipeline_result = None

    if run_btn:
        if not poem_text or not poem_text.strip():
            st.error("Please enter a poem to analyze.")
        else:
            result = run_pipeline(
                poem_text.strip(),
                include_images,
                include_audio,
                include_video,
                poem_id=poem_id,
                demo_mode=demo_mode,
                target_language=target_language,
            )
            st.session_state["target_language"] = target_language
            # Tag the analysis with OCR source if it came from camera/image
            if st.session_state.get("ocr_source"):
                result.analysis.ocr_source   = st.session_state["ocr_source"]
                result.analysis.ocr_language = st.session_state.get("ocr_lang", "")
            st.session_state.pipeline_result = result

    result = st.session_state.pipeline_result

    if result is None:
        st.markdown("""
        <div style='text-align:center;padding:4rem 2rem;'>
            <div style='font-size:4rem;margin-bottom:1rem;'>🌿</div>
            <div style='font-family:"Playfair Display",serif;font-size:1.4rem;color:var(--sangam-ink);margin-bottom:1rem;'>
                Enter a Sangam poem to begin
            </div>
            <div style='font-size:1rem;color:var(--sangam-muted);max-width:500px;margin:0 auto;font-style:italic;'>
                "As the kurinji flower blooms on the mountain slopes,<br>
                so does the meaning of ancient verse unfold<br>
                to those who look deeply."
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📜 Analysis",
        "🎬 Scenes",
        "🔊 Voice",
        "🎥 Experience",
        "🗣️ Ask Pulavar",
    ])
    with tab1:
        render_stage_notices(result, "analysis")
        display_analysis(result.analysis)
    with tab2:
        render_stage_notices(result, "scenes")
        display_scenes(result.scenes, result.images, result.analysis)
    with tab3:
        render_stage_notices(result, "voice")
        display_narration(result.narration)
    with tab4:
        render_stage_notices(result, "video")
        display_video_experience(result)
    with tab5: display_chatbot(result.analysis)


if __name__ == "__main__":
    main()
