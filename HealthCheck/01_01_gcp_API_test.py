import os
from google import genai

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

resp = client.models.generate_content(
    model="models/gemini-2.5-flash",
    contents="Return strict JSON: {\"ok\": true}"
)

print(resp.text)