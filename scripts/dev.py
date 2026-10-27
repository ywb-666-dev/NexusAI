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


def owns_infra(name, command):
    expected = RUNTIME / ("mysql" if name.lower() in ("mysqld", "mysqld.exe") else "")
    flag = "--datadir" if name.lower() in ("mysqld", "mysqld.exe") else "--dir"
    if name.lower() not in ("mysqld", "mysqld.exe", "redis-server", "redis-server.exe"):
        return False
    for index, arg in enumerate(command):
        if arg == flag and index + 1 < len(command):
            value = command[index + 1]
        elif arg.startswith(flag + "="):
            value = arg.split("=", 1)[1]
        else:
            continue
        path = Path(value.strip('"'))
        return path.is_absolute() and path.resolve() == expected.resolve()
    return False


def stop_owned_infra():
    import psutil

    sys.path.insert(0, str(ROOT / "nexus-python"))
    from app.core.config import settings

    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            name, command = proc.info["name"] or "", proc.info["cmdline"] or []
            if not owns_infra(name, command):
                continue
            if name.lower().startswith("mysqld"):
                import pymysql

                with pymysql.connect(
                    host="127.0.0.1",
                    port=3306,
                    user=settings.db.username,
                    password=settings.db.password,
                    connect_timeout=5,
                    read_timeout=10,
                ) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT @@datadir")
                        if (
                            Path(cursor.fetchone()[0]).resolve()
                            != (RUNTIME / "mysql").resolve()
                        ):
                            raise RuntimeError(
                                "Database data directory does not match this project"
                            )
                        cursor.execute("SHUTDOWN")
            else:
                import redis

                client = redis.Redis(
                    host="127.0.0.1",
                    port=6379,
                    socket_timeout=10,
                    decode_responses=True,
                )
                if client.info("server")["process_id"] != proc.pid:
                    raise RuntimeError("Redis process does not match this project")
                if Path(client.config_get("dir")["dir"]).resolve() != RUNTIME.resolve():
                    raise RuntimeError(
                        "Redis data directory does not match this project"
                    )
                client.shutdown(save=True)
            proc.wait(timeout=20)
            print(f"Stopped project-owned {name}; data saved.")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        except Exception:
            raise RuntimeError(
                "Could not gracefully stop project infrastructure; no unrelated service was terminated."
            ) from None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop", "status"])
    parser.add_argument("--build", action="store_true")
    parser.add_argument(
        "--infra",
        action="store_true",
        help="With stop, also gracefully shut down project-owned MySQL/Redis.",
    )
    args = parser.parse_args()
    if args.infra and args.action != "stop":
        parser.error("--infra is only supported with stop")
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
                    children = proc.children(recursive=True)
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                    except psutil.TimeoutExpired:
                        proc.kill()
                    for child in children:
                        try:
                            child.terminate()
                            child.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            child.kill()
                        except psutil.NoSuchProcess:
                            pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        pidfile.write_text("[]")
        if args.infra:
            stop_owned_infra()
        print(
            "Stopped owned application services."
            + (
                " Project infrastructure checked and stopped."
                if args.infra
                else " MySQL and Redis remain available."
            )
        )
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
