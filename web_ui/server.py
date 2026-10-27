"""Lightweight Web Dashboard Server for QA Form Validation Studio."""
from __future__ import annotations

import json
import mimetypes
import os
import queue
import sys
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.config_loader import ApplicationConfig, BrowserConfig, ExecutionConfig, FrameworkConfig, LoginConfig
from core.browser.browser_manager import BrowserManager
from core.login.login_manager import LoginManager, LoginException
from core.navigation.navigator import Navigator, NavigationException
from form_engine.field_classifier import FieldClassifier
from form_engine.field_detector import FieldDetector
from form_engine.form_detector import FormDetector
from form_engine.form_executor import FormExecutor
from form_engine.models import TestResult, TestStatus
from reporting.logger import logger
from reporting.report_manager import ReportManager
from rules.rule_registry import RuleRegistry

# Global event queue for Server-Sent Events (SSE)
sse_clients: List[queue.Queue] = []
sse_lock = threading.Lock()
current_run_status = {"running": False, "progress": 0, "total": 0, "results": []}


def broadcast_event(event_data: Dict[str, Any]) -> None:
    """Dispatches a JSON event payload to all connected SSE clients."""
    with sse_lock:
        data_str = json.dumps(event_data)
        message = f"data: {data_str}\n\n"
        for q in list(sse_clients):
            try:
                q.put_nowait(message)
            except Exception:
                if q in sse_clients:
                    sse_clients.remove(q)


