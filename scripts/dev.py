"""Build and run the local stack, keeping logs and owned process IDs in .runtime."""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime"


def available(port):
    with socket.socket() as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop", "status"])
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()
    RUNTIME.mkdir(exist_ok=True)
    pidfile = RUNTIME / "services.json"
    if args.action == "status":
        for name, port in [
            ("frontend", 5173),
            ("gateway", 8080),
            ("java", 8081),
            ("python", 8000),
            ("mysql", 3306),
            ("redis", 6379),
        ]:
            print(f'{name}: {"listening" if available(port) else "stopped"} ({port})')
        return
    if args.action == "stop":
        import psutil

        for entry in json.loads(pidfile.read_text()) if pidfile.exists() else []:
            try:
                proc = psutil.Process(entry["pid"])
                if abs(proc.create_time() - entry["created"]) < 1 and Path(
                    proc.cwd()
                ).resolve().is_relative_to(ROOT):
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                    except psutil.TimeoutExpired:
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        pidfile.write_text("[]")
        print("Stopped owned application services. MySQL and Redis remain available.")
        return
    if args.build:
        for folder, command in [
            (
                "nexus-java",
                [
                    "mvn.cmd" if os.name == "nt" else "mvn",
                    "-q",
                    "-DskipTests",
                    "package",
                ],
            ),
            (
                "gateway",
                [
                    "mvn.cmd" if os.name == "nt" else "mvn",
                    "-q",
                    "-DskipTests",
                    "package",
                ],
            ),
            ("frontend", ["npm.cmd" if os.name == "nt" else "npm", "run", "build"]),
        ]:
            subprocess.run(command, cwd=ROOT / folder, check=True)
    sys.path.insert(0, str(ROOT / "nexus-python"))
    from app.core.config import settings

    env = os.environ.copy()
    env.update(
        DB_HOST=settings.db.host,
        DB_PORT=str(settings.db.port),
        DB_DATABASE=settings.db.database,
        DB_USERNAME=settings.db.username,
        DB_PASSWORD=settings.db.password,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/init_db.py")], env=env, check=True
    )
    specs = [
        (
            "python",
            8000,
            [
                sys.executable,
                "-B",
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            ROOT / "nexus-python",
        ),
        (
            "java",
            8081,
            [
                "java",
                "-Duser.timezone=UTC",
                "-jar",
                str(ROOT / "nexus-java/target/nexus-java-0.0.1-SNAPSHOT.jar"),
            ],
            ROOT / "nexus-java",
        ),
        (
            "gateway",
            8080,
            [
                "java",
                "-jar",
                str(ROOT / "gateway/target/nexus-gateway-0.0.1-SNAPSHOT.jar"),
            ],
            ROOT / "gateway",
        ),
        (
            "frontend",
            5173,
            [
                "node",
                str(ROOT / "frontend/node_modules/vite/bin/vite.js"),
                "--host",
                "127.0.0.1",
            ],
            ROOT / "frontend",
        ),
    ]
    import psutil

    records = json.loads(pidfile.read_text()) if pidfile.exists() else []
    for name, port, command, cwd in specs:
        if available(port):
            print(f"{name}: already listening")
            continue
        with (RUNTIME / f"{name}.log").open("ab") as log:
            proc = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        records.append(
            {
                "name": name,
                "pid": proc.pid,
                "created": psutil.Process(proc.pid).create_time(),
            }
        )
        pidfile.write_text(json.dumps(records))
        for _ in range(60):
            if available(port):
                break
            if proc.poll() is not None:
                raise RuntimeError(f"{name} exited; inspect .runtime/{name}.log")
            time.sleep(0.5)
        else:
            raise RuntimeError(f"{name} did not start; inspect .runtime/{name}.log")
        print(f"{name}: started ({port})")
    print("Open http://127.0.0.1:5173")


if __name__ == "__main__":
    main()
