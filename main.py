import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uuid
import html
import requests
from typing import Optional
import logging

app = FastAPI()

# Konfiguracija logovanja
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dozvoli sve domene (CORS)
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Globalna promenljiva za čuvanje podataka o firmama
firm_data = {}

# Postavi svoj Hugging Face API token ovde
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

# Model koji se koristi
MODEL_NAME = "moonshotai/Kimi-K2-Instruct:novita"

class FirmInput(BaseModel):
    firmText: str
    baseUrl: Optional[str] = None

class Query(BaseModel):
    question: str
    firmText: str

@app.post("/generate-embed")
async def generate_embed(data: FirmInput):
    embed_id = str(uuid.uuid4())[:8]
    firm_data[embed_id] = data.firmText

    escaped_js = html.escape(data.firmText).replace('\n', '\\n').replace('"', '\\"')
    
    base_url = data.baseUrl if data.baseUrl else ""

    embed_code = f'''
<style>
  /* Plutajuća chat ikonica */
  #chat-toggle-btn-{embed_id} {{
    position: fixed;
    bottom: 30px;
    right: 30px;
    background-color: #007bff;
    color: white;
    border-radius: 50%;
    width: 60px;
    height: 60px;
    border: none;
    cursor: pointer;
    font-size: 28px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background-color 0.3s ease;
    z-index: 9999;
  }}
  #chat-toggle-btn-{embed_id}:hover {{
    background-color: #0056b3;
  }}

  /* Chat container - skriven po defaultu */
  #chat-container-{embed_id} {{
    font-family: Arial, sans-serif;
    max-width: 400px;
    width: 100%;
    position: fixed;
    bottom: 100px;
    right: 30px;
    border: 1px solid #ccc;
    border-radius: 12px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.15);
    background-color: white;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    max-height: 0;
    opacity: 0;
    transform: translateY(20px);
    transition: max-height 0.4s ease, opacity 0.4s ease, transform 0.4s ease;
    z-index: 9998;
  }}

  /* Kad je chat otvoren */
  #chat-container-{embed_id}.open {{
    max-height: 450px;
    opacity: 1;
    transform: translateY(0);
  }}

  /* Chat history */
  #chat-history-{embed_id} {{
    flex-grow: 1;
    padding: 15px;
    overflow-y: auto;
    background-color: #f7f9fc;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }}

  /* Poruke korisnika */
  .msg-user-{embed_id} {{
    align-self: flex-end;
    background-color: #007bff;
    color: white;
    border-radius: 18px 18px 0 18px;
    padding: 10px 15px;
    max-width: 80%;
    word-wrap: break-word;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1);
  }}

  /* Poruke AI */
  .msg-ai-{embed_id} {{
    align-self: flex-start;
    background-color: #e9ecef;
    color: #333;
    border-radius: 18px 18px 18px 0;
    padding: 10px 15px;
    max-width: 80%;
    word-wrap: break-word;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1);
  }}

  /* Input wrapper */
  #chat-input-wrapper-{embed_id} {{
    display: flex;
    padding: 12px;
    border-top: 1px solid #eee;
    background-color: white;
  }}

  /* Input polje */
  #user-input-{embed_id} {{
    flex-grow: 1;
    padding: 12px 15px;
    border: 1px solid #ddd;
    border-radius: 20px;
    font-size: 15px;
    outline: none;
    transition: border-color 0.2s ease;
  }}
  #user-input-{embed_id}:focus {{
    border-color: #007bff;
  }}

  /* Dugme Pošalji */
  #send-btn-{embed_id} {{
    padding: 12px 25px;
    background-color: #007bff;
    color: white;
    border: none;
    border-radius: 20px;
    cursor: pointer;
    margin-left: 12px;
    font-weight: 600;
    transition: background-color 0.3s ease;
  }}
  #send-btn-{embed_id}:hover {{
    background-color: #0056b3;
  }}
</style>

<!-- Ikonica za otvaranje/zakljucavanje chat-a -->
<button id="chat-toggle-btn-{embed_id}" aria-label="Otvori chat">💬</button>

<!-- Chat kontejner -->
<div id="chat-container-{embed_id}">
  <div id="chat-history-{embed_id}">
    <!-- Poruke će se prikazivati ovde -->
  </div>
  <div id="chat-input-wrapper-{embed_id}">
    <input
      type="text"
      id="user-input-{embed_id}"
      placeholder="Unesite pitanje..."
      autocomplete="off"
    />
    <button id="send-btn-{embed_id}">Pošalji</button>
  </div>
</div>

<script>
  document.addEventListener('DOMContentLoaded', function() {{
    const toggleBtn = document.getElementById('chat-toggle-btn-{embed_id}');
    const container = document.getElementById('chat-container-{embed_id}');
    const chatHistory = document.getElementById('chat-history-{embed_id}');
    const userInput = document.getElementById('user-input-{embed_id}');
    const sendBtn = document.getElementById('send-btn-{embed_id}');
    const firmText = "{escaped_js}";
    const baseUrl = "{base_url}";

    // Toggle otvaranje/zatvaranje chata
    toggleBtn.addEventListener('click', () => {{
      container.classList.toggle('open');
      if(container.classList.contains('open')) {{
        userInput.focus();
      }}
    }});

    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(e) {{
      if (e.key === 'Enter') {{
        sendMessage(e);
      }}
    }});

    async function sendMessage(event) {{
      event.preventDefault();
      const question = userInput.value.trim();
      if (!question) return;

      userInput.value = '';
      chatHistory.innerHTML += `<div class="msg-user-{embed_id}">${{question}}</div>`;
      chatHistory.scrollTop = chatHistory.scrollHeight;

      try {{
        const response = await fetch(`${{baseUrl}}/ask`, {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ question: question, firmText: firmText }})
        }});

        if (!response.ok) {{
          let errorText = "Greška u odgovoru.";
          try {{
            const errorData = await response.json();
            errorText = errorData.detail || errorText;
          }} catch(e) {{}}
          throw new Error(errorText);
        }}

        const data = await response.json();
        chatHistory.innerHTML += `<div class="msg-ai-{embed_id}">${{data.answer}}</div>`;
        chatHistory.scrollTop = chatHistory.scrollHeight;
      }} catch (error) {{
        console.error('Greška:', error);
        chatHistory.innerHTML += `<div class="msg-ai-{embed_id}">Greška: ${{error.message}}</div>`;
        chatHistory.scrollTop = chatHistory.scrollHeight;
      }}
    }}
  }});
</script>
'''

    backend_code = f'''
# Backend kod za referencu - koristi isti main.py kao i ovaj
# Token: {HF_API_TOKEN}
# Model: {MODEL_NAME}
# Endpoint: /ask
'''

    return JSONResponse({"embed_code": embed_code, "backend_code": backend_code, "id": embed_id})

