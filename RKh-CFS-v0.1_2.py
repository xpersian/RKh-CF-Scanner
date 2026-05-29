#!/usr/bin/env python3
"""
RKh-CFS v0.1 - User-friendly Cloudflare Clean-IP scanner for VLESS configs.

Place xray.exe beside this script on Windows, or xray beside this script on Linux/macOS.
The scanner replaces only the outbound server address with each candidate IP while
preserving SNI/Host/path from the original VLESS config, then measures real latency
through Xray's local SOCKS proxy.

Use only on IPs/ranges you own or are authorized to test. Keep concurrency modest.
"""
from __future__ import annotations

import argparse
import csv
import ipaddress
import json
import os
import platform
import random
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

try:
    import requests
except Exception:
    requests = None

try:
    from rich import box
    from rich.align import Align
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
    from rich.prompt import Confirm, IntPrompt, Prompt
    from rich.table import Table
    from rich.text import Text
    RICH = True
except Exception:
    RICH = False

APP_NAME = "RKh-CFS"
APP_VERSION = "v0.1.2"
APP_CHANNEL = "@pingplas_channel"
APP_TITLE = f"{APP_NAME} {APP_VERSION}"
APP_HEADER = f"{APP_TITLE} | {APP_CHANNEL}"
DEFAULT_URL = "https://cp.cloudflare.com/generate_204"
DEFAULT_TIMEOUT = 8
DEFAULT_CONCURRENCY = 10
DEFAULT_TRIES = 1
MAX_DEFAULT_HOSTS = 4096

console = Console() if RICH else None
_print_lock = threading.Lock()


@dataclass
class VlessConfig:
    raw: str
    uuid: str
    host: str
    port: int
    remark: str
    query: Dict[str, str]


@dataclass
class ScanResult:
    ip: str
    ok: bool
    latency_ms: Optional[float] = None
    status_code: Optional[int] = None
    error: str = ""


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def cprint(text: str = "", style: Optional[str] = None) -> None:
    if RICH:
        console.print(text, style=style)
    else:
        print(text)


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def show_banner() -> None:
    clear_screen()
    if RICH:
        logo = Text()
        logo.append("\n  ██████╗ ██╗  ██╗██╗  ██╗      ██████╗███████╗███████╗\n", style="bold cyan")
        logo.append("  ██╔══██╗██║ ██╔╝██║  ██║     ██╔════╝██╔════╝██╔════╝\n", style="bold cyan")
        logo.append("  ██████╔╝█████╔╝ ███████║     ██║     █████╗  ███████╗\n", style="bold cyan")
        logo.append("  ██╔══██╗██╔═██╗ ██╔══██║     ██║     ██╔══╝  ╚════██║\n", style="bold cyan")
        logo.append("  ██║  ██║██║  ██╗██║  ██║     ╚██████╗██║     ███████║\n", style="bold cyan")
        logo.append("  ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝      ╚═════╝╚═╝     ╚══════╝\n", style="bold cyan")
        subtitle = Text("Cloudflare Clean-IP Scanner for VLESS + Xray Core", style="white")
        version = Text(f"{APP_HEADER}", style="bold magenta")
        console.print(Panel(Align.center(logo + Text("\n") + version + Text("\n") + subtitle), border_style="cyan", box=box.DOUBLE))
    else:
        print(f"==== {APP_HEADER} - Cloudflare Clean-IP Scanner ====")


def pause(message: str = "Press Enter to continue") -> None:
    try:
        if RICH:
            Prompt.ask(f"[dim]{message}[/dim]", default="")
        else:
            input(message)
    except KeyboardInterrupt:
        raise


def prompt_str(message: str, default: Optional[str] = None, password: bool = False) -> str:
    if RICH:
        return Prompt.ask(message, default=default, password=password).strip()
    suffix = f" [{default}]" if default else ""
    val = input(f"{message}{suffix}: ").strip()
    return val or (default or "")


