"""Entrypoint cho Railway/Cloud deployment - đọc PORT từ biến môi trường."""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"Starting server on port {port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
