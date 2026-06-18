"""
gemini_client.py — Centralized Gemini client.
Single place to initialize and get the model.
All modules import from here — no duplicate genai.configure() calls.
"""

import os
import time

# Free tier models in order of stability — most reliable first
MODELS_TO_TRY = [
    "gemini-1.5-flash",      # Most stable free tier
    "gemini-2.0-flash",      # Second choice
    "gemini-2.5-flash",      # Often overloaded, last resort
]

_api_key = None


def _get_api_key():
    global _api_key
    if _api_key is None:
        _api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not _api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY not found. "
                "Add it to your .env file: GEMINI_API_KEY=your_key_here"
            )
    return _api_key


class _SmartModel:
    """
    Drop-in replacement for GenerativeModel.
    Tries multiple models with retry — existing code needs zero changes.
    """
    def generate_content(self, prompt: str):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("Run: pip install google-generativeai")

        genai.configure(api_key=_get_api_key())
        last_error = None

        for model_name in MODELS_TO_TRY:
            for attempt in range(1, 4):
                try:
                    print(f"[gemini] Trying {model_name} (attempt {attempt}/3)...")
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    print(f"[gemini] ✅ {model_name} succeeded.")
                    return response
                except Exception as e:
                    last_error = e
                    err = str(e)
                    if any(x in err for x in ["503", "UNAVAILABLE", "high demand"]):
                        wait = 5 * attempt
                        print(f"[gemini] ⏳ Overloaded, waiting {wait}s...")
                        time.sleep(wait)
                    elif any(x in err for x in ["429", "quota", "rate"]):
                        print(f"[gemini] ⚠️ Quota hit on {model_name}, trying next...")
                        break  # try next model immediately
                    elif any(x in err for x in ["404", "not found"]):
                        print(f"[gemini] ⚠️ {model_name} unavailable, skipping...")
                        break
                    else:
                        print(f"[gemini] 🚨 Unexpected error: {err[:150]}")
                        break

        raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")


def get_model() -> _SmartModel:
    """
    Returns a smart model wrapper.
    Drop-in for genai.GenerativeModel — same .generate_content() interface.
    """
    return _SmartModel()