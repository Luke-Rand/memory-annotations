"""
Analyzer module for object and face detection using OpenCV and dlib.
"""

import cv2
import dlib
from utils import is_image_file

# Load pre-trained models
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
hog_face_detector = dlib.get_frontal_face_detector()

def detect_faces(image_path):
    """Detect faces in an image using OpenCV and dlib."""
    if not is_image_file(image_path):
        raise ValueError(f"Unsupported file extension: {image_path}")

    # Read the image
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Detect faces using OpenCV Haar Cascade
    faces_haarcascade = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

    # Detect faces using dlib HOG-based method
    faces_dlib = hog_face_detector(gray, 1)

    return {
        'haarcascade': faces_haarcascade,
        'dlib': [(face.left(), face.top(), face.right(), face.bottom()) for face in faces_dlib]
    }

def detect_objects(image_path):
    """Detect objects in an image using OpenCV."""
    if not is_image_file(image_path):
        raise ValueError(f"Unsupported file extension: {image_path}")

    # Load pre-trained object detection model
    net = cv2.dnn.readNetFromCaffe("deploy.prototxt", "res10_300x300_ssd_iter_140000.caffemodel")

    # Read the image
    image = cv2.imread(image_path)
    (h, w) = image.shape[:2]

    # Preprocess the image for object detection
    blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0))

    # Pass the blob through the network and obtain the detections
    net.setInput(blob)
    detections = net.forward()

    return detections

# Example usage
if __name__ == "__main__":
    image_path = "path_to_your_image.jpg"
    
    print("Detecting faces...")
    face_results = detect_faces(image_path)
    print("Faces detected with Haar Cascade:", len(face_results['haarcascade']))
    print("Faces detected with dlib HOG:", len(face_results['dlib']))

    print("\\nDetecting objects...")
    object_detections = detect_objects(image_path)
    for i in range(object_detections.shape[2]):
        confidence = object_detections[0, 0, i, 2]
        if confidence > 0.5:  # Confidence threshold
            idx = int(object_detections[0, 0, i, 1])
            box = object_detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")
            print(f"Object detected with confidence {confidence}: ({startX}, {startY}) to ({endX}, {endY})")