import os
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

class DialClient:
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=os.getenv("DAIL_API_KEY"),
            api_version=os.getenv("API_VERSION"),
            azure_endpoint=os.getenv("AZURE_ENDPOINT"),
        )
        self.chat_model = os.getenv("DEFAULT_MODEL", "gpt-4o")  # fallback
        self.embed_model = os.getenv("EMBEDDING_MODEL", "text-embedding-005")

    # Generic chat
    def chat(self, messages, temperature=0.0):
        try:
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[Chat Error] {str(e)}"

    # Generic embedding
    def embed(self, text):
        try:
            response = self.client.embeddings.create(
                model=self.embed_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            return f"[Embedding Error] {str(e)}"

    # 🔹 NEW: Document validation helper for Claims Agent
    def validate_claim_document(self, claim_type: str, doc_text: str) -> str:
        """
        Validate claim documents using GPT-4o.
        Returns either:
        - 'YES | ExtractedInfo' (if valid)
        - 'NO' (if invalid)
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are an insurance claims validator. "
                               "Your job is to validate claim documents for health or vehicle insurance."
                },
                {
                    "role": "user",
                    "content": f"""
Document text:
{doc_text}

Task: For a {claim_type} insurance claim:
- If valid: reply "YES | ExtractedInfo"
- If invalid: reply "NO"

Validation rules:
- Health claim requires hospital info.
- Vehicle claim requires police station info.
"""
                }
            ]
            response = self.client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                temperature=0.0,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[Validation Error] {str(e)}"
