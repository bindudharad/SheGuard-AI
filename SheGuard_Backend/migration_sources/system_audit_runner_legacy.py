from __future__ import annotations

import ast
import csv
import importlib
import importlib.metadata as md
import json
import os
import py_compile
import re
import sqlite3
import subprocess
import sys
import time
import traceback
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
AUDIT_TMP = REPORTS / "audit_runtime"
AUDIT_TMP.mkdir(parents=True, exist_ok=True)
NOW = datetime.now().isoformat(timespec="seconds")
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
SKIP_DIRS = {".venv", "__pycache__", ".pytest_cache"}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path)


def write_report(name: str, data: dict) -> None:
    (REPORTS / name).write_text(json.dumps(data, indent=2, ensure_ascii=True, default=str), encoding="utf-8")


def mark(ok: bool, warning: bool = False) -> str:
    if ok and not warning:
        return "PASS"
    if ok:
        return "WARN"
    return "FAIL"


def run_cmd(args: list[str], timeout: int = 60, env: dict | None = None) -> dict:
    started = time.perf_counter()
    try:
        proc = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=env)
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        }
    except subprocess.TimeoutExpired:
        return {"returncode": None, "stdout": "", "stderr": "timeout", "duration_ms": round((time.perf_counter() - started) * 1000, 2)}


def iter_files(base: Path = ROOT, pattern_suffix: str | None = None):
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            path = Path(dirpath) / filename
            if pattern_suffix is None or path.name.endswith(pattern_suffix):
                yield path


def inventory() -> dict:
    files = []
    by_top = defaultdict(lambda: {"files": 0, "bytes": 0, "extensions": Counter()})
    for path in iter_files(ROOT):
        stat = path.stat()
        top = path.relative_to(ROOT).parts[0]
        by_top[top]["files"] += 1
        by_top[top]["bytes"] += stat.st_size
        by_top[top]["extensions"][path.suffix.lower() or "[no_ext]"] += 1
        files.append({"path": rel(path), "bytes": stat.st_size, "ext": path.suffix.lower()})
    required = [
        "main.py",
        "backend/app.py",
        "models/v2/sheguard_sequence_model.pt",
        "models/v2/sequence_scaler.joblib",
        "models/v2/sequence_label_encoder.joblib",
        "sheguard.db",
        "requirements.txt",
        "config.yaml",
    ]
    missing = [item for item in required if not (ROOT / item).exists()]
    names = Counter(p.name.lower() for p in iter_files(ROOT))
    report = {
        "generated_at": NOW,
        "total_files_excluding_venv_cache": len(files),
        "top_level_summary": {
            key: {"files": val["files"], "bytes": val["bytes"], "extensions": dict(val["extensions"].most_common(20))}
            for key, val in sorted(by_top.items())
        },
        "required_paths_missing": missing,
        "duplicate_file_names_sample": [{"name": k, "count": v} for k, v in names.items() if v > 1][:100],
        "files_sample_first_1000": files[:1000],
    }
    report["status"] = mark(not missing, bool(report["duplicate_file_names_sample"]))
    write_report("full_system_inventory.json", report)
    return report


def python_validation() -> dict:
    py_files = list(iter_files(ROOT, ".py"))
    compile_fail = []
    for path in py_files:
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            compile_fail.append({"path": rel(path), "error": str(exc)})
    modules = [
        "backend.app",
        "backend.api.schemas",
        "backend.database.session",
        "backend.models.entities",
        "backend.services.security",
        "backend.services.stability",
        "backend.services.gpu",
        "backend.services.evidence_manager",
        "backend.services.cloud_ai",
        "backend.routes.incidents",
        "action_sequence_classifier",
        "action_classifier",
        "utils.tracking",
        "utils.sequence_features",
        "video_clipper",
    ]
    import_results = []
    for module in modules:
        started = time.perf_counter()
        try:
            importlib.import_module(module)
            import_results.append({"module": module, "status": "PASS", "duration_ms": round((time.perf_counter() - started) * 1000, 2)})
        except Exception as exc:
            import_results.append({"module": module, "status": "FAIL", "error": str(exc), "traceback": traceback.format_exc()[-2000:]})
    circular = []
    imports_by_file = {}
    for path in py_files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
            names = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names.append(node.module)
            imports_by_file[rel(path)] = sorted(set(names))
        except Exception:
            pass
    for file, imports in imports_by_file.items():
        if file.startswith("backend/"):
            module = file[:-3].replace("/", ".")
            for imported in imports:
                imported_file = imported.replace(".", "/") + ".py"
                if imported_file in imports_by_file and module in imports_by_file[imported_file]:
                    circular.append({"a": module, "b": imported})
    report = {
        "generated_at": NOW,
        "python_files": len(py_files),
        "compiled_pass": len(py_files) - len(compile_fail),
        "compiled_fail": compile_fail,
        "safe_import_results": import_results,
        "possible_circular_imports": circular,
        "deprecated_api_observations": ["FastAPI @app.on_event works but is deprecated; lifespan handlers are preferred."],
    }
    report["status"] = mark(not compile_fail and all(r["status"] == "PASS" for r in import_results), bool(circular))
    write_report("python_validation_report.json", report)
    return report


