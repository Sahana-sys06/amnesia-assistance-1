# Amnesia Assistance — integrated local dashboard

This project combines the Streamlit daily dashboard with the supplied face collection, training, and live-recognition scripts.

## Run on Windows

1. Install Python 3.10 or newer and Arduino IDE is not needed for this dashboard.
2. Open PowerShell in this folder.
3. Run:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe -m streamlit run app.py
   ```

4. Open the local URL Streamlit prints. Allow camera access in the browser when prompted.

## What is integrated

- `app.py` is the main Streamlit dashboard with reminder management and face collection/checking screens.
- The in-page camera captures one photo at a time using the browser camera.
- The Hardware & voice page supports browser speech commands and sends reminders to the ESP32 over USB serial.
- `collect_faces.py` is an optional local live camera collector (SPACE saves a sample, Q quits).
- `train_model.py` trains an OpenCV LBPH model from the local `dataset/` folders.
- The dashboard's live recognition uses the browser webcam and checks a frame once per second; `recognize_faces.py` remains an optional local OpenCV tool.
- `face_tools.py` contains shared local capture/training/recognition helpers.
- `web_dashboard.py` is a compatibility launcher for the Streamlit app. The previous custom dashboard depended on missing `database/` and `reminders/` modules, so it has been replaced by this unified entry point.
- `reminders.json` is created locally after reminder changes.

## Safety and privacy

Face images and model weights are sensitive. This app stores them locally in `dataset/` and `model/`; those folders are excluded by `.gitignore`. Do not upload participant images or model files to a public repository or Streamlit Cloud. Ask for informed permission before collecting anyone's face. Recognition can be wrong, and the displayed name is only a possible match; it must be confirmed by a person. This is an educational prototype, not a medical device or an emergency service.

Still-photo checks and live browser recognition send captured images to the Streamlit server for matching. Live recognition checks one frame per second while running. Face samples, metadata, and trained model files are runtime data; the Streamlit-hosted filesystem can reset when the app restarts. The browser can connect to local USB serial only when the user grants the browser permission. The app does not place calls, send caregiver alerts, or provide medical advice.