class QADashboardHandler(SimpleHTTPRequestHandler):
    """HTTP request handler providing REST API and serving static dashboard assets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_ROOT / "web_ui" / "static"), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/stream":
            self._handle_sse_stream()
        elif path == "/api/presets":
            self._handle_presets()
        elif path == "/api/status":
            self._handle_status()
        elif path == "/api/reports":
            self._handle_reports_list()
        elif path.startswith("/reports/"):
            self._serve_external_file(PROJECT_ROOT / path.lstrip("/"))
        elif path.startswith("/screenshots/"):
            self._serve_external_file(PROJECT_ROOT / path.lstrip("/"))
        else:
            # Default to static files (index.html, css, js)
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/run":
            self._handle_run_request()
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")

    def _handle_sse_stream(self):
        """Streams real-time test progress using Server-Sent Events."""
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        client_queue: queue.Queue = queue.Queue()
        with sse_lock:
            sse_clients.append(client_queue)

        try:
            # Send initial ping
            self.wfile.write(b": ping\n\n")
            self.wfile.flush()
            while True:
                try:
                    msg = client_queue.get(timeout=15.0)
                    self.wfile.write(msg.encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    # Keep-alive heartbeat
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            with sse_lock:
                if client_queue in sse_clients:
                    sse_clients.remove(client_queue)

    def _handle_presets(self):
        """Returns pre-configured sample project URLs for easy 1-click testing."""
        presets = [
            {
                "id": "hmis-portal",
                "name": "HMIS — Hospital Management Information System (PITB)",
                "target_url": "https://hmis-beta.pitb.gov.pk/login",
                "has_login": True,
                "base_url": "https://hmis-beta.pitb.gov.pk/login",
                "hospital": "PITB Testing Hospital 2",
                "project_name": "HMIS",
            },
            {
                "id": "auction-citizen",
                "name": "Citizen Auction Portal — Registration (PITB)",
                "target_url": "https://dev-auction-citizen.pitb.gov.pk/register",
                "has_login": False,
                "base_url": "https://dev-auction-citizen.pitb.gov.pk/register",
            },
            {
                "id": "knowledge-hub",
                "name": "Knowledge Hub — Sign Up (PITB)",
                "target_url": "https://webdev.pitb.gov.pk/knowledgehub/sign-up",
                "has_login": False,
                "base_url": "https://webdev.pitb.gov.pk/knowledgehub/sign-up",
            },
            {
                "id": "demo-local",
                "name": "Local Demo Form (Create User)",
                "target_url": "http://127.0.0.1:8080/create_user.html",
                "has_login": True,
                "base_url": "http://127.0.0.1:8080/login.html",
                "username": "admin",
                "password": "Admin@123456",
            },
            {
                "id": "demo-wizard",
                "name": "Multi-Step Wizard Registration (3 Steps)",
                "target_url": "http://127.0.0.1:8080/wizard_registration.html",
                "has_login": False,
                "base_url": "http://127.0.0.1:8080/wizard_registration.html",
            },
        ]
        self._send_json(presets)

    def _handle_status(self):
        self._send_json(current_run_status)

    def _handle_reports_list(self):
        reports_dir = PROJECT_ROOT / "reports"
        items = []
        if reports_dir.exists():
            for f in reports_dir.glob("*.html"):
                items.append({
                    "name": f.name,
                    "path": f"/reports/{f.name}",
                    "size_kb": round(f.stat().st_size / 1024, 1),
                    "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(f.stat().st_mtime)),
                })
        self._send_json(sorted(items, key=lambda x: x["modified"], reverse=True))

    def _handle_run_request(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            req_data = json.loads(body.decode("utf-8"))
        except Exception:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON payload")
            return

        if current_run_status["running"]:
            self._send_json({"error": "A validation run is already in progress. Please wait."}, status=409)
            return

        # Start execution in separate daemon thread
        threading.Thread(target=execute_validation_run, args=(req_data,), daemon=True).start()
        self._send_json({"status": "started", "message": "Validation test execution initiated"})

    def _serve_external_file(self, file_path: Path):
        """Serves files from reports or screenshots directories."""
        if not file_path.exists() or file_path.is_dir():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        mime_type, _ = mimetypes.guess_type(str(file_path))
        mime_type = mime_type or "application/octet-stream"
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, f"Error reading file: {e}")

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


def execute_validation_run(payload: Dict[str, Any]) -> None:
    """Orchestrates test execution invoked via the Web UI."""
    global current_run_status
    current_run_status = {"running": True, "progress": 0, "total": 0, "results": []}

    target_url = payload.get("target_url", "").strip()
    has_login = payload.get("has_login", False)
    base_url = payload.get("base_url", target_url).strip() or target_url
    username = payload.get("username", "").strip()
    password = payload.get("password", "").strip()
    hospital = payload.get("hospital", "").strip()
    project_name = payload.get("project_name", "").strip()
    headed = payload.get("headed", True)
    slow_mo = int(payload.get("slow_mo", 50))

    if not target_url:
        broadcast_event({"type": "error", "message": "Target Form URL cannot be empty."})
        current_run_status["running"] = False
        return

    if not project_name:
        if "hmis" in target_url.lower() or "hmis" in base_url.lower() or hospital:
            project_name = "HMIS"
        else:
            project_name = f"Web Validation: {urlparse(target_url).netloc}"

    broadcast_event({"type": "log", "message": f"Starting validation run for: {target_url} [{project_name}]"})

    login_wait = int(payload.get("login_wait_seconds", 10))

    # Assemble dynamic configuration
    config = FrameworkConfig(
        project_name=project_name,
        application=ApplicationConfig(base_url=base_url, target_url=target_url),
        login=LoginConfig(
            username=username,
            password=password,
            hospital=hospital,
            wait_seconds=login_wait,
        ),
        browser=BrowserConfig(browser="chromium", headless=not headed, slow_mo=slow_mo, timeout=30000),
        execution=ExecutionConfig(
            screenshot_on_failure=True,
            screenshot_on_observation=True,
            output_dir=str(PROJECT_ROOT / "reports"),
            screenshots_dir=str(PROJECT_ROOT / "screenshots"),
        ),
    )

    # If testing local demo, start demo server automatically
    demo_server = None
    if "127.0.0.1:8080" in target_url or "localhost:8080" in target_url:
        from demo.server import DemoServer
        demo_server = DemoServer(port=8080)
        demo_server.start()
        time.sleep(0.5)

    browser_mgr = BrowserManager(config, headless_override=not headed)

    try:
        page = browser_mgr.start()
        broadcast_event({"type": "log", "message": "Browser opened. Checking authentication..."})

        # Login flow if enabled
        if has_login:
            broadcast_event({"type": "log", "message": "Authentication flow started..."})
            login_mgr = LoginManager(config)
            page = login_mgr.authenticate(page)
            broadcast_event({"type": "log", "message": "Authentication completed."})

        # Navigation
        navigator = Navigator(config)
        page = navigator.navigate_to_target(page)
        broadcast_event({"type": "log", "message": f"Target form opened: {page.url}"})

        # Form & Field Detection
        classifier = FieldClassifier(overrides=config.field_overrides)
        detector = FieldDetector(classifier=classifier, config=config.raw_config)
        form_detector = FormDetector(field_detector=detector)

        forms = form_detector.detect_forms(page)
        forms_with_fields = [f for f in forms if len(f.fields) > 0]
        if not forms_with_fields:
            broadcast_event({"type": "error", "message": "No interactive form fields detected on target page."})
            return

        target_form = max(forms_with_fields, key=lambda f: len(f.fields))
        broadcast_event({
            "type": "form_detected",
            "selector": target_form.selector,
            "fields_count": len(target_form.fields),
            "fields": [{"name": f.name, "type": f.semantic_type.value, "label": f.label} for f in target_form.fields],
        })

        # Rule Generation
        rule_registry = RuleRegistry()
        test_cases = rule_registry.generate_all(target_form.fields, config.raw_config)
        current_run_status["total"] = len(test_cases)

        broadcast_event({"type": "test_suite_generated", "count": len(test_cases)})

        # Executor with SSE streaming
        executor = FormExecutor(
            config,
            event_listener=broadcast_event,
            form_detector=form_detector,
            rule_registry=rule_registry,
        )
        results = executor.execute_suite(page, target_form, test_cases)

        # Generate Reports
        ReportManager.save_json_summary(results, config.execution.output_dir)
        html_report_path = ReportManager.save_html_summary(results, config.execution.output_dir, config.project_name)

        broadcast_event({
            "type": "run_completed",
            "total": len(results),
            "passed": sum(1 for r in results if r.status == TestStatus.PASS),
            "failed": sum(1 for r in results if r.status == TestStatus.FAIL),
            "observation": sum(1 for r in results if r.status == TestStatus.OBSERVATION),
            "html_report": f"/reports/{Path(html_report_path).name}",
        })

    except Exception as e:
        logger.exception(f"Execution run error: {e}")
        broadcast_event({"type": "error", "message": str(e)})
    finally:
        browser_mgr.stop()
        if demo_server:
            demo_server.stop()
        current_run_status["running"] = False


def start_studio_server(port: int = 5000, open_browser: bool = True) -> None:
    """Launches the QA Dashboard server on specified port and opens default browser."""
    server_address = ("127.0.0.1", port)
    ThreadingHTTPServer.allow_reuse_address = True
    httpd = ThreadingHTTPServer(server_address, QADashboardHandler)
    url = f"http://127.0.0.1:{port}"
    print("=" * 70)
    print(f"  QA Form Validation Studio is running at: {url}")
    print(f"  Open {url} in your browser to begin testing.")
    print("  Press Ctrl+C to stop.")
    print("=" * 70)

    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping QA Form Validation Studio...")
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    start_studio_server(port=5000, open_browser=True)
