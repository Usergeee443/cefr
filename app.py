from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

app = FastAPI(title="CEFR Mock Test Platform")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Landing page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/pricing", response_class=HTMLResponse)
async def pricing(request: Request):
    """Pricing page"""
    return templates.TemplateResponse("pricing.html", {"request": request})

@app.get("/features", response_class=HTMLResponse)
async def features(request: Request):
    """Features page"""
    return templates.TemplateResponse("features.html", {"request": request})

@app.get("/faq", response_class=HTMLResponse)
async def faq(request: Request):
    """FAQ page"""
    return templates.TemplateResponse("faq.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "CEFR Mock Test Platform"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
