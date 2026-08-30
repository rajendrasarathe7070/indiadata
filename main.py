import os
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv


load_dotenv()

app = FastAPI(title="Indian Data SaaS API")

# CORS Setup: Taqi RapidAPI se data fetch karte waqt error na aaye
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase Connection
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Render Free Tier ko active rakhne ke liye pinger endpoint
@app.get("/ping")
def ping():
    return {"status": "success", "message": "FastAPI Server is active!"}

# 1. PINCODE LOOKUP ENDPOINT
@app.get("/api/v1/pincode/{code}")
def get_pincode_data(code: int):
    try:
        # Supabase se pincode table query karna
        response = supabase.table("pincodes").select("*").eq("pincode", code).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Pincode not found"
            )
            
        return {
            "success": True, 
            "count": len(response.data), 
            "data": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2. IFSC LOOKUP ENDPOINT
@app.get("/api/v1/ifsc/{code}")
def get_ifsc_data(code: str):
    try:
        ifsc_code = code.upper().strip()
        # Supabase se ifsc table query karna
        response = supabase.table("ifsc_codes").select("*").eq("IFSC", ifsc_code).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Invalid or Unknown IFSC code"
            )
            
        # Hamein sirf ek record chahiye isliye data[0] return kar rahe hain
        return {"success": True, "data": response.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
