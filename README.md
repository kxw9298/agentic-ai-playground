# agentic-ai-playground

## Quickstart
1) Save files as laid out above.
2) Create `.env` from `.env.example` and set your `OPENAI_API_KEY`.
3) Build & run:
```bash
docker compose up --build
```
4) In a new terminal, test health:
```bash
curl http://localhost:8080/health
curl http://localhost:8765/health
```
5) Try the agent:
```bash
curl -s -X POST http://localhost:8080/chat \
  -H 'Content-Type: application/json' \
  -d '{"conversation_id": "demo-1", "message": "List files via tool and read sample.txt"}' | jq
```
You should see the agent plan → call `list_files` and `read_file` → produce a grounded answer.