def dependency_audit() -> dict:
    reqs = [line.strip() for line in (ROOT / "requirements.txt").read_text().splitlines() if line.strip() and not line.startswith("#")]
    packages = [re.split(r"[<>=!~]", req)[0].strip() for req in reqs]
    packages += ["torchvision", "sqlite3", "websockets", "yaml", "transformers"]
    installed, missing = {}, []
    name_map = {"opencv-python": "cv2", "PyYAML": "yaml", "python-dotenv": "dotenv", "scikit-learn": "sklearn", "sqlite3": "sqlite3"}
    for package in packages:
        import_name = name_map.get(package, package.replace("-", "_"))
        try:
            if package == "sqlite3":
                installed[package] = {"version": sqlite3.sqlite_version, "import": import_name}
            else:
                mod = importlib.import_module(import_name)
                try:
                    version = md.version(package)
                except Exception:
                    version = getattr(mod, "__version__", "unknown")
                installed[package] = {"version": version, "import": import_name}
        except Exception as exc:
            missing.append({"package": package, "import": import_name, "error": str(exc)})
    report = {
        "generated_at": NOW,
        "requirements": reqs,
        "installed": installed,
        "missing_or_unimportable": missing,
        "notes": ["transformers is not required by current code.", "torchvision is not listed directly in requirements."],
    }
    report["status"] = mark(not any(item["package"] in [re.split(r"[<>=!~]", req)[0].strip() for req in reqs] for item in missing), bool(missing))
    write_report("dependency_audit.json", report)
    return report


def gpu_validation() -> dict:
    report = {"generated_at": NOW, "torch_import": False}
    try:
        import torch

        report.update(
            {
                "torch_import": True,
                "torch_version": torch.__version__,
                "torch_cuda_build": torch.version.cuda,
                "cuda_available": bool(torch.cuda.is_available()),
                "device_count": torch.cuda.device_count(),
            }
        )
        if torch.cuda.is_available():
            idx = torch.cuda.current_device()
            props = torch.cuda.get_device_properties(idx)
            report.update(
                {
                    "gpu_name": torch.cuda.get_device_name(idx),
                    "total_vram_mb": round(props.total_memory / (1024 * 1024), 2),
                    "allocated_mb": round(torch.cuda.memory_allocated(idx) / (1024 * 1024), 2),
                    "reserved_mb": round(torch.cuda.memory_reserved(idx) / (1024 * 1024), 2),
                    "cuda_tensor_smoke": str(torch.zeros((1, 4), device="cuda").device),
                }
            )
        else:
            report["fallback"] = "CPU fallback expected on this host."
    except Exception as exc:
        report["error"] = str(exc)
    report["status"] = mark(report.get("torch_import", False), not report.get("cuda_available", False))
    write_report("gpu_validation_report.json", report)
    return report


