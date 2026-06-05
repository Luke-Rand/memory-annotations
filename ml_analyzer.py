import os
import io
from pathlib import Path
from PIL import Image

class MLAnalyzer:
    def __init__(self):
        self.enabled = False
        self.model = None
        self.preprocess = None
        self.categories = None
        self._attempt_init()

    def _attempt_init(self):
        try:
            import torch
            import torchvision.transforms as T
            from torchvision.models import mobilenet_v3_small, MobileNet_V3_Small_Weights
            
            self.torch = torch
            self.T = T
            self.weights = MobileNet_V3_Small_Weights.DEFAULT
            self.mobilenet_v3_small = mobilenet_v3_small
            self.enabled = True
            print("ML Analyzer: PyTorch + Torchvision MobileNetV3 loaded successfully.")
        except ImportError:
            print("ML Analyzer: PyTorch and Torchvision not installed. Running with ML features disabled.")
            self.enabled = False

    def load_model(self):
        if not self.enabled or self.model is not None:
            return
        
        # Load weights and model lazily
        try:
            self.model = self.mobilenet_v3_small(weights=self.weights)
            self.model.eval()
            self.preprocess = self.weights.transforms()
            self.categories = self.weights.meta["categories"]
            print("ML Analyzer: MobileNetV3 model weights loaded.")
        except Exception as e:
            print(f"ML Analyzer: Failed to load model weights: {e}")
            self.enabled = False

    def analyze(self, image_path_or_bytes):
        if not self.enabled:
            return []
        
        self.load_model()
        if not self.model:
            return []

        try:
            # Handle Path, file, PIL image, or bytes
            if isinstance(image_path_or_bytes, (str, Path)):
                img = Image.open(image_path_or_bytes).convert("RGB")
            elif isinstance(image_path_or_bytes, Image.Image):
                img = image_path_or_bytes.convert("RGB")
            else:
                img = Image.open(io.BytesIO(image_path_or_bytes)).convert("RGB")
            
            # Apply pre-processing transforms
            input_tensor = self.preprocess(img).unsqueeze(0)
            
            # Run inference
            with self.torch.no_grad():
                prediction = self.model(input_tensor).squeeze(0)
                probs = self.torch.nn.functional.softmax(prediction, dim=0)
                
            # Get top 5 predictions
            top5_prob, top5_catid = self.torch.topk(probs, 5)
            
            results = []
            for i in range(top5_prob.size(0)):
                prob = top5_prob[i].item()
                cat_name = self.categories[top5_catid[i].item()]
                # Clean up comma-separated ImageNet synonyms
                label = cat_name.split(",")[0].strip()
                # 10% confidence threshold for feature identification
                if prob >= 0.10:
                    results.append({
                        'feature': label,
                        'confidence': round(prob * 100, 1)
                    })
            return results
        except Exception as e:
            print(f"ML Analyzer: Inference failed: {e}")
            return []

# Singleton instance
analyzer = MLAnalyzer()
