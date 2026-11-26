"""Compatibility entrypoint: run this project as a Streamlit web app."""
from streamlit.web.cli import main
import sys
from pathlib import Path
if __name__=="__main__":
    sys.argv=["streamlit","run",str(Path(__file__).with_name("app.py")),*sys.argv[1:]]
    raise SystemExit(main())
