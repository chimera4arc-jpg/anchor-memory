import json, os, sys
from http.server import HTTPServer, BaseHTTPRequestHandler
sys.path.insert(0, os.path.dirname(__file__))
from anchor_mcp import create_server

db_path = os.environ.get("DB_PATH", "/data/anchor_memory")
tools, handle_tool, mem = create_server(db_path=db_path)

class MCPHandler(BaseHTTPRequestHandler):
    def _send(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            return self._send({"status": "ok", "memory_count": mem.count()})
        if self.path == "/tools":
            return self._send({"tools": tools})
        self._send({"error": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        action = body.get("action")
        if action == "tools/list":
            return self._send({"tools": tools})
        elif action == "tools/call":
            result = handle_tool(body["name"], body.get("arguments", {}))
            return self._send(result)
        elif action == "health":
            return self._send({"status": "ok", "memory_count": mem.count()})
        else:
            self._send({"error": f"unknown action: {action}"}, 400)

port = int(os.environ.get("PORT", 8000))
print(f"Anchor Memory MCP Server running on port {port}")
HTTPServer(("0.0.0.0", port), MCPHandler).serve_forever()
