import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import date

app = FastAPI(title="Kinesiology Site API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Kinesiology API en ligne"}

# Public content endpoints
class FAQItem(BaseModel):
    question: str
    answer: str

_FAQ_DATA: List[FAQItem] = [
    FAQItem(question="Qu'est-ce que la kinésiologie ?", answer="La kinésiologie est une approche holistique qui utilise le test musculaire pour identifier les déséquilibres et favoriser l'équilibre du corps et de l'esprit."),
    FAQItem(question="Pour qui ?", answer="Pour adultes, enfants et sportifs. Elle accompagne le stress, les émotions, la préparation mentale et l'amélioration du bien-être."),
    FAQItem(question="Comment se déroule une séance ?", answer="Après un échange, des tests musculaires doux permettent d'identifier les corrections adaptées (respiration, mouvements, techniques énergétiques)."),
]

@app.get("/api/faq", response_model=List[FAQItem])
def get_faq():
    return _FAQ_DATA

# Reservation endpoints (persist in MongoDB)
@app.post("/api/appointments")
def create_appointment(appt: 'Appointment'):
    try:
        from schemas import Appointment  # type: ignore
        from database import db, create_document  # type: ignore
    except Exception:
        raise HTTPException(status_code=500, detail="Base de données indisponible")

    if db is None:
        raise HTTPException(status_code=500, detail="Base de données indisponible")

    # Ensure chosen date is not in the past
    if appt.date < date.today():
        raise HTTPException(status_code=400, detail="La date ne peut pas être dans le passé")

    inserted_id = create_document("appointment", appt)
    return {"status": "ok", "id": inserted_id}

@app.get("/api/appointments")
def list_appointments():
    try:
        from database import db, get_documents  # type: ignore
    except Exception:
        raise HTTPException(status_code=500, detail="Base de données indisponible")

    if db is None:
        raise HTTPException(status_code=500, detail="Base de données indisponible")

    docs = get_documents("appointment", {}, 100)
    # Convert ObjectIds to strings and dates to iso strings
    converted = []
    for d in docs:
        d = dict(d)
        if d.get("_id") is not None:
            try:
                d["_id"] = str(d["_id"])
            except Exception:
                pass
        if isinstance(d.get("date"), date):
            d["date"] = d["date"].isoformat()
        converted.append(d)
    return converted

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        from database import db  # type: ignore
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
                response["connection_status"] = "Connected"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
