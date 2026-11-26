"""Collect face samples locally. Only use with informed permission."""
from pathlib import Path
import cv2
from face_tools import detect_faces

ROOT=Path(__file__).resolve().parent
DATASET=ROOT/"dataset"

def main():
    label=input("Participant name/label (consent required): ").strip()
    import re
    label=re.sub(r"[^A-Za-z0-9_-]+","_",label).strip("_")[:48]
    if not label: print("Enter a valid label."); return
    folder=DATASET/label; folder.mkdir(parents=True,exist_ok=True)
    camera=cv2.VideoCapture(0)
    if not camera.isOpened(): print("Could not open webcam."); return
    print("SPACE saves the largest detected face; Q quits.")
    count=0
    while True:
        ok,frame=camera.read()
        if not ok: break
        gray,faces=detect_faces(frame)
        for x,y,w,h in faces: cv2.rectangle(frame,(x,y),(x+w,y+h),(0,220,0),2)
        cv2.putText(frame,f"{label}: saved {count} | SPACE save | Q quit",(10,28),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,220,0),2)
        cv2.imshow("Amnesia Assistance - Consent-based collection",frame)
        key=cv2.waitKey(1)&0xFF
        if key==ord('q'): break
        if key==32 and len(faces):
            x,y,w,h=max(faces,key=lambda box:box[2]*box[3]); face=cv2.resize(gray[y:y+h,x:x+w],(200,200))
            cv2.imwrite(str(folder/f"face_{len(list(folder.glob('*.jpg'))):04d}.jpg"),face); count+=1
            print(f"Saved sample {count}.")
    camera.release(); cv2.destroyAllWindows(); print(f"Saved {count} samples for {label}.")
if __name__=="__main__": main()