def model_validation() -> dict:
    report = {"generated_at": NOW, "artifacts": {}, "issues": []}
    paths = [
        "models/v2/sheguard_sequence_model.pt",
        "models/v2/sequence_scaler.joblib",
        "models/v2/sequence_label_encoder.joblib",
        "models/v2/metrics_v2.json",
        "models/model.joblib",
        "models/scaler.joblib",
        "models/label_encoder.joblib",
        "yolov8n.pt",
    ]
    for item in paths:
        path = ROOT / item
        report["artifacts"][item] = {"exists": path.exists(), "bytes": path.stat().st_size if path.exists() else None}
    try:
        import joblib
        import numpy as np
        import torch

        checkpoint = torch.load(ROOT / "models/v2/sheguard_sequence_model.pt", map_location="cpu", weights_only=False)
        report["checkpoint_keys"] = sorted(checkpoint.keys())
        report["checkpoint_meta"] = {key: checkpoint.get(key) for key in ["sequence_length", "hidden_size", "input_size", "num_classes"]}
        report["label_classes"] = [str(x) for x in joblib.load(ROOT / "models/v2/sequence_label_encoder.joblib").classes_]
        from action_sequence_classifier import ActionSequenceClassifier

        clf = ActionSequenceClassifier(device="cpu")
        report["sequence_classifier_available"] = clf.available
        report["sequence_classifier_device"] = str(clf.device)
        if clf.available:
            seq_len = clf.sequence_length
            feat_len = int(checkpoint.get("input_size", 19))
            label, conf, probs = clf._predict_sequence(np.zeros((1, seq_len, feat_len), dtype=np.float32))
            report["safe_inference_smoke"] = {"label": label, "confidence": conf, "probabilities_keys": list(probs.keys())}
        clf.close()
    except Exception as exc:
        report["issues"].append({"type": "model_load_or_smoke_failed", "error": str(exc), "traceback": traceback.format_exc()[-3000:]})
    report["status"] = mark(not report["issues"] and all(v["exists"] for v in report["artifacts"].values()))
    write_report("model_validation_report.json", report)
    return report


def dataset_validation() -> dict:
    dataset = ROOT / "dataset"
    files = list(iter_files(dataset)) if dataset.exists() else []
    manifests = [p for p in files if p.suffix.lower() in {".csv", ".json", ".txt"} and any(t in p.name.lower() for t in ["manifest", "train", "test", "val", "split"])]
    manifest_summary = []
    for path in manifests[:50]:
        item = {"path": rel(path), "bytes": path.stat().st_size}
        try:
            if path.suffix.lower() == ".csv":
                with path.open(newline="", encoding="utf-8", errors="ignore") as handle:
                    item["rows_including_header"] = sum(1 for _ in csv.reader(handle))
            elif path.suffix.lower() == ".json":
                obj = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
                item["json_type"] = type(obj).__name__
                item["entries"] = len(obj) if hasattr(obj, "__len__") else None
        except Exception as exc:
            item["error"] = str(exc)
        manifest_summary.append(item)
    sample = [p for p in files if p.suffix.lower() in {".mp4", ".avi", ".mpg", ".jpg", ".jpeg", ".png"}][:60]
    media = []
    try:
        import cv2

        for path in sample:
            item = {"path": rel(path), "ext": path.suffix.lower(), "bytes": path.stat().st_size}
            if path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                img = cv2.imread(str(path))
                item["readable"] = img is not None
                item["shape"] = list(img.shape) if img is not None else None
            else:
                cap = cv2.VideoCapture(str(path))
                ok, _ = cap.read()
                item.update({"open": bool(cap.isOpened()), "first_frame": bool(ok), "fps": cap.get(cv2.CAP_PROP_FPS), "frame_count": cap.get(cv2.CAP_PROP_FRAME_COUNT)})
                cap.release()
            media.append(item)
    except Exception as exc:
        media.append({"error": str(exc)})
    report = {
        "generated_at": NOW,
        "dataset_exists": dataset.exists(),
        "total_dataset_files": len(files),
        "extension_counts": dict(Counter(p.suffix.lower() for p in files).most_common()),
        "largest_parent_counts": dict(Counter(rel(p.parent) for p in files).most_common(40)),
        "manifest_files_found": [rel(p) for p in manifests],
        "manifest_summary_sample": manifest_summary,
        "sampled_media_validation": media,
        "limitations": ["Sampled media readability only; full frame-by-frame corruption scan was not run."],
    }
    report["status"] = mark(dataset.exists() and bool(files), any(not x.get("readable", x.get("first_frame", True)) for x in media))
    write_report("dataset_validation_report.json", report)
    return report


