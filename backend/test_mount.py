from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

app = FastAPI()

def hello():
    return 'Admin Hello'

# Simulate SQLAdmin which mounts another FastAPI app
admin_app = FastAPI()
admin_app.get("/")(hello)

app.mount("/admin", admin_app)

@app.get("/{full_path:path}")
def catch_all(full_path: str):
    if full_path.startswith("admin"):
        raise HTTPException(status_code=404, detail="Intercepted by catch-all!")
    return f"catch_all: {full_path}"

client = TestClient(app)
res_no_slash = client.get("/admin", follow_redirects=False)
print("GET /admin:", res_no_slash.status_code, res_no_slash.text)
res_slash = client.get("/admin/", follow_redirects=False)
print("GET /admin/:", res_slash.status_code, res_slash.text)
