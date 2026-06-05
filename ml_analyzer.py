import os
import io
from pathlib import Path
from PIL import Image

# A tailored vocabulary for historical/family slide archives
LABELS_CONFIG = {
    "family": "a photo of a family or group of relatives",
    "group photo": "a group photo of people",
    "portrait": "a portrait photo of a person",
    "landscape": "a landscape photo of nature, trees, or sky",
    "wedding": "a photo of a wedding, bride, or groom",
    "beach": "a photo of a beach, ocean, or seaside",
    "lake": "a photo of a lake, river, or water body",
    "mountain": "a photo of mountains or hills",
    "forest": "a photo of a forest, woods, or park",
    "birthday party": "a photo of a birthday party, cake, or candles",
    "camping": "a photo of camping, tents, or campsite",
    "hiking": "a photo of hiking or walking in nature",
    "city": "a photo of a city, buildings, or street scene",
    "indoor": "a photo taken indoors or inside a house",
    "outdoor": "a photo taken outdoors in the open air",
    "snow": "a photo of snow, ice, or winter scene",
    "vintage": "a vintage, retro, or old archival photo"
}

class MLAnalyzer:
    def __init__(self):
        self.enabled = False
        self.model = None
        self.processor = None
        self._attempt_init()

    def _attempt_init(self):
        try:
            import torch
            from transformers import SiglipProcessor, SiglipModel
            
            self.torch = torch
            self.SiglipProcessor = SiglipProcessor
            self.SiglipModel = SiglipModel
            self.enabled = True
            print("ML Analyzer: PyTorch + Transformers SigLIP loaded successfully.")
        except ImportError:
            print("ML Analyzer: PyTorch/Transformers not installed. Running with ML features disabled.")
            self.enabled = False

    def load_model(self):
        if not self.enabled or self.model is not None:
            return
        
        # Load weights and model lazily to avoid startup delays
        try:
            model_name = "google/siglip-base-patch16-224"
            print(f"ML Analyzer: Loading {model_name} (approx 400MB)...")
            self.model = self.SiglipModel.from_pretrained(model_name)
            self.processor = self.SiglipProcessor.from_pretrained(model_name)
            print("ML Analyzer: SigLIP model weights loaded successfully.")
        except Exception as e:
            print(f"ML Analyzer: Failed to load SigLIP model weights: {e}")
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
            
            # Prepare prompts and image inputs
            labels = list(LABELS_CONFIG.keys())
            prompts = list(LABELS_CONFIG.values())
            
            # SigLIP requires padding="max_length"
            inputs = self.processor(text=prompts, images=img, return_tensors="pt", padding="max_length")
            
            # Run inference
            with self.torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                # Softmax over all text labels for stable relative scoring
                probs = logits_per_image.softmax(dim=1).squeeze(0)
                
            results = []
            for idx, prob_tensor in enumerate(probs):
                prob = prob_tensor.item()
                # 4% minimum threshold for softmax filtering across labels
                if prob >= 0.04:
                    results.append({
                        'feature': labels[idx],
                        'confidence': round(prob * 100, 1)
                    })
                    
            # Sort descending by confidence
            results.sort(key=lambda x: x['confidence'], reverse=True)
            return results
        except Exception as e:
            print(f"ML Analyzer: SigLIP inference failed: {e}")
            return []

# Singleton instance
analyzer = MLAnalyzer()