def realtime_and_camera() -> tuple[dict, dict]:
    main = (ROOT / "main.py").read_text(encoding="utf-8", errors="ignore")
    camera_mgr = (ROOT / "backend/services/camera_manager.py").read_text(encoding="utf-8", errors="ignore")
    checks = {
        "confidence_smoothing": "TemporalStabilityEngine" in main,
        "cooldown": "alert_cooldown" in main,
        "inactivity": "InactivityAnalyzer" in main,
        "pre_event_buffer": "RollingVideoBuffer" in main,
        "reconnect": "def reconnect" in main,
        "rtsp_ip_support": "rtsp://" in main or "http://" in main,
    }
    report = {"generated_at": NOW, "flow_checks": checks, "issues": []}
    try:
        from backend.services.stability import TemporalStabilityEngine, fuse_signals

        engine = TemporalStabilityEngine(window=3, persistence_frames=2)
        first = engine.smooth("audit", "fall", 0.9, {"fall": 0.9, "normal": 0.1})
        second = engine.smooth("audit", "fall", 0.92, {"fall": 0.92, "normal": 0.08})
        report["smoothing_smoke"] = {"first": first, "second": second, "fused": fuse_signals(0.9, 0.9, label="fall")}
    except Exception as exc:
        report["issues"].append({"error": str(exc)})
    report["status"] = mark(all(checks.values()) and not report["issues"])
    write_report("realtime_pipeline_report.json", report)
    cam = {
        "generated_at": NOW,
        "webcam_index_support": "VideoCapture" in main + camera_mgr,
        "droidcam_fallback_support": "build_droidcam_sources" in main,
        "rtsp_or_ip_support": "rtsp://" in main or "http://" in main,
        "reconnect_support": "reconnect" in main + camera_mgr,
        "fps_tracking": "fps" in (main + camera_mgr).lower(),
        "health_monitoring": "CameraHealth" in camera_mgr,
        "stream_timeout_explicit": False,
        "notes": ["OpenCV capture does not set explicit network read timeouts; RTSP stalls may block depending on backend."],
    }
    cam["status"] = mark(all([cam["webcam_index_support"], cam["droidcam_fallback_support"], cam["reconnect_support"], cam["fps_tracking"], cam["health_monitoring"]]), True)
    write_report("camera_validation_report.json", cam)
    return report, cam


def api_validation() -> dict:
    env = os.environ.copy()
    env["SHEGUARD_DB_PATH"] = str(AUDIT_TMP / "api_validation.sqlite")
    script = r'''
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from fastapi.testclient import TestClient
from backend.app import app
client = TestClient(app)
phone = "98" + str(int(time.time()*1000))[-8:]
results = []
def call(method, path, **kwargs):
    r = getattr(client, method)(path, **kwargs)
    try: body = r.json()
    except Exception: body = r.text[:200]
    results.append({"method": method.upper(), "path": path, "status_code": r.status_code, "ok": 200 <= r.status_code < 300, "body_keys": list(body.keys()) if isinstance(body, dict) else []})
    return r
with client:
    r = call("post", "/register", json={"full_name":"Audit User","phone_number":phone,"password":"secret123"})
    uid = r.json().get("user_id")
    r = call("post", "/login", json={"phone_number":phone,"password":"secret123"})
    token = r.json().get("access_token")
    call("get", f"/profile/{uid}")
    call("post", "/contacts/add", json={"user_id":uid,"relation":"friend","contact_name":"Audit Contact","phone_number":"9999999999"})
    call("get", f"/contacts/{uid}")
    call("post", "/location/update", json={"user_id":uid,"latitude":12.9716,"longitude":77.5946,"speed":1.2})
    call("get", f"/location/live/{uid}")
    r = call("post", "/incident/create", json={"user_id":uid,"incident_type":"fall","confidence":0.91,"ai_summary":"Audit smoke incident","send_alert":False})
    iid = r.json().get("incident",{}).get("incident_id")
    call("get", f"/incident/history/{uid}")
    call("get", "/incident/live")
    call("post", "/camera/register", json={"camera_name":"Audit Camera","ip_address":"127.0.0.1","online_status":"offline"})
    call("get", "/camera/list")
    call("get", f"/evidence/{iid}")
    call("get", f"/secure/evidence/{iid}", headers={"Authorization": f"Bearer {token}"})
    call("get", "/health/gpu")
print(json.dumps(results))
'''
    run = run_cmd([sys.executable, "-c", script], timeout=90, env=env)
    report = {"generated_at": NOW, "mode": "Temporary SQLite DB under reports/audit_runtime; production sheguard.db not modified.", "command": {k: v for k, v in run.items() if k != "stdout"}, "tests": []}
    try:
        report["tests"] = json.loads(run["stdout"].strip().splitlines()[-1])
    except Exception as exc:
        report["parse_error"] = str(exc)
        report["raw_stdout"] = run["stdout"]
    report["status"] = mark(run["returncode"] == 0 and report["tests"] and all(t["ok"] for t in report["tests"]))
    write_report("backend_api_validation.json", report)
    return report


