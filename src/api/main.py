from fastapi import FastAPI, HTTPException
from typing import List
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from database.db_manager import DBManager

app = FastAPI(title="WaterAlert API", version="1.0.0")
db = DBManager()

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API WaterAlert", "status": "online"}

@app.get("/leaks")
def get_leaks():
    leaks = db.get_all_leaks()
    # Format the data for JSON
    results = []
    for l in leaks:
        results.append({
            "id": l[0],
            "citizen": l[2],
            "address": l[6],
            "severity": l[7],
            "technician": l[8],
            "status": l[9],
            "timestamp": l[10]
        })
    return results

@app.get("/leaks/{leak_id}")
def get_leak(leak_id: int):
    leak = db.get_leak_by_id(leak_id)
    if not leak:
        raise HTTPException(status_code=404, detail="Leak not found")
    return {
        "id": leak[0],
        "user_id": leak[1],
        "citizen": leak[2],
        "address": leak[6],
        "severity": leak[7],
        "status": leak[8],
        "timestamp": leak[9]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
