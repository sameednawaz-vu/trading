
import requests
import json

def test_nvidia_api():
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    api_key = "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"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "meta/llama-3.3-70b-instruct",
        "messages": [{"role": "user", "content": "Test message. Reply with 'OK'."}],
        "temperature": 0.2,
        "top_p": 0.7,
        "max_tokens": 1024,
        "stream": False
    }
    
    try:
        print("Sending request to Nvidia API...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_nvidia_api()