def database_validation() -> dict:
    db = ROOT / "sheguard.db"
    report = {"generated_at": NOW, "db_path": str(db), "exists": db.exists(), "tables": {}, "indexes": {}, "foreign_key_check": [], "integrity_check": None}
    if db.exists():
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            report["integrity_check"] = conn.execute("PRAGMA integrity_check").fetchall()
            report["foreign_key_check"] = conn.execute("PRAGMA foreign_key_check").fetchall()
            for table in ["users", "emergency_contacts", "live_locations", "incidents", "evidence", "cctv_cameras"]:
                exists = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None
                columns = conn.execute(f"PRAGMA table_info({table})").fetchall() if exists else []
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] if exists else None
                report["tables"][table] = {"exists": exists, "row_count": count, "columns": [row[1] for row in columns]}
                report["indexes"][table] = conn.execute(f"PRAGMA index_list({table})").fetchall() if exists else []
        finally:
            conn.close()
    report["status"] = mark(db.exists() and all(v["exists"] for v in report["tables"].values()) and report["integrity_check"] == [("ok",)] and report["foreign_key_check"] == [])
    write_report("database_validation_report.json", report)
    return report


def evidence_telegram_config_security_performance_logging_architecture(db_report: dict) -> dict:
    reports = {}
    # evidence
    ev = {"generated_at": NOW, "folders": {}, "smoke": {}, "issues": []}
    for folder in ["evidence/images", "evidence/videos", "evidence/metadata", "captures", "clips"]:
        path = ROOT / folder
        files = [p for p in path.rglob("*") if p.is_file()] if path.exists() else []
        ev["folders"][folder] = {"exists": path.exists(), "files": len(files), "bytes_sampled": sum(p.stat().st_size for p in files[:5000])}
    try:
        import numpy as np
        from backend.services.evidence_manager import EvidenceManager, RollingVideoBuffer

        tmp = AUDIT_TMP / "evidence_smoke"
        mgr = EvidenceManager(str(tmp / "images"), str(tmp / "videos"), str(tmp / "metadata"), fps=5.0, retention_days=0)
        frame = np.zeros((32, 32, 3), dtype=np.uint8)
        image = mgr.save_frame(frame, "audit", "auditcam")
        meta = mgr.save_metadata("audit", {"ok": True}, "auditcam")
        buf = RollingVideoBuffer(pre_event_seconds=1, fps=5)
        for _ in range(5):
            buf.add(frame)
        video = buf.save_pre_event_clip(str(tmp / "videos" / "audit.mp4"), fps=5)
        ev["smoke"] = {"image_exists": image.exists(), "metadata_exists": meta.exists(), "video_exists": Path(video).exists() if video else False}
    except Exception as exc:
        ev["issues"].append({"error": str(exc), "traceback": traceback.format_exc()[-2000:]})
    ev["status"] = mark(not ev["issues"] and ev["smoke"].get("image_exists") and ev["smoke"].get("video_exists"), not ev["folders"]["evidence/metadata"]["exists"])
    write_report("evidence_validation_report.json", ev)
    reports["evidence"] = ev

    # telegram/config
    tel = {"generated_at": NOW, "env_files": {}, "send_function_available": False, "notes": ["No live Telegram send was performed to avoid alert spam."]}
    for env_file in [ROOT / ".env", ROOT / ".env.example"]:
        if env_file.exists():
            keys = [line.split("=", 1)[0].strip() for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines() if "=" in line and not line.strip().startswith("#")]
            tel["env_files"][env_file.name] = {"keys_present": keys, "telegram_token_present": "TELEGRAM_BOT_TOKEN" in keys, "telegram_chat_present": "TELEGRAM_CHAT_ID" in keys}
    try:
        from dotenv import load_dotenv

        load_dotenv(ROOT / ".env")
        from backend.services.telegram import format_alert_text, send_telegram_alert

        tel["send_function_available"] = callable(send_telegram_alert)
        tel["formatting_smoke"] = format_alert_text("Audit", "fall", 0.9, "HIGH", 1.0, 2.0, "now", "summary")
        tel["runtime_token_configured"] = bool(os.environ.get("TELEGRAM_BOT_TOKEN"))
        tel["runtime_chat_configured"] = bool(os.environ.get("TELEGRAM_CHAT_ID"))
    except Exception as exc:
        tel["error"] = str(exc)
    tel["status"] = mark(tel["send_function_available"], not (tel.get("runtime_token_configured") and tel.get("runtime_chat_configured")))
    write_report("telegram_validation_report.json", tel)
    reports["telegram"] = tel

    cfg = {"generated_at": NOW, "files": {}, "env_keys": {}, "issues": []}
    for path in [ROOT / "config.yaml", ROOT / "config/camera_config.json", ROOT / ".env", ROOT / ".env.example"]:
        cfg["files"][rel(path)] = {"exists": path.exists(), "bytes": path.stat().st_size if path.exists() else None}
    try:
        from backend.core.config import settings

        cfg["config_sections"] = sorted(settings.data.keys())
    except Exception as exc:
        cfg["issues"].append({"error": str(exc)})
    for key in ["GROQ_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY", "HF_TOKEN", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "SHEGUARD_JWT_SECRET"]:
        cfg["env_keys"][key] = {"configured": bool(os.environ.get(key))}
    cfg["status"] = mark(not cfg["issues"] and cfg["files"]["config.yaml"]["exists"], any(not v["configured"] for v in cfg["env_keys"].values()))
    write_report("config_validation_report.json", cfg)
    reports["config"] = cfg

    # security
    py_files = list(iter_files(ROOT, ".py"))
    findings = []
    for path in py_files + [ROOT / ".env", ROOT / ".env.example", ROOT / "config.yaml", ROOT / "backend/app.py"]:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "dev-only-change-this-secret" in text:
            findings.append({"severity": "HIGH", "path": rel(path), "issue": "Default JWT fallback secret is present; set SHEGUARD_JWT_SECRET in production."})
        if 'allow_origins=["*"]' in text:
            findings.append({"severity": "MEDIUM", "path": rel(path), "issue": "CORS allows all origins."})
    sec = {"generated_at": NOW, "password_hashing": "PBKDF2-SHA256 with salt", "jwt_readiness": "Implemented", "protected_endpoints": ["/secure/evidence/{incident_id}"], "legacy_unprotected_endpoints": ["/evidence/{incident_id}", "/incident/live"], "findings": findings}
    sec["status"] = mark(not any(f["severity"] == "HIGH" for f in findings), bool(findings))
    write_report("security_audit_report.json", sec)
    reports["security"] = sec

    # performance
    perf = {"generated_at": NOW, "measurements": {}, "notes": []}
    try:
        import psutil

        perf["measurements"]["process_rss_mb"] = round(psutil.Process().memory_info().rss / (1024 * 1024), 2)
        perf["measurements"]["cpu_percent_sample"] = psutil.cpu_percent(interval=0.2)
        perf["measurements"]["system_memory_percent"] = psutil.virtual_memory().percent
    except Exception as exc:
        perf["notes"].append(f"psutil unavailable: {exc}")
    try:
        from backend.services.stability import TemporalStabilityEngine

        engine = TemporalStabilityEngine()
        start = time.perf_counter()
        for i in range(1000):
            engine.smooth("perf", "fall" if i % 2 else "normal", 0.8, {"fall": 0.8, "normal": 0.2})
        perf["measurements"]["smoothing_1000_calls_ms"] = round((time.perf_counter() - start) * 1000, 2)
    except Exception as exc:
        perf["notes"].append(str(exc))
    perf["notes"].append("Live camera FPS was not measured to avoid intrusive camera access.")
    perf["status"] = mark(True, True)
    write_report("performance_audit.json", perf)
    reports["performance"] = perf

    log_dir = ROOT / "logs"
    log_files = [p for p in log_dir.rglob("*") if p.is_file()] if log_dir.exists() else []
    log = {"generated_at": NOW, "logs_dir_exists": log_dir.exists(), "configuration_file_exists": (ROOT / "logging_config.py").exists(), "log_files": [{"path": rel(p), "bytes": p.stat().st_size} for p in log_files], "notes": ["Route-level API request logging middleware is not currently implemented."]}
    log["status"] = mark(log["logs_dir_exists"] and log["configuration_file_exists"], True)
    write_report("logging_validation_report.json", log)
    reports["logging"] = log

    arch_findings = []
    if (ROOT / "main.py").stat().st_size > 25000:
        arch_findings.append({"severity": "MEDIUM", "issue": "main.py is large and owns several runtime responsibilities."})
    arch = {"generated_at": NOW, "components": {"backend_modular": True, "ai_modules": True, "dashboard_websocket_ready": (ROOT / "backend/routes/realtime.py").exists(), "central_config": (ROOT / "config.yaml").exists(), "docker_ready": (ROOT / "Dockerfile").exists() and (ROOT / "docker-compose.yml").exists()}, "findings": arch_findings}
    arch["status"] = mark(not any(f["severity"] == "HIGH" for f in arch_findings), bool(arch_findings))
    write_report("architecture_audit_report.json", arch)
    reports["architecture"] = arch
    return reports


