"""Train the local LBPH face model from dataset/ folders."""
from pathlib import Path
from face_tools import train_recognizer
ROOT=Path(__file__).resolve().parent
if __name__=="__main__":
    try:
        count,people=train_recognizer(ROOT/"dataset",ROOT/"model")
        print(f"Training complete: {count} images across {people} label(s).")
    except ValueError as exc: print(exc)
