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

@app.get("/")
def ping():
    return {"status": "success", "message": "Advanced FastAPI Server is active!" ,"by-": "Rajendra Sarathe" }

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

# 2. STANDARD IFSC LOOKUP (Sahi Column 'IFSC' matching ke sath)
@app.get("/api/v1/ifsc/{code}")
def get_ifsc_data(code: str):
    try:
        ifsc_code = code.upper().strip()
        
        # NOTE: Aapke CSV data ke mutabik column ka naam capital "IFSC" hai, isliye yahan capital kiya
        response = supabase.table("ifsc_code").select("*").eq("IFSC", ifsc_code).execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(status_code=404, detail="Invalid or Unknown IFSC code")
            
        return {"success": True, "data": response.data[0]} # Clean Single Object Response
    except HTTPException as he: 
        raise he
    except Exception as e: 
        # Database fetch error ki jagah ab real database error screen par aayega
        raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")

# 3. ADVANCED: STATE SE DISTRICTS (Case-Insensitive Setup)
# 3. FIXED: STATE SE DISTRICTS (Smart Case-Insensitive Filter)
@app.get("/api/v1/districts")
def get_districts_by_state(state: str = Query(..., description="State name e.g. Telangana")):
    try:
        # Wildcard '%' jodne se user 'telangana' likhe ya 'Telangana', match ho jayega
        state_query = f"%{state.strip()}%"
        
        response = supabase.table("pincode").select("district").ilike("statename", state_query).execute()
        
        if not response.data or len(response.data) == 0:
            return {"success": True, "count": 0, "districts": []}
            
        unique_districts = list(set([row['district'] for row in response.data if row.get('district')]))
        return {"success": True, "count": len(unique_districts), "districts": sorted(unique_districts)}
    except Exception as e: 
        # detail=str(e) lagane se agar koi galti hogi to screen par saaf dikhegi
        raise HTTPException(status_code=500, detail=str(e))
# 4. ADVANCED: UNIQUE BANKS LIST
@app.get("/api/v1/banks/unique")
def get_unique_banks():
    try:
        response = supabase.table("IFSC").select("BANK").execute()
        if not response.data or len(response.data) == 0:
            return {"success": True, "banks": []}
        unique_banks = list(set([row['BANK'] for row in response.data if row.get('BANK')]))
        return {"success": True, "count": len(unique_banks), "banks": sorted(unique_banks)}
    except Exception as e: raise HTTPException(status_code=500, detail="Error fetching unique banks")

# 5. ADVANCED: BRANCH FINDER (Case-Insensitive Smart Search)

# 5. FIXED: BRANCH FINDER (Sahi Table 'ifsc_codes' aur Columns ke sath)
@app.get("/api/v1/search-branch")
def search_bank_branch(
    bank: str = Query(..., description="e.g. Bank of Baroda"), 
    city: str = Query(..., description="e.g. Harsud")
):
    try:
        bank_query = f"%{bank.strip()}%"
        city_query = f"%{city.strip()}%"
        # Yahan table ka naam strictly 'ifsc_code' kar diya gaya hai
        response = supabase.table("ifsc_code").select("BRANCH,IFSC,ADDRESS").ilike("BANK", bank_query).ilike("CITY", city_query).execute()
        return {"success": True, "count": len(response.data), "branches": response.data}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
