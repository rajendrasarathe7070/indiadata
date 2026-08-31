import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from typing import Optional, Dict, Any
import requests
from bs4 import BeautifulSoup
from google import genai
from supabase import create_client, Client
from dotenv import load_dotenv
import json

load_dotenv()

app = FastAPI(title="Pay-As-You-Go AI Scraper API")

# क्लाइंट्स इनिशियलाइजेशन
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

# 🔑 सुरक्षा, क्रेडिट वेरिफिकेशन और यूसेज ट्रैकिंग Middleware
async def verify_credits_and_track(endpoint: str, target_url: str, api_key: str):
    # 1. यूजर और उसका क्रेडिट डेटा चेक करें
    user_query = supabase.table("users").select("id, total_credits, used_credits").eq("api_key", api_key).execute()
    
    if not user_query.data:
        raise HTTPException(status_code=403, detail="अवैध API Key।")
    
    user = user_query.data[0]
    total_credits = user["total_credits"]
    used_credits = user["used_credits"]
    
    # 2. चेक करें कि क्या क्रेडिट बचा है
    if used_credits >= total_credits:
        raise HTTPException(
            status_code=429, 
            detail="आपका API क्रेडिट खत्म हो गया है! कृपया लिमिट बढ़ाने के लिए रिचार्ज करें।"
        )
    
    # 3. यदि क्रेडिट है, तो used_credits को +1 बढ़ाएं
    supabase.table("users").update({"used_credits": used_credits + 1}).eq("id", user["id"]).execute()
    
    # 4. इतिहास के लिए लॉग्स टेबल में एंट्री करें
    supabase.table("api_logs").insert({
        "api_key": api_key,
        "endpoint": endpoint,
        "target_url": target_url
    }).execute()

# इनपुट डेटा का ढांचा
class ScrapeRequest(BaseModel):
    url: str
    mode: str = "json"  # ऑप्शन्स: json, markdown, summary
    json_structure: Optional[Dict[str, Any]] = None

@app.post("/api/v1/convert")
async def convert_content(request: ScrapeRequest, api_key: str = Depends(api_key_header)):
    # क्रेडिट चेक और डिडक्शन को ट्रिगर करें
    await verify_credits_and_track(endpoint=request.mode, target_url=request.url, api_key=api_key)
    
    try:
        # 1. वेबसाइट डेटा फेच करें
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(request.url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 2. HTML साफ़ करें
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style", "iframe", "nav", "footer"]):
            script.decompose()
        
        clean_text = " ".join(soup.get_text().split())[:10000]

        # 3. मोड के हिसाब से जेमिनी प्रॉम्प्ट सेट करें
        if request.mode == "json":
            if not request.json_structure:
                raise HTTPException(status_code=400, detail="JSON मोड के लिए 'json_structure' ज़रूरी है।")
            prompt = f"इस टेक्स्ट से डेटा निकालो और ठीक इस JSON स्ट्रक्चर में वापस करो: {request.json_structure}. सिर्फ वैलिड JSON दें, कोई बैकस्टिक्स (```json) या एक्सप्लेनेशन न लिखें।\n\nटेक्स्ट:\n{clean_text}"
            
        elif request.mode == "markdown":
            prompt = f"इस वेबसाइट के टेक्स्ट को साफ़ Markdown (.md) फॉर्मेट में बदलो। फालतू लिंक्स हटा दें।\n\nटेक्स्ट:\n{clean_text}"
            
        elif request.mode == "summary":
            prompt = f"इस वेबसाइट के कंटेंट को 5 मुख्य बुलेट पॉइंट्स में समराइज करो।\n\nटेक्स्ट:\n{clean_text}"
            
        else:
            raise HTTPException(status_code=400, detail="गलत मोड!")

        # 4. जेमिनी 2.5 फ्लैश मॉडल कॉल करें
        ai_response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        result_text = ai_response.text.strip()

        # 5. रिस्पॉन्स भेजें
        if request.mode == "json":
            try:
                return {"success": True, "mode": request.mode, "data": json.loads(result_text)}
            except:
                return {"success": True, "mode": request.mode, "raw_data": result_text, "note": "JSON parsing failed."}
                
        return {"success": True, "mode": request.mode, "data": result_text}

    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"वेबसाइट फेच एरर: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"सर्ver एरर: {str(e)}")
