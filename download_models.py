import os
import requests

# Define URLs for the model files
urls = {
    "deploy.prototxt": "https://raw.githubusercontent.com/opencv/opencv/master/data/deep_learning_model/deploy.prototxt",
    "res10_300x300_ssd_iter_140000.caffemodel": "https://raw.githubusercontent.com/opencv/opencv_3rdparty/dnn_samples_face_detector/res10_300x300_ssd_iter_140000.caffemodel"
}

# Define the directory to save the model files
model_dir = "models"

# Create the directory if it doesn't exist
os.makedirs(model_dir, exist_ok=True)

# Download and save each file
for filename, url in urls.items():
    response = requests.get(url)
    if response.status_code == 200:
        with open(os.path.join(model_dir, filename), "wb") as f:
            f.write(response.content)
        print(f"Successfully downloaded {filename}")
    else:
        print(f"Failed to download {filename}")

print("Download complete. Model files are now available in the 'models' directory.")