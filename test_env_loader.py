import os
from dotenv import load_dotenv

load_dotenv()
print("NVIDIA_API_KEY from dotenv:", os.environ.get("NVIDIA_API_KEY"))
