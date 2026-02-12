# Dans le shell Django

import google.generativeai as genai
from django.conf import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

# Testez différents modèles
models_to_try = ['gemini-1.5-flash', 'gemini-1.0-pro']
for model_name in models_to_try:
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Bonjour")
        print(f"✅ {model_name}: {response.text}")
    except Exception as e:
        print(f"❌ {model_name}: {e}")