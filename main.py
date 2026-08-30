import os
from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="India Financial & Geo Databank API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

@app.get("/ping")
def ping():
    return {"status": "success", "message": "Advanced FastAPI Server is active!"}

# 1. STANDRAD PINCODE LOOKUP (Flexible Data Input)
@app.get("/api/v1/pincode/{code}")
def get_pincode_data(code: str):
    try:
        search_val = int(code.strip()) if code.strip().isdigit() else code.strip()
        response = supabase.table("pincode").select("*").eq("pincode", search_val).execute()
        
        # Empty list check standard tarika
        if not response.data or len(response.data) == 0:
            raise HTTPException(status_code=404, detail="Pincode not found")
            
        return {"success": True, "count": len(response.data), "data": response.data}
    except HTTPException as he: raise he
    except Exception as e: raise HTTPException(status_code=500, detail="Database fetch error")

# 2. STANDARD IFSC LOOKUP (Crash-Proof Single Object Format)
@app.get("/api/v1/ifsc/{code}")
def get_ifsc_data(code: str):
    try:
        ifsc_code = code.upper().strip()
        response = supabase.table("ifsc_codes").select("*").eq("ifsc", ifsc_code).execute()
        
        # Yahan array empty hone par crash nahi hoga, gracefully 404 dega
        if not response.data or len(response.data) == 0:
            raise HTTPException(status_code=404, detail="Invalid or Unknown IFSC code")
            
        return {"success": True, "data": response.data[0]} 
    except HTTPException as he: raise he
    except Exception as e: raise HTTPException(status_code=500, detail="Database fetch error")

# 3. ADVANCED: STATE SE DISTRICTS (Case-Insensitive Setup)
@app.get("/api/v1/districts")
def get_districts_by_state(state: str = Query(..., description="State name e.g. Telangana")):
    try:
        state_name = state.strip()
        # .ilike se User 'telangana' likhe ya 'Telangana', matching ho jayegi
        response = supabase.table("pincode").select("district").ilike("statename", state_name).execute()
        
        if not response.data or len(response.data) == 0:
            return {"success": True, "count": 0, "districts": []}
            
        unique_districts = list(set([row['district'] for row in response.data if row.get('district')]))
        return {"success": True, "count": len(unique_districts), "districts": sorted(unique_districts)}
    except Exception as e: raise HTTPException(status_code=500, detail="Error filtering districts")

# 4. ADVANCED: UNIQUE BANKS LIST
@app.get("/api/v1/banks/unique")
def get_unique_banks():
    try:
        response = supabase.table("ifsc_codes").select("BANK").execute()
        if not response.data or len(response.data) == 0:
            return {"success": True, "banks": []}
        unique_banks = list(set([row['BANK'] for row in response.data if row.get('BANK')]))
        return {"success": True, "count": len(unique_banks), "banks": sorted(unique_banks)}
    except Exception as e: raise HTTPException(status_code=500, detail="Error fetching unique banks")

# 5. ADVANCED: BRANCH FINDER (Case-Insensitive Smart Search)
@app.get("/api/v1/search-branch")
def search_bank_branch(
    bank: str = Query(..., description="e.g. Bank of Baroda"), 
    city: str = Query(..., description="e.g. Harsud")
):
    try:
        bank_name = bank.strip()
        city_name = city.strip()
        # ilike lagane se users lowercase me bhi search karenge to sahi data milega
        response = supabase.table("ifsc_codes").select("BRANCH,ifsc,ADDRESS").ilike("BANK", bank_name).ilike("CITY", city_name).execute()
        return {"success": True, "count": len(response.data), "branches": response.data}
    except Exception as e: raise HTTPException(status_code=500, detail="Error searching branches")
