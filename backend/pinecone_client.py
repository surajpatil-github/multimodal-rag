import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

text_index = pc.Index(os.getenv("PINECONE_TEXT_INDEX"))
image_index = pc.Index(os.getenv("PINECONE_IMAGE_INDEX"))
