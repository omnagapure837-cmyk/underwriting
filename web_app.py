from __future__ import annotations

import argparse
import html
import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs

from underwriting_engine import extract_profile, evaluate_underwriting, format_report, load_chart_data


def build_documents_from_form(form: dict[str, str]) -> tuple[str, str]:
    proposal = "\n".join(
        [
            f"Identity: {form.get('identity', '')}",
            f"Age: {form.get('age', '')}",
            f"Gender: {form.get('gender', '')}",
            f"Occupation: {form.get('occupation', '')}",
            f"Income: {form.get('income', '')}",
            f"Smoking: {form.get('smoking', 'No')}",
            f"Alcohol: {form.get('alcohol', 'none')}",
            f"Riders: {form.get('riders', '')}",
        ]
    )
    medical = f"Medical Conditions: {form.get('medical_conditions', '')}"
    return proposal, medical


def render_page(report: str = "", payload: str = "") -> str:
    report_html = f"<pre>{html.escape(report)}</pre>" if report else ""
    payload_html = (
        f"<details><summary>JSON Output</summary><pre>{html.escape(payload)}</pre></details>"
        if payload
        else ""
    )

    return f"""<!doctype html>
<html>
<head>
  <meta charset='utf-8'>
  <title>Life Underwriting Tool</title>
  <style>
    body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 24px auto; line-height: 1.4; }}
    .grid {{ display:grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    label {{ display:block; font-weight:bold; margin-bottom:4px; }}
    input, select {{ width:100%; padding:8px; }}
    textarea {{ width:100%; min-height:80px; padding:8px; }}
    button {{ margin-top: 12px; padding:10px 18px; }}
  </style>
</head>
<body>
  <h1>Automated Life Underwriting Tool</h1>
  <p>Fill the proposal and medical details, then click <strong>Evaluate</strong>.</p>
  <form method='post'>
    <div class='grid'>
      <div><label>Identity</label><input name='identity' value='Alex Morgan' required></div>
      <div><label>Age</label><input name='age' type='number' min='18' max='100' value='39' required></div>
      <div><label>Gender</label><input name='gender' value='Male' required></div>
      <div><label>Occupation</label><input name='occupation' value='driver' required></div>
      <div><label>Income</label><input name='income' type='number' value='85000' required></div>
      <div><label>Smoking</label>
        <select name='smoking'><option>No</option><option selected>Yes</option></select>
      </div>
      <div><label>Alcohol</label>
        <select name='alcohol'><option>none</option><option>social</option><option selected>regular</option><option>heavy</option></select>
      </div>
      <div><label>Riders (comma-separated)</label><input name='riders' value='Accident, Critical_Illness'></div>
    </div>
    <div style='margin-top:12px'>
      <label>Medical Conditions</label>
      <textarea name='medical_conditions'>Hypertension(Moderate), Diabetes(Controlled)</textarea>
    </div>
    <button type='submit'>Evaluate</button>
  </form>
  {report_html}
  {payload_html}
</body>
</html>"""


class UnderwritingHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        page = render_page()
        self._send_html(page)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        raw_form = parse_qs(body)
        form = {k: v[0] for k, v in raw_form.items()}

        proposal_text, medical_text = build_documents_from_form(form)
        charts = load_chart_data(Path("config/charts.json"))
        profile = extract_profile(proposal_text, medical_text)
        result = evaluate_underwriting(profile, charts)

        page = render_page(format_report(result), json.dumps(asdict(result), default=str, indent=2))
        self._send_html(page)

    def _send_html(self, payload: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(payload.encode("utf-8"))


def run(port: int = 8765) -> None:
    server = HTTPServer(("0.0.0.0", port), UnderwritingHandler)
    print(f"Open http://localhost:{port} in Chrome")
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run underwriting web UI")
    parser.add_argument("--port", type=int, default=8765, help="Port for the local web UI")
    args = parser.parse_args()
    run(args.port)
