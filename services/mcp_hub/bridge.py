import os
from typing import List
from fastapi import FastAPI, HTTPException
import uvicorn

MCP_ROOT = os.getenv("MCP_ROOT", "/data")

app = FastAPI(title="MCP Bridge", version="0.1")

@app.get("/health")
def health():
    return {"status": "ok", "root": MCP_ROOT}

@app.get("/list")
def list_files():
    result: List[str] = []
    for root, _, files in os.walk(MCP_ROOT):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, MCP_ROOT)
            result.append(rel)
    return {"files": sorted(result)}

@app.post("/read")
def read_file(path: str):
    target = os.path.join(MCP_ROOT, path)
    if not os.path.abspath(target).startswith(os.path.abspath(MCP_ROOT)):
        raise HTTPException(400, "Path traversal not allowed")
    if not os.path.exists(target):
        raise HTTPException(404, "Not found")
    with open(target, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    return {"path": path, "content": content}