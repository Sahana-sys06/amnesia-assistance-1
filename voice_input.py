import streamlit.components.v1 as components
from pathlib import Path

voice_commands = components.declare_component(
    "amnesia_voice_commands", path=str(Path(__file__).resolve().parent / "voice_component")
)
