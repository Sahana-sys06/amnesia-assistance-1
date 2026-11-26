"""Open local live recognition in a separate webcam window. Not a proof of identity."""
from pathlib import Path
import argparse
import cv2
from face_tools import detect_faces, load_recognizer
ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--threshold",type=float,default=55.0); args=parser.parse_args()
    try: recognizer,names=load_recognizer(ROOT/"model")
    except ValueError as exc: print(exc); return
    camera=cv2.VideoCapture(0)
    if not camera.isOpened(): print("Could not open webcam. Close other camera applications and try again."); return
    print("Live recognition running locally. Press Q to quit. Confirm any suggested name with the person or caregiver.")
    while True:
        ok,frame=camera.read()
        if not ok: break
        gray,faces=detect_faces(frame)
        for x,y,w,h in faces:
            face=cv2.resize(gray[y:y+h,x:x+w],(200,200)); label,distance=recognizer.predict(face)
            name=names.get(str(label),"Unknown") if distance<=args.threshold else "Unknown"
            text=f"Possible: {name} - confirm" if name!="Unknown" else "Unknown"
            color=(0,165,0) if name!="Unknown" else (0,0,220)
            cv2.rectangle(frame,(x,y),(x+w,y+h),color,2); cv2.putText(frame,text,(x,max(25,y-10)),cv2.FONT_HERSHEY_SIMPLEX,.6,color,2)
        cv2.putText(frame,"Q quit | Matches may be wrong; confirm identity",(10,25),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),2)
        cv2.imshow("Amnesia Assistance - Local live recognition",frame)
        if cv2.waitKey(1)&0xFF==ord('q'): break
    camera.release(); cv2.destroyAllWindows()
if __name__=="__main__": main()
