import cv2
from analyzer import detect_faces, detect_objects

def process_image(image_path):
    # Detect faces
    face_results = detect_faces(image_path)
    print("Faces detected with Haar Cascade:", len(face_results['haarcascade']))
    print("Faces detected with dlib HOG:", len(face_results['dlib']))

    # Detect objects
    object_detections = detect_objects(image_path)
    for i in range(object_detections.shape[2]):
        confidence = object_detections[0, 0, i, 2]
        if confidence > 0.5:  # Confidence threshold
            idx = int(object_detections[0, 0, i, 1])
            box = object_detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")
            print(f"Object detected with confidence {confidence}: ({startX}, {startY}) to ({endX}, {endY})")

if __name__ == "__main__":
    image_path = "path_to_your_image.jpg"
    process_image(image_path)