from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import os

app = FastAPI(title="CEFR Mock Test Platform")

# Mount static files only if directory exists
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# ========== Public Pages ==========

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Landing page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/info", response_class=HTMLResponse)
async def info(request: Request):
    """Info/About page"""
    return templates.TemplateResponse("info.html", {"request": request})

# ========== Authentication Pages ==========

@app.get("/auth", response_class=HTMLResponse)
async def auth(request: Request):
    """Authentication - Email entry"""
    return templates.TemplateResponse("auth.html", {"request": request})

@app.get("/auth/password", response_class=HTMLResponse)
async def auth_password(request: Request):
    """Authentication - Password entry for existing users"""
    return templates.TemplateResponse("auth-password.html", {"request": request})

@app.get("/auth/newuser", response_class=HTMLResponse)
async def auth_newuser(request: Request):
    """Authentication - New user registration"""
    return templates.TemplateResponse("auth-newuser.html", {"request": request})

@app.get("/auth/recovery", response_class=HTMLResponse)
async def auth_recovery(request: Request):
    """Authentication - Password recovery"""
    return templates.TemplateResponse("auth-recovery.html", {"request": request})

# ========== Payment ==========

@app.get("/payment", response_class=HTMLResponse)
async def payment(request: Request):
    """Payment page"""
    return templates.TemplateResponse("payment.html", {"request": request})

# ========== Dashboard ==========

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/dashboard/tests", response_class=HTMLResponse)
async def dashboard_tests(request: Request):
    """Tests page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/dashboard/results", response_class=HTMLResponse)
async def dashboard_results(request: Request):
    """Results page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/dashboard/profile", response_class=HTMLResponse)
async def dashboard_profile(request: Request):
    """Profile page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

# ========== Old Pages (for backward compatibility) ==========

@app.get("/pricing", response_class=HTMLResponse)
async def pricing(request: Request):
    """Old pricing page - redirect to payment"""
    return RedirectResponse(url="/payment")

@app.get("/features", response_class=HTMLResponse)
async def features(request: Request):
    """Old features page - redirect to info"""
    return RedirectResponse(url="/info")

@app.get("/faq", response_class=HTMLResponse)
async def faq(request: Request):
    """Old FAQ page - redirect to info"""
    return RedirectResponse(url="/info")

# ========== Utility Endpoints ==========

@app.get("/logout")
async def logout(request: Request):
    """Logout - redirect to home"""
    return RedirectResponse(url="/")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "CEFR Mock Test Platform"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
