from transformers import CLIPProcessor, CLIPModel
import torch
from PIL import Image

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

def embed_image(image: Image.Image):
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        vec = model.get_image_features(**inputs)
    return vec[0].tolist()   # 512-dim

def embed_text_clip(text: str):
    inputs = processor(text=[text], return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        vec = model.get_text_features(**inputs)
    return vec[0].tolist()   # 512-dim

def embed_text_clip(text: str):
    inputs = processor(text=[text], return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        vec = model.get_text_features(**inputs)
    return vec[0].tolist()   # 512-dim