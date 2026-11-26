from __future__ import annotations
import json
from pathlib import Path
import cv2
import numpy as np

CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

def decode_image(image_bytes: bytes):
    image=cv2.imdecode(np.frombuffer(image_bytes,dtype=np.uint8),cv2.IMREAD_COLOR)
    if image is None: raise ValueError("Could not read that image. Take another photo and try again.")
    return image

def detect_faces(image):
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    faces=CASCADE.detectMultiScale(gray,scaleFactor=1.2,minNeighbors=5,minSize=(80,80))
    return gray,faces

def collect_sample(image_bytes: bytes,dataset: Path,name: str):
    if not name: raise ValueError("Enter a short person label first.")
    image=decode_image(image_bytes)
    gray,faces=detect_faces(image)
    if len(faces)==0: raise ValueError("No face found. Improve lighting and face the camera, then try again.")
    x,y,w,h=max(faces,key=lambda box:box[2]*box[3])
    face=cv2.resize(gray[y:y+h,x:x+w],(200,200))
    folder=dataset/name; folder.mkdir(parents=True,exist_ok=True)
    existing=len(list(folder.glob("*.jpg")))
    path=folder/f"face_{existing:04d}.jpg"
    if not cv2.imwrite(str(path),face): raise ValueError("Could not save the sample.")
    return path.name

def train_recognizer(dataset: Path,model_dir: Path):
    if not hasattr(cv2,"face"):
        raise ValueError("OpenCV face tools are missing. Install opencv-contrib-python and remove opencv-python.")
    if not dataset.exists(): raise ValueError("No saved face samples yet. Add consenting participants first.")
    people=sorted(p for p in dataset.iterdir() if p.is_dir())
    images=[]; labels=[]; names={}
    for label_id,person in enumerate(people):
        names[str(label_id)]=person.name
        for path in sorted(person.glob("*.jpg")):
            image=cv2.imread(str(path),cv2.IMREAD_GRAYSCALE)
            if image is not None: images.append(cv2.resize(image,(200,200))); labels.append(label_id)
    if len(images)<2 or not labels: raise ValueError("Save at least two clear face samples before training.")
    model_dir.mkdir(parents=True,exist_ok=True)
    recognizer=cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(images,np.asarray(labels,dtype=np.int32))
    recognizer.write(str(model_dir/"lbph_model.yml"))
    (model_dir/"labels.json").write_text(json.dumps(names,indent=2),encoding="utf-8")
    return len(images),len(names)

def load_recognizer(model_dir: Path):
    model_path=model_dir/"lbph_model.yml"; labels_path=model_dir/"labels.json"
    if not hasattr(cv2,"face"): raise ValueError("Install opencv-contrib-python to use face recognition.")
    if not model_path.exists() or not labels_path.exists(): raise ValueError("Train the model first.")
    rec=cv2.face.LBPHFaceRecognizer_create(); rec.read(str(model_path))
    labels=json.loads(labels_path.read_text(encoding="utf-8"))
    return rec,labels

def recognize_image(image_bytes: bytes,model_dir: Path,threshold: float=55.0):
    recognizer,names=load_recognizer(model_dir)
    image=decode_image(image_bytes); gray,faces=detect_faces(image); results=[]
    for x,y,w,h in faces:
        sample=cv2.resize(gray[y:y+h,x:x+w],(200,200))
        label,distance=recognizer.predict(sample)
        match=names.get(str(label),"Unknown") if distance<=threshold else "Unknown"
        if match!="Unknown": results.append((match,float(distance)))
        color=(40,145,70) if match!="Unknown" else (50,50,200)
        text=f"{match} - confirm" if match!="Unknown" else "Unknown"
        cv2.rectangle(image,(x,y),(x+w,y+h),color,2)
        cv2.putText(image,text,(x,max(24,y-8)),cv2.FONT_HERSHEY_SIMPLEX,.65,color,2)
    return results,image
