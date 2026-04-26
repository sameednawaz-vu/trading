import os
from openai import OpenAI

client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",
  api_key = "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"
)

completion = client.chat.completions.create(
  model="meta/llama-3.1-70b-instruct",
  messages=[{"role":"user","content":"Hello"}],
  temperature=0.2,
  top_p=0.7,
  max_tokens=1024,
)

print(completion.choices[0].message.content)