def prompt_int(message: str, default: int, min_value: int = 1, max_value: Optional[int] = None) -> int:
    while True:
        try:
            if RICH:
                value = IntPrompt.ask(message, default=default)
            else:
                raw = input(f"{message} [{default}]: ").strip()
                value = int(raw or default)
            if value < min_value or (max_value is not None and value > max_value):
                raise ValueError
            return value
        except Exception:
            cprint(f"Please enter a number between {min_value} and {max_value or '∞'}.", "yellow")


def prompt_confirm(message: str, default: bool = True) -> bool:
    if RICH:
        return Confirm.ask(message, default=default)
    raw = input(f"{message} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes", "1", "true"}


def parse_vless(uri_or_file: str) -> VlessConfig:
    value = uri_or_file.strip().strip('"').strip("'")
    possible = Path(value)
    if not value.startswith("vless://") and possible.exists():
        value = possible.read_text(encoding="utf-8").strip()
    if not value.startswith("vless://"):
        raise ValueError("VLESS config must start with vless:// or be a file containing a vless:// link.")
    parsed = urlparse(value)
    uuid = parsed.username or parsed.netloc.split("@")[0]
    host = parsed.hostname or ""
    port = parsed.port or 443
    if not uuid or not host:
        raise ValueError("Invalid VLESS link: missing UUID or server address.")
    query_multi = parse_qs(parsed.query, keep_blank_values=True)
    query = {k: unquote(v[-1]) if v else "" for k, v in query_multi.items()}
    remark = unquote(parsed.fragment or "RKh-CFS")
    return VlessConfig(raw=value, uuid=uuid, host=host, port=port, remark=remark, query=query)


