from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import cv2
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from voice_input import voice_commands
from hardware import available_ports, connect as connect_esp32, send_line, read_lines

from face_tools import collect_sample, detect_faces, load_recognizer, train_recognizer, recognize_image

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "dataset"
MODEL_DIR = ROOT / "model"
REMINDERS_FILE = ROOT / "reminders.json"

st.set_page_config(page_title="Amnesia Assistance", page_icon="🌿", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
:root{--ink:#263b36;--muted:#61736b;--paper:#f6f6f0;--surface:#fffefa;--line:#e5e8dd;--deep:#355f4f;--sage:#e7eee3;--peach:#fff3e8}
.stApp{background:var(--paper);color:var(--ink);font-family:'DM Sans',sans-serif}
[data-testid="stSidebar"]{background:#edf2e9;border-right:1px solid #e4e9df}
.block-container{max-width:1450px;padding-top:2rem;padding-bottom:3rem}
h1,h2,h3{font-family:'Manrope','DM Sans',sans-serif!important;color:var(--ink)!important;letter-spacing:-.035em}
h1{font-size:2.05rem!important}.hero{background:#e6eee2;border-radius:22px;padding:24px 27px;margin:10px 0 20px}.eyebrow{color:#526e5d;font-size:.78rem;font-weight:700;letter-spacing:.09em;text-transform:uppercase}.hero-title{font-family:Manrope,sans-serif;font-weight:800;font-size:1.6rem;letter-spacing:-.04em;color:var(--ink);margin:.25rem 0}.hero-copy{color:#52675c;font-size:1rem}.panel{background:#fffefa;border:1px solid #e9eadf;border-radius:18px;padding:18px 20px;margin-bottom:14px}.panel-title{font-family:Manrope,sans-serif;font-size:1.22rem;font-weight:750;color:var(--ink);margin-bottom:10px}.subtle{color:#63746e;font-size:.9rem}.stat{background:#fffefa;border:1px solid #e9eadf;border-radius:16px;padding:15px}.stButton>button{min-height:46px;border-radius:13px;border:1px solid #dfe6db;background:#fffefa;color:#355f4f;font-weight:700}.stButton>button[kind="primary"]{background:#355f4f;border-color:#355f4f;color:white}.stTextInput input,.stTextArea textarea{border-radius:12px;background:#fffefa}.status{padding:12px 14px;border-radius:13px;background:#edf3e9;color:#385e49;font-weight:600}
</style>
""", unsafe_allow_html=True)


def read_reminders():
    if REMINDERS_FILE.exists():
        try:
            values=json.loads(REMINDERS_FILE.read_text(encoding="utf-8"))
            if isinstance(values,list): return values
        except (OSError, json.JSONDecodeError):
            pass
    return [
        {"title":"Morning medicine","time":"9:00 AM","note":"Take with breakfast and a glass of water."},
        {"title":"Anna is visiting","time":"10:30 AM","note":"Your daughter will stay for tea."},
        {"title":"Lunch","time":"1:00 PM","note":"Soup is in the fridge."},
    ]


def save_reminders(items):
    REMINDERS_FILE.write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding="utf-8")


def safe_label(text):
    return re.sub(r"[^A-Za-z0-9_-]+","_",text.strip()).strip("_")[:48]


with st.sidebar:
    st.markdown("## 🌿 Amnesia Assistance")
    st.caption("A gentle daily support dashboard")
    page=st.radio("Go to",["Today","People & camera","Manage reminders","Hardware & voice","Caregiver notes"],label_visibility="visible")
    st.divider()

if page=="Today":
    st.title("Good morning, Margaret")
    st.caption(f"{date.today().strftime('%A, %B %d').replace(' 0', ' ')} · You’re at home")
    st.markdown('<div class="hero"><div class="eyebrow">A gentle start</div><div class="hero-title">You’re at home. You’re safe.</div><div class="hero-copy">Your reminders and familiar people are here. Let’s take today one step at a time.</div></div>',unsafe_allow_html=True)
    reminders=read_reminders()
    left,right=st.columns([1.5,1],gap="large")
    with left:
        st.markdown('<div class="panel-title">Today, at a glance</div>',unsafe_allow_html=True)
        for item in reminders:
            with st.container(border=True):
                cols=st.columns([.18,1])
                cols[0].markdown("### ⏰")
                cols[1].markdown(f"**{item['time']} · {item['title']}**  \n{item['note']}")
        st.info("A reminder supports daily care; it does not confirm that medicine was taken.")
    with right:
        st.markdown('<div class="panel"><div class="panel-title">People you know</div><div class="subtle">Use People & camera to capture a photo or open the live recognition window.</div></div>',unsafe_allow_html=True)
        if st.button("Open live camera recognition",type="primary",use_container_width=True):
            model=MODEL_DIR/"lbph_model.yml"
            if not model.exists(): st.warning("Train the model first in People & camera.")
            else:
                subprocess.Popen([sys.executable,str(ROOT/"recognize_faces.py")],cwd=str(ROOT))
                st.success("Live recognition opened in a separate window on this laptop.")
        st.markdown('<div class="panel"><div class="panel-title">Need help?</div><div class="subtle">Call a trusted caregiver using your phone or agreed emergency plan.</div></div>',unsafe_allow_html=True)

elif page=="People & camera":
    st.title("People & camera")
    st.markdown('<div class="hero"><div class="eyebrow">Familiar faces</div><div class="hero-title">Add a person or check a face</div><div class="hero-copy">Ask each person’s permission before taking or saving their photo. A match can be wrong; confirm it with the person or caregiver.</div></div>',unsafe_allow_html=True)
    col1,col2=st.columns(2,gap="large")
    with col1:
        st.markdown('<div class="panel-title">Add a consenting person</div>',unsafe_allow_html=True)
        name=st.text_input("Person’s name or family label",placeholder="For example: Anna")
        role=st.text_input("Relationship",placeholder="For example: Daughter")
        consent=st.checkbox("I have permission to capture and save this person’s face samples.")
        sample_camera=st.camera_input("Take a face sample",key="sample_camera",resolution="720p")
        sample_file=st.file_uploader("Or upload a photo if the camera preview is blank",type=["jpg","jpeg","png"],key="sample_file")
        sample=sample_camera if sample_camera is not None else sample_file
        if st.button("Save this sample",type="primary",disabled=not(sample and name.strip() and consent)):
            try:
                saved=collect_sample(sample.getvalue(),DATASET,safe_label(name))
                st.success(f"Saved {saved} face sample(s) for {name.strip()}.")
            except ValueError as exc: st.error(str(exc))
        if role.strip(): st.caption(f"Relationship note: {name.strip()} · {role.strip()} (shown as context; not used by the face model)")
    with col2:
        st.markdown('<div class="panel-title">Train and check</div>',unsafe_allow_html=True)
        st.caption("Training uses the saved face samples on this laptop. More than one varied sample per person is recommended.")
        if st.button("Train face model",use_container_width=True):
            try:
                count,people=train_recognizer(DATASET,MODEL_DIR)
                st.success(f"Trained on {count} samples for {people} label(s).")
            except ValueError as exc: st.error(str(exc))
        check_camera=st.camera_input("Take a photo to check",key="check_camera",resolution="720p")
        check_file=st.file_uploader("Or upload a photo to check",type=["jpg","jpeg","png"],key="check_file")
        check=check_camera if check_camera is not None else check_file
        threshold=st.slider("Matching strictness (prototype distance cutoff)",20,100,55,help="This is not a confidence percentage. Lower is stricter; uncertain results should remain Unknown.")
        if st.button("Check this photo",disabled=check is None,use_container_width=True):
            try:
                result,annotated=recognize_image(check.getvalue(),MODEL_DIR,threshold)
                st.image(cv2.cvtColor(annotated,cv2.COLOR_BGR2RGB),caption="Check any suggested name with a person or caregiver.")
                if result:
                    for name_found,distance in result: st.warning(f"Possible match: {name_found} · distance {distance:.1f}. Please confirm; this is not proof of identity.")
                else: st.info("No face was recognized. Treat this as Unknown.")
            except ValueError as exc: st.error(str(exc))

elif page=="Manage reminders":
    st.title("Manage reminders")
    st.caption("Keep each reminder short, familiar, and approved by the care team.")
    reminders=read_reminders()
    with st.form("add_reminder"):
        title=st.text_input("Reminder title")
        time_text=st.text_input("Time",placeholder="For example: 9:00 AM")
        note=st.text_area("Helpful note",placeholder="Short, calm wording")
        submitted=st.form_submit_button("Add reminder",type="primary")
    if submitted:
        if title.strip() and time_text.strip():
            reminders.append({"title":title.strip()[:80],"time":time_text.strip()[:40],"note":note.strip()[:240]})
            save_reminders(reminders); st.success("Reminder added."); st.rerun()
        else: st.error("Enter a title and a time.")
    for index,item in enumerate(reminders):
        with st.container(border=True):
            a,b=st.columns([4,1]); a.markdown(f"**{item['time']} · {item['title']}**  \n{item['note']}")
            if b.button("Delete",key=f"delete_{index}"):
                reminders.pop(index); save_reminders(reminders); st.rerun()

elif page=="Hardware & voice":
    st.title("Hardware & voice")
    st.markdown('<div class="hero"><div class="eyebrow">Hands-free support</div><div class="hero-title">Speak a simple command or send a reminder to the OLED.</div><div class="hero-copy">Run this dashboard on the laptop, keep the ESP32 connected by USB, and allow microphone access in Microsoft Edge or Chrome.</div></div>',unsafe_allow_html=True)
    st.subheader("Voice helper")
    st.caption("Try: “What happens next?”, “Who is Anna?”, or “When is my medicine reminder?” Browser voice recognition availability and language support vary.")
    transcript=voice_commands(key="voice_commands",default="")
    if transcript and transcript != st.session_state.get("last_voice_command",""):
        st.session_state.last_voice_command=transcript
        text=transcript.lower()
        reminders=read_reminders()
        if any(k in text for k in ["next","today","routine","happen"]):
            first=reminders[0] if reminders else None
            reply=(f"Next is {first['title']} at {first['time']}. {first['note']}" if first else "There are no reminders yet.")
        elif "who" in text or "anna" in text:
            reply="Anna is your daughter. Please confirm the person with your family."
        elif "medicine" in text or "medication" in text or "pill" in text:
            med=next((r for r in reminders if any(k in r['title'].lower() for k in ["medicine","medication","pill"])),None)
            reply=(f"Your reminder is {med['title']} at {med['time']}. {med['note']}" if med else "I can’t find a medicine reminder in today’s list.")
        else:
            reply="I heard you. You can ask what happens next, who is visiting, or when a reminder is scheduled."
        st.session_state.voice_reply=reply
    if st.session_state.get("voice_reply"):
        st.success(st.session_state.voice_reply)
        if st.button("Speak the answer",key="speak_reply"):
            import json
            components.html(f"<script>window.speechSynthesis.cancel();window.speechSynthesis.speak(new SpeechSynthesisUtterance({json.dumps(st.session_state.voice_reply)}));</script>",height=0)

    st.divider(); st.subheader("ESP32 and OLED over USB")
    st.caption("Connect the ESP32 to this laptop with its USB cable. Select the COM port, connect, then send the current reminder. This uses the serial message format in the matching Arduino sketch; no Wi-Fi is needed while USB is connected.")
    ports=available_ports()
    labels=[f"{device} — {description}" for device,description in ports]
    selected=st.selectbox("ESP32 port",labels,placeholder="Connect the ESP32 and refresh this page")
    if "esp32_serial" not in st.session_state: st.session_state.esp32_serial=None
    a,b=st.columns(2)
    with a:
        if st.button("Connect ESP32",type="primary",disabled=not bool(ports),use_container_width=True):
            try:
                conn=st.session_state.esp32_serial
                if conn and conn.is_open: conn.close()
                port=ports[labels.index(selected)][0]
                st.session_state.esp32_serial=connect_esp32(port)
                send_line(st.session_state.esp32_serial,"PERSON|Margaret|Patient")
                st.success(f"Connected to {port}; sent the patient label.")
            except Exception as exc: st.error(f"Could not open the port: {exc}")
    with b:
        if st.button("Disconnect",use_container_width=True):
            conn=st.session_state.get("esp32_serial")
            if conn and conn.is_open: conn.close()
            st.session_state.esp32_serial=None
            st.info("ESP32 disconnected.")
    current=read_reminders()
    if current:
        chosen=st.selectbox("Reminder to show on OLED",current,format_func=lambda item:f"{item['time']} · {item['title']}")
        if st.button("Send reminder to OLED",disabled=not bool(st.session_state.esp32_serial),use_container_width=True):
            try:
                import time
                dose_id=int(time.time())
                send_line(st.session_state.esp32_serial,f"MED|{dose_id}|{chosen['title']}|{chosen['time']}")
                st.success("Reminder sent to the ESP32.")
            except Exception as exc: st.error(f"Could not send reminder: {exc}")
    if st.button("Check ESP32 button response",disabled=not bool(st.session_state.esp32_serial)):
        responses=read_lines(st.session_state.esp32_serial)
        if responses: st.info(" · ".join(responses))
        else: st.caption("No button response received yet.")

else:
    st.title("Caregiver notes")
    st.markdown('<div class="hero"><div class="eyebrow">For family and care teams</div><div class="hero-title">A shared routine, with consent.</div><div class="hero-copy">Use clear reminders and agreed check-ins. Limit who can access personal details and face samples.</div></div>',unsafe_allow_html=True)

st.divider()