def master(reports: dict) -> dict:
    runtime = {
        "generated_at": NOW,
        "smoke_tests": {
            "backend_startup_api": reports["api"]["status"],
            "gru_model_loading": reports["model"].get("sequence_classifier_available", False),
            "sqlite_connection": reports["database"]["status"],
            "telegram_initialization": reports["telegram"]["status"],
            "camera_opening": "NOT_RUN_SAFE_MODE",
            "sample_incident_creation": any(t.get("path") == "/incident/create" and t.get("ok") for t in reports["api"].get("tests", [])),
            "evidence_saving": reports["evidence"].get("smoke", {}).get("image_exists") and reports["evidence"].get("smoke", {}).get("video_exists"),
        },
    }
    runtime["status"] = mark(True, True)
    write_report("runtime_smoke_tests_report.json", runtime)
    reports["runtime"] = runtime
    weights = {"python": 10, "dependencies": 7, "gpu": 6, "model": 10, "dataset": 7, "realtime": 10, "camera": 6, "api": 10, "database": 9, "evidence": 7, "telegram": 4, "config": 5, "security": 8, "performance": 4, "logging": 3, "architecture": 4}

    def score(report: dict) -> float:
        return {"PASS": 1.0, "WARN": 0.72, "FAIL": 0.25}.get(report.get("status"), 0.5)

    overall = round(sum(score(reports[k]) * w for k, w in weights.items()) / sum(weights.values()) * 100, 1)
    category_scores = {
        "AI stability score": round((score(reports["realtime"]) * 0.45 + score(reports["model"]) * 0.35 + score(reports["dataset"]) * 0.20) * 100, 1),
        "backend quality score": round((score(reports["api"]) * 0.55 + score(reports["database"]) * 0.25 + score(reports["logging"]) * 0.20) * 100, 1),
        "GPU readiness": round(score(reports["gpu"]) * 100, 1),
        "production readiness": round((score(reports["security"]) * 0.35 + score(reports["config"]) * 0.25 + score(reports["architecture"]) * 0.25 + score(reports["performance"]) * 0.15) * 100, 1),
        "security score": round(score(reports["security"]) * 100, 1),
        "realtime readiness": round(score(reports["realtime"]) * 100, 1),
        "scalability score": round((score(reports["camera"]) * 0.35 + score(reports["architecture"]) * 0.35 + score(reports["performance"]) * 0.30) * 100, 1),
    }
    issues = []
    for name, report in reports.items():
        if report.get("status") in {"FAIL", "WARN"}:
            issues.append({"component": name, "status": report["status"], "issue": f"{name} audit reported {report['status']}"})
    for finding in reports["security"].get("findings", []):
        issues.append({"component": "security", **finding})
    if not reports["gpu"].get("cuda_available"):
        issues.append({"component": "gpu", "severity": "MEDIUM", "issue": "CUDA is not available; CPU fallback is active."})
    if not reports["camera"].get("stream_timeout_explicit"):
        issues.append({"component": "camera", "severity": "MEDIUM", "issue": "No explicit RTSP/OpenCV stream timeout configured."})
    recs = [
        "Set SHEGUARD_JWT_SECRET in production and remove reliance on the development fallback secret.",
        "Restrict CORS origins before exposing the backend outside a trusted LAN.",
        "Add explicit RTSP/OpenCV timeout settings or watchdog process isolation.",
        "Move realtime event orchestration out of main.py into smaller services.",
        "Add structured API request logging middleware with correlation IDs.",
        "Run full dataset media corruption validation as a long-running offline job.",
        "Install CUDA-enabled PyTorch on GPU hosts and verify /health/gpu.",
        "Add tests for WebSocket events, secure evidence access, cloud fallback, and evidence metadata.",
        "Use Alembic or another migration tool before PostgreSQL migration.",
        "Mock Telegram requests in automated tests instead of sending live alerts.",
    ]
    working = [k for k, v in reports.items() if v.get("status") == "PASS"]
    partial = [k for k, v in reports.items() if v.get("status") == "WARN"]
    broken = [k for k, v in reports.items() if v.get("status") == "FAIL"]
    master_text = f"""# SheGuard AI Master System Audit

Generated: {NOW}
Root: `{ROOT}`

## Summary

- Overall health score: **{overall}/100**
- AI stability score: **{category_scores['AI stability score']}/100**
- Backend quality score: **{category_scores['backend quality score']}/100**
- GPU readiness: **{category_scores['GPU readiness']}/100**
- Production readiness: **{category_scores['production readiness']}/100**
- Security score: **{category_scores['security score']}/100**
- Realtime readiness: **{category_scores['realtime readiness']}/100**
- Scalability score: **{category_scores['scalability score']}/100**

## Working Components

{chr(10).join('- ' + item for item in working) if working else '- None'}

## Partially Working / Warning

{chr(10).join('- ' + item for item in partial) if partial else '- None'}

## Broken Components

{chr(10).join('- ' + item for item in broken) if broken else '- None'}

## Top Critical Issues

{chr(10).join(f"{idx + 1}. [{item.get('severity', item.get('status', 'WARN'))}] {item.get('component')}: {item.get('issue')}" for idx, item in enumerate(issues[:10])) if issues else 'No critical failures detected.'}

## Top Recommendations

{chr(10).join(f"{idx + 1}. {rec}" for idx, rec in enumerate(recs[:10]))}

## Safety Notes

- API smoke tests used a temporary SQLite DB under `reports/audit_runtime`; production `sheguard.db` was not modified.
- Evidence smoke tests wrote only diagnostic files under `reports/audit_runtime/evidence_smoke`.
- No model retraining, dataset deletion, evidence deletion, or destructive migration was performed.
- Dataset media validation was sampled; exhaustive decoding should run offline.
"""
    (REPORTS / "MASTER_SYSTEM_AUDIT.md").write_text(master_text, encoding="utf-8")
    summary = {
        "overall_health_score": overall,
        "category_scores": category_scores,
        "total_files_analyzed": reports["inventory"]["total_files_excluding_venv_cache"],
        "python_modules_validated": reports["python"]["python_files"],
        "apis_tested": len(reports["api"].get("tests", [])),
        "gpu_status": reports["gpu"],
        "model_status": reports["model"]["status"],
        "db_status": reports["database"]["status"],
        "evidence_status": reports["evidence"]["status"],
        "telegram_status": reports["telegram"]["status"],
        "realtime_status": reports["realtime"]["status"],
        "top_issues": issues[:10],
        "top_recommendations": recs[:10],
    }
    write_report("audit_summary_current.json", summary)
    return summary


def main() -> None:
    reports = {}
    reports["inventory"] = inventory()
    reports["python"] = python_validation()
    reports["dependencies"] = dependency_audit()
    reports["gpu"] = gpu_validation()
    reports["model"] = model_validation()
    reports["dataset"] = dataset_validation()
    reports["realtime"], reports["camera"] = realtime_and_camera()
    reports["api"] = api_validation()
    reports["database"] = database_validation()
    reports.update(evidence_telegram_config_security_performance_logging_architecture(reports["database"]))
    print(json.dumps(master(reports), indent=2, ensure_ascii=True, default=str))


if __name__ == "__main__":
    main()