@app.post("/ask")
def ask(query: Query):
    messages = [
        {
            "role": "system",
            "content": "Ti si asistent koji odgovara samo na osnovu opisa firme koji mu je prosleđen."
        },
        {
            "role": "user",
            "content": f"Opis firme:\\n{query.firmText}\\n\\nPitanje:\\n{query.question}\\nOdgovori jasno i kratko."
        }
    ]

    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False
    }

    try:
        logger.info("Šaljem zahtev Hugging Face chat completions API-ju...")
        response = requests.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Greška pri pozivu Hugging Face API: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Status code: {e.response.status_code}")
            logger.error(f"Response: {e.response.text}")
        raise HTTPException(status_code=500, detail=f"Greška pri pozivu AI modela: {str(e)}")

    try:
        data = response.json()
    except Exception as e:
        logger.error(f"Greška pri parsiranju odgovora: {str(e)}")
        logger.error(f"Response text: {response.text}")
        raise HTTPException(status_code=500, detail="Neočekivan odgovor od AI modela.")

    try:
        answer = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        logger.error(f"Nevalidan format odgovora: {str(e)}")
        raise HTTPException(status_code=500, detail="Neočekivan format odgovora od AI modela.")

    return {"answer": answer}

@app.get("/")
async def root():
    return {"message": "Backend radi"}

@app.get("/test-hf-api")
async def test_hf_api():
    """Endpoint za testiranje Hugging Face API-ja"""
    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    test_payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": "What is the capital of France?"}
        ],
        "stream": False
    }
    try:
        response = requests.post(
            "https://router.huggingface.co/v1/chat/completions",
            headers=headers,
            json=test_payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}