def expand_targets(items: Iterable[str], max_hosts: int = MAX_DEFAULT_HOSTS) -> List[str]:
    out: List[str] = []
    seen = set()

    def add(ip: str) -> None:
        if ip not in seen:
            seen.add(ip)
            out.append(ip)
            if len(out) > max_hosts:
                raise ValueError(f"Too many targets. Current limit is {max_hosts}. Use --max-hosts to raise it.")

    for item in items:
        item = item.strip().strip(",")
        if not item or item.startswith("#"):
            continue
        p = Path(item)
        if p.exists() and p.is_file():
            lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
            for ip in expand_targets(lines, max_hosts=max_hosts - len(out)):
                add(ip)
            continue
        if "/" in item:
            net = ipaddress.ip_network(item, strict=False)
            for ip in net.hosts() if net.num_addresses > 2 else net:
                add(str(ip))
            continue
        if "-" in item:
            start_s, end_s = [x.strip() for x in item.split("-", 1)]
            start, end = ipaddress.ip_address(start_s), ipaddress.ip_address(end_s)
            if start.version != end.version or int(end) < int(start):
                raise ValueError(f"Invalid IP range: {item}")
            for n in range(int(start), int(end) + 1):
                add(str(ipaddress.ip_address(n)))
            continue
        add(str(ipaddress.ip_address(item)))
    return out


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def find_xray(explicit: Optional[str] = None) -> Optional[Path]:
    candidates: List[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    base = app_dir()
    exe = "xray.exe" if platform.system().lower().startswith("win") else "xray"
    candidates.extend([base / exe, base / "xray.exe", base / "xray"])
    for c in candidates:
        if c.exists() and c.is_file():
            return c.resolve()
    from_path = shutil.which("xray")
    if from_path:
        return Path(from_path).resolve()
    return None


def check_environment(xray_path: Optional[Path]) -> bool:
    ok = True
    rows = []
    base = app_dir()
    for name, exists in [
        ("xray.exe / xray", bool(xray_path)),
        ("geoip.dat", (base / "geoip.dat").exists()),
        ("geosite.dat", (base / "geosite.dat").exists()),
        ("requests[socks]", requests is not None),
    ]:
        rows.append((name, exists))
        if name in {"xray.exe / xray", "requests[socks]"} and not exists:
            ok = False
    if RICH:
        table = Table(title="Startup Check", box=box.ROUNDED, border_style="cyan")
        table.add_column("Component", style="white")
        table.add_column("Status")
        for name, exists in rows:
            table.add_row(name, "[green]FOUND[/green]" if exists else "[red]MISSING[/red]")
        console.print(table)
    else:
        for name, exists in rows:
            print(f"{'OK' if exists else 'MISSING'} - {name}")
    if not ok:
        cprint("\nPlace xray.exe in the application folder and install dependencies with: pip install -r requirements.txt", "yellow")
    return ok


def vless_to_xray_outbound(v: VlessConfig, server_ip: str) -> Dict:
    q = v.query
    network = (q.get("type") or q.get("network") or "tcp").lower()
    security = (q.get("security") or "none").lower()
    flow = q.get("flow", "")
    outbound = {
        "tag": "proxy",
        "protocol": "vless",
        "settings": {"vnext": [{"address": server_ip, "port": v.port, "users": [{"id": v.uuid, "encryption": q.get("encryption", "none")}]}]},
        "streamSettings": {"network": network, "security": security},
    }
    if flow:
        outbound["settings"]["vnext"][0]["users"][0]["flow"] = flow
    sni = q.get("sni") or q.get("servername") or q.get("serverName") or v.host
    fp = q.get("fp") or q.get("fingerprint") or "chrome"
    alpn = q.get("alpn", "")
    if security in {"tls", "reality"}:
        tls_key = "realitySettings" if security == "reality" else "tlsSettings"
        outbound["streamSettings"][tls_key] = {"serverName": sni, "fingerprint": fp, "allowInsecure": q.get("allowInsecure", "0") in {"1", "true"}}
        if alpn:
            outbound["streamSettings"][tls_key]["alpn"] = [x.strip() for x in alpn.split(",") if x.strip()]
        if security == "reality":
            if q.get("pbk"):
                outbound["streamSettings"][tls_key]["publicKey"] = q.get("pbk")
            if q.get("sid"):
                outbound["streamSettings"][tls_key]["shortId"] = q.get("sid")
            if q.get("spx"):
                outbound["streamSettings"][tls_key]["spiderX"] = q.get("spx")
    host_header = q.get("host") or q.get("authority") or sni
    path = q.get("path") or "/"
    if network == "ws":
        outbound["streamSettings"]["wsSettings"] = {"path": path, "headers": {"Host": host_header}}
    elif network == "grpc":
        outbound["streamSettings"]["grpcSettings"] = {"serviceName": q.get("serviceName") or q.get("serviceNameMode") or q.get("path", "").strip("/")}
    elif network in {"http", "h2"}:
        outbound["streamSettings"]["httpSettings"] = {"path": path, "host": [host_header]}
    elif network in {"httpupgrade", "httpupgrade".lower()}:
        outbound["streamSettings"]["httpupgradeSettings"] = {"path": path, "host": host_header}
    elif network in {"xhttp", "splithttp"}:
        outbound["streamSettings"]["splithttpSettings"] = {"path": path, "host": host_header}
    elif network == "tcp" and q.get("headerType") == "http":
        outbound["streamSettings"]["tcpSettings"] = {"header": {"type": "http", "request": {"path": [path], "headers": {"Host": [host_header]}}}}
    return outbound


def make_xray_config(v: VlessConfig, server_ip: str, socks_port: int, loglevel: str) -> Dict:
    return {
        "log": {"loglevel": loglevel},
        "inbounds": [{"tag": "socks-in", "listen": "127.0.0.1", "port": socks_port, "protocol": "socks", "settings": {"udp": False}}],
        "outbounds": [vless_to_xray_outbound(v, server_ip), {"tag": "direct", "protocol": "freedom"}, {"tag": "block", "protocol": "blackhole"}],
    }


def wait_port(port: int, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return True
        except OSError:
            time.sleep(0.05)
    return False


def test_ip(v: VlessConfig, ip: str, xray: Path, timeout: int, tries: int, url: str, loglevel: str, keep_configs: bool = False) -> ScanResult:
    last_error = ""
    for _ in range(max(1, tries)):
        socks_port = free_port()
        temp_dir_obj = tempfile.TemporaryDirectory(prefix="rkh_cfs_")
        temp_dir = Path(temp_dir_obj.name)
        cfg_path = temp_dir / "config.json"
        cfg_path.write_text(json.dumps(make_xray_config(v, ip, socks_port, loglevel), indent=2), encoding="utf-8")
        proc = None
        start = time.perf_counter()
        try:
            proc = subprocess.Popen([str(xray), "run", "-config", str(cfg_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(app_dir()))
            if not wait_port(socks_port, min(3.0, timeout)):
                last_error = "Xray SOCKS port did not start"
                continue
            if requests is None:
                return ScanResult(ip=ip, ok=False, error="Python package requests[socks] is not installed")
            proxies = {"http": f"socks5h://127.0.0.1:{socks_port}", "https": f"socks5h://127.0.0.1:{socks_port}"}
            r = requests.get(url, proxies=proxies, timeout=timeout, headers={"User-Agent": f"{APP_HEADER}"})
            latency = (time.perf_counter() - start) * 1000
            if 200 <= r.status_code < 400:
                return ScanResult(ip=ip, ok=True, latency_ms=latency, status_code=r.status_code)
            last_error = f"HTTP {r.status_code}"
        except Exception as exc:
            last_error = str(exc).split("\n", 1)[0][:160]
        finally:
            if proc is not None:
                try:
                    proc.terminate()
                    proc.wait(timeout=1)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
            if keep_configs:
                keep_dir = app_dir() / "configs" / "temp"
                keep_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(cfg_path, keep_dir / f"{ip.replace(':','_')}_{int(time.time())}.json")
            temp_dir_obj.cleanup()
    return ScanResult(ip=ip, ok=False, error=last_error or "Failed")


def save_results(results: List[ScanResult], output_dir: Path) -> Tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    ok = sorted([r for r in results if r.ok], key=lambda r: r.latency_ms or 10**9)
    txt_path = output_dir / "clean_ips.txt"
    csv_path = output_dir / "clean_ips.csv"
    txt_path.write_text("\n".join(f"{r.ip} | {r.latency_ms:.1f} ms | HTTP {r.status_code}" for r in ok) + ("\n" if ok else ""), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ip", "latency_ms", "status_code", "tested_at"])
        now = datetime.now().isoformat(timespec="seconds")
        for r in ok:
            w.writerow([r.ip, f"{r.latency_ms:.1f}", r.status_code, now])
    return txt_path, csv_path


def show_config_summary(v: VlessConfig) -> None:
    q = v.query
    if RICH:
        table = Table(title="Configuration Summary", box=box.ROUNDED, border_style="green")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        table.add_row("Original Address", v.host)
        table.add_row("Port", str(v.port))
        table.add_row("Transport", q.get("type") or q.get("network") or "tcp")
        table.add_row("Security", q.get("security", "none"))
        table.add_row("SNI", q.get("sni") or q.get("servername") or v.host)
        table.add_row("Host Header", q.get("host") or q.get("authority") or q.get("sni") or v.host)
        table.add_row("Path", q.get("path", "/"))
        console.print(table)
    else:
        print(f"Address: {v.host}:{v.port} | SNI: {q.get('sni') or v.host}")



def summarize_latency(samples: List[ScanResult]) -> ScanResult:
    ok_samples = [r for r in samples if r.ok and r.latency_ms is not None]
    ip = samples[0].ip if samples else ""
    if not ok_samples:
        err = samples[-1].error if samples else "No samples"
        return ScanResult(ip=ip, ok=False, error=err)
    # Use average latency as the final score, while requiring at least one successful real Xray request.
    avg = sum(r.latency_ms or 0 for r in ok_samples) / len(ok_samples)
    status = ok_samples[-1].status_code
    return ScanResult(ip=ip, ok=True, latency_ms=avg, status_code=status, error=f"{len(ok_samples)}/{len(samples)} successful samples")


def retest_ip_latency(v: VlessConfig, ip: str, xray: Path, timeout: int, sample_count: int, url: str, loglevel: str) -> ScanResult:
    samples: List[ScanResult] = []
    for _ in range(max(1, sample_count)):
        samples.append(test_ip(v, ip, xray, timeout, 1, url, loglevel, False))
    return summarize_latency(samples)


def run_latency_recheck(v: VlessConfig, ok_results: List[ScanResult], xray: Path, workers: int, timeout: int, sample_count: int, url: str, loglevel: str) -> List[ScanResult]:
    ips = [r.ip for r in sorted(ok_results, key=lambda r: r.latency_ms or 10**9)]
    if not ips:
        return []
    results: List[ScanResult] = []
    if RICH:
        title = f"Re-checking latency: {sample_count} real Xray test(s) per IP"
        progress = Progress(SpinnerColumn(), TextColumn("[bold magenta]{task.description}"), BarColumn(), TextColumn("{task.completed}/{task.total}"), TimeElapsedColumn(), console=console)
        with progress:
            task = progress.add_task(title, total=len(ips))
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futures = {ex.submit(retest_ip_latency, v, ip, xray, timeout, sample_count, url, loglevel): ip for ip in ips}
                for fut in as_completed(futures):
                    r = fut.result()
                    results.append(r)
                    if r.ok:
                        console.print(f"[bright_green]RE-OK[/bright_green] {r.ip:<39} [bold]{r.latency_ms:.1f} ms avg[/bold]  ({r.error})")
                    else:
                        console.print(f"[red]DROP[/red]  {r.ip:<39} {r.error}")
                    progress.advance(task)
    else:
        done = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(retest_ip_latency, v, ip, xray, timeout, sample_count, url, loglevel): ip for ip in ips}
            for fut in as_completed(futures):
                r = fut.result()
                results.append(r)
                done += 1
                if r.ok:
                    print(f"RE-OK {r.ip:<39} {r.latency_ms:.1f} ms avg ({r.error})")
                print(f"Re-check progress: {done}/{len(ips)}", end="\r")
        print()
    return results

def interactive() -> None:
    show_banner()
    xray = find_xray()
    check_environment(xray)
    if not xray or requests is None:
        pause()
        return

    if RICH:
        console.print(Panel("[bold]Start New Scan[/bold]\n\nThis wizard will ask for your VLESS config, targets, and scan settings.", border_style="magenta"))

    # Step 1
    while True:
        cprint("\n[bold cyan]Step 1/4 - VLESS Configuration[/bold cyan]" if RICH else "\nStep 1/4 - VLESS Configuration")
        cprint("Paste a vless:// link or enter a file path containing one.", "dim")
        raw = prompt_str("VLESS config")
        try:
            v = parse_vless(raw)
            cprint("Configuration loaded successfully.", "green")
            show_config_summary(v)
            break
        except Exception as e:
            cprint(f"Invalid configuration: {e}", "red")

    # Step 2
    while True:
        cprint("\n[bold cyan]Step 2/4 - Target IPs[/bold cyan]" if RICH else "\nStep 2/4 - Target IPs")
        cprint("Examples: 104.16.0.1 | 104.16.0.0/24 | 104.16.0.1-104.16.0.255 | ips.txt", "dim")
        raw_targets = prompt_str("Targets").replace(",", " ").split()
        try:
            targets = expand_targets(raw_targets, max_hosts=MAX_DEFAULT_HOSTS)
            cprint(f"Loaded {len(targets)} target(s).", "green")
            break
        except Exception as e:
            cprint(f"Invalid targets: {e}", "red")

    # Step 3
    cprint("\n[bold cyan]Step 3/4 - Scan Settings[/bold cyan]" if RICH else "\nStep 3/4 - Scan Settings")
    cprint("Choose how many workers should test IPs at the same time. Higher is faster, but heavier.", "dim")
    concurrency = prompt_int("Scan workers", DEFAULT_CONCURRENCY, 1, 100)
    timeout = prompt_int("Connection timeout seconds", DEFAULT_TIMEOUT, 2, 60)
    tries = DEFAULT_TRIES
    test_url = prompt_str("Test URL", DEFAULT_URL)
    output_dir = app_dir() / "results"

    # Step 4
    cprint("\n[bold cyan]Step 4/4 - Ready[/bold cyan]" if RICH else "\nStep 4/4 - Ready")
    if RICH:
        panel = f"Targets: [bold]{len(targets)}[/bold]\nConcurrency: [bold]{concurrency}[/bold]\nTimeout: [bold]{timeout}s[/bold]\nXray: [bold]{xray.name}[/bold]\nOutput: [bold]{output_dir}[/bold]"
        console.print(Panel(panel, title="Scan Plan", border_style="green"))
    else:
        print(f"Targets: {len(targets)} | Concurrency: {concurrency} | Timeout: {timeout}s")
    if not prompt_confirm("Start scan now?", True):
        cprint("Scan canceled.", "yellow")
        return

    results = run_scan(v, targets, xray, concurrency, timeout, tries, test_url, "warning", False)
    txt, csvp = save_results(results, output_dir)
    show_final_results(results, txt, csvp)

    ok_results = [r for r in results if r.ok]
    if ok_results and prompt_confirm("Run a second latency check for working IPs?", True):
        sample_count = prompt_int("Latency tests per IP", 5, 1, 20)
        recheck_workers = prompt_int("Re-check workers", min(concurrency, 10), 1, 100)
        rechecked = run_latency_recheck(v, ok_results, xray, recheck_workers, timeout, sample_count, test_url, "warning")
        retxt, recsv = save_results(rechecked, output_dir)
        show_final_results(rechecked, retxt, recsv)


def run_scan(v: VlessConfig, targets: List[str], xray: Path, concurrency: int, timeout: int, tries: int, url: str, loglevel: str, keep_configs: bool) -> List[ScanResult]:
    results: List[ScanResult] = []
    if RICH:
        progress = Progress(SpinnerColumn(), TextColumn("[bold cyan]{task.description}"), BarColumn(), TextColumn("{task.completed}/{task.total}"), TimeElapsedColumn(), console=console)
        with progress:
            task = progress.add_task("Scanning", total=len(targets))
            with ThreadPoolExecutor(max_workers=concurrency) as ex:
                futures = {ex.submit(test_ip, v, ip, xray, timeout, tries, url, loglevel, keep_configs): ip for ip in targets}
                for fut in as_completed(futures):
                    r = fut.result()
                    results.append(r)
                    if r.ok:
                        console.print(f"[green]OK[/green]  {r.ip:<39} [bold]{r.latency_ms:.1f} ms[/bold]  HTTP {r.status_code}")
                    progress.advance(task)
    else:
        done = 0
        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            futures = {ex.submit(test_ip, v, ip, xray, timeout, tries, url, loglevel, keep_configs): ip for ip in targets}
            for fut in as_completed(futures):
                r = fut.result()
                results.append(r)
                done += 1
                if r.ok:
                    print(f"OK {r.ip:<39} {r.latency_ms:.1f} ms HTTP {r.status_code}")
                print(f"Progress: {done}/{len(targets)}", end="\r")
        print()
    return results


def show_final_results(results: List[ScanResult], txt_path: Path, csv_path: Path) -> None:
    ok = sorted([r for r in results if r.ok], key=lambda r: r.latency_ms or 10**9)
    failed = len(results) - len(ok)
    if RICH:
        console.print(Panel(f"[bold green]Scan Finished[/bold green]\n\nWorking IPs: [bold green]{len(ok)}[/bold green]\nFailed IPs: [bold red]{failed}[/bold red]", border_style="green"))
        table = Table(title="Best Results", box=box.ROUNDED, border_style="cyan")
        table.add_column("#", justify="right", style="dim")
        table.add_column("IP", style="white")
        table.add_column("Latency", justify="right", style="green")
        table.add_column("HTTP", justify="right")
        for i, r in enumerate(ok[:20], 1):
            table.add_row(str(i), r.ip, f"{r.latency_ms:.1f} ms", str(r.status_code))
        console.print(table)
        console.print(f"[green]Saved TXT:[/green] {txt_path}")
        console.print(f"[green]Saved CSV:[/green] {csv_path}")
    else:
        print(f"\nScan Finished | Working: {len(ok)} | Failed: {failed}")
        for i, r in enumerate(ok[:20], 1):
            print(f"{i}. {r.ip} {r.latency_ms:.1f} ms HTTP {r.status_code}")
        print(f"Saved TXT: {txt_path}\nSaved CSV: {csv_path}")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=f"{APP_HEADER} - Cloudflare Clean-IP scanner for VLESS + Xray")
    p.add_argument("-c", "--config", help="VLESS URI or text file containing a VLESS URI")
    p.add_argument("-t", "--targets", nargs="*", help="IP, CIDR, range, or file path")
    p.add_argument("--xray", help="Path to xray executable. Default: xray.exe/xray beside script")
    p.add_argument("-o", "--output-dir", default=str(app_dir() / "results"), help="Output folder")
    p.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    p.add_argument("--tries", type=int, default=DEFAULT_TRIES)
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    p.add_argument("--max-hosts", type=int, default=MAX_DEFAULT_HOSTS)
    p.add_argument("--url", default=DEFAULT_URL)
    p.add_argument("--loglevel", choices=["debug", "info", "warning", "error", "none"], default="warning")
    p.add_argument("--keep-configs", action="store_true")
    p.add_argument("--recheck", action="store_true", help="After the first scan, re-test working IPs and save updated results")
    p.add_argument("--recheck-samples", type=int, default=5, help="Latency tests per working IP during --recheck")
    p.add_argument("--recheck-workers", type=int, default=None, help="Workers for --recheck. Default: same as --concurrency")
    return p


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    if not args.config and not args.targets:
        try:
            interactive()
            return 0
        except KeyboardInterrupt:
            cprint("\nCanceled by user.", "yellow")
            return 130

    if not args.config or not args.targets:
        parser.error("CLI mode requires both -c/--config and -t/--targets. Run without arguments for interactive mode.")
    xray = find_xray(args.xray)
    if not xray:
        cprint("xray.exe/xray not found. Place it beside the script or pass --xray.", "red")
        return 2
    if requests is None:
        cprint("Missing dependency: pip install requests[socks] rich", "red")
        return 2
    try:
        v = parse_vless(args.config)
        targets = expand_targets(args.targets, args.max_hosts)
    except Exception as e:
        cprint(str(e), "red")
        return 2
    results = run_scan(v, targets, xray, args.concurrency, args.timeout, args.tries, args.url, args.loglevel, args.keep_configs)
    txt, csvp = save_results(results, Path(args.output_dir))
    show_final_results(results, txt, csvp)
    if args.recheck:
        ok_results = [r for r in results if r.ok]
        rechecked = run_latency_recheck(v, ok_results, xray, args.recheck_workers or args.concurrency, args.timeout, args.recheck_samples, args.url, args.loglevel)
        txt, csvp = save_results(rechecked, Path(args.output_dir))
        show_final_results(rechecked, txt, csvp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
