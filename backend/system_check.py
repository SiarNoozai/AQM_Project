"""Lokaler LLM-Kompatibilitaets-Check.

Erkennt RAM/VRAM des Rechners und schaetzt, welche lokalen Sprachmodelle
(GGUF, Q4_K_M-Quantisierung) darauf lauffaehig sind. Die Schaetzlogik ist
inspiriert von LLMcalc (https://github.com/Raskoll2/LLMcalc).

Zusaetzlich prueft das Modul, ob LM Studio oder Ollama lokal erreichbar
sind und welches Modell dort aktuell geladen ist. Alles laeuft zu 100 %
lokal - es verlassen keine Portfoliodaten den Rechner.
"""

from __future__ import annotations

import os
import platform
import subprocess
from typing import Any

import httpx

try:
    from .recommendations import lmstudio_candidate_urls
except ImportError:
    from recommendations import lmstudio_candidate_urls

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
PROBE_TIMEOUT = 2.0

# Q4_K_M-Dateigroessen (GB) gaengiger lokaler Modelle plus Overhead-Puffer.
# Quelle der Groessen: Hugging Face GGUF-Repos; Logik angelehnt an LLMcalc.
MODEL_CATALOG: list[dict[str, Any]] = [
    {"name": "Llama 3.2 1B", "params": "1B", "sizeGb": 0.9},
    {"name": "Llama 3.2 3B", "params": "3B", "sizeGb": 2.1},
    {"name": "Phi-3.5 Mini 3.8B", "params": "3.8B", "sizeGb": 2.4},
    {"name": "Mistral 7B", "params": "7B", "sizeGb": 4.4},
    {"name": "Dolphin 2.9 Llama3 8B", "params": "8B", "sizeGb": 4.9},
    {"name": "Llama 3.1 8B", "params": "8B", "sizeGb": 4.9},
    {"name": "Qwen 2.5 14B", "params": "14B", "sizeGb": 9.0},
    {"name": "Qwen 2.5 32B", "params": "32B", "sizeGb": 19.9},
    {"name": "Llama 3.3 70B", "params": "70B", "sizeGb": 42.5},
]

CONTEXT_OVERHEAD_GB = 1.2
CPU_USABLE_RAM_FRACTION = 0.70


def _ram_gb() -> float:
    system = platform.system()
    try:
        if system == "Windows":
            import ctypes

            class MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatusEx()
            status.dwLength = ctypes.sizeof(MemoryStatusEx)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return round(status.ullTotalPhys / (1024**3), 1)
        if system == "Darwin":
            output = subprocess.check_output(["sysctl", "-n", "hw.memsize"], timeout=3)
            return round(int(output.strip()) / (1024**3), 1)
        with open("/proc/meminfo", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemTotal:"):
                    return round(int(line.split()[1]) / (1024**2), 1)
    except Exception:
        pass
    return 0.0


def _gpu_info() -> dict[str, Any]:
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            timeout=4,
            stderr=subprocess.DEVNULL,
        )
        line = output.decode("utf-8", errors="replace").strip().splitlines()[0]
        name, vram_mb = [part.strip() for part in line.split(",")[:2]]
        return {"name": name, "vramGb": round(float(vram_mb) / 1024, 1)}
    except Exception:
        pass

    if platform.system() == "Windows":
        try:
            # qwMemorySize aus der Registry ist auch bei AMD/Intel und >4 GB korrekt.
            script = (
                "$gpu = Get-CimInstance Win32_VideoController | Select-Object -First 1; "
                "$vram = 0; "
                "try { $vram = (Get-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Class\\{4d36e968-e325-11ce-bfc1-08002be10318}\\0*' "
                "-Name HardwareInformation.qwMemorySize -ErrorAction SilentlyContinue | "
                "Select-Object -ExpandProperty 'HardwareInformation.qwMemorySize' -First 1) } catch {}; "
                "if (-not $vram) { $vram = $gpu.AdapterRAM }; "
                "Write-Output ($gpu.Name + '|' + $vram)"
            )
            output = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", script],
                timeout=10,
                stderr=subprocess.DEVNULL,
            )
            line = output.decode("utf-8", errors="replace").strip()
            if "|" in line:
                name, _, vram_raw = line.partition("|")
                try:
                    vram_gb = round(float(vram_raw.strip() or 0) / (1024**3), 1)
                except ValueError:
                    vram_gb = 0.0
                if name.strip():
                    return {"name": name.strip(), "vramGb": max(vram_gb, 0.0)}
        except Exception:
            pass
    return {"name": "Keine dedizierte GPU erkannt", "vramGb": 0.0}


def _classify(size_gb: float, ram_gb: float, vram_gb: float) -> dict[str, Any]:
    required = size_gb + CONTEXT_OVERHEAD_GB
    usable_ram = ram_gb * CPU_USABLE_RAM_FRACTION

    if vram_gb and required <= vram_gb:
        return {"status": "gpu", "label": "Laeuft komplett auf der GPU (schnell)"}
    if vram_gb and required <= vram_gb + usable_ram:
        if required <= usable_ram:
            return {"status": "cpu", "label": "Laeuft im RAM auf der CPU (solide)"}
        return {"status": "partial", "label": "Laeuft mit GPU-Teilauslagerung (mittel)"}
    if required <= usable_ram:
        return {"status": "cpu", "label": "Laeuft im RAM auf der CPU (solide)"}
    return {"status": "no", "label": "Zu gross fuer diesen Rechner"}


async def _probe_lmstudio() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=PROBE_TIMEOUT, trust_env=False) as client:
        for base_url in lmstudio_candidate_urls():
            try:
                response = await client.get(f"{base_url}/v1/models")
                response.raise_for_status()
                models = [item.get("id", "?") for item in response.json().get("data", [])]
                return {"available": True, "models": models[:5], "url": base_url}
            except Exception:
                continue
    return {"available": False, "models": [], "url": lmstudio_candidate_urls()[0]}


async def _probe_ollama() -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT, trust_env=False) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            response.raise_for_status()
            models = [item.get("name", "?") for item in response.json().get("models", [])]
            return {"available": True, "models": models[:5]}
    except Exception:
        return {"available": False, "models": []}


async def build_llm_check() -> dict[str, Any]:
    ram_gb = _ram_gb()
    gpu = _gpu_info()
    vram_gb = float(gpu.get("vramGb", 0.0))

    models = []
    for entry in MODEL_CATALOG:
        verdict = _classify(float(entry["sizeGb"]), ram_gb, vram_gb)
        models.append({**entry, **verdict})

    lmstudio = await _probe_lmstudio()
    ollama = await _probe_ollama()

    return {
        "hardware": {
            "os": platform.system(),
            "ramGb": ram_gb,
            "gpuName": gpu.get("name", "unbekannt"),
            "vramGb": vram_gb,
        },
        "models": models,
        "providers": {
            "lmstudio": lmstudio,
            "ollama": {"url": OLLAMA_URL, **ollama},
        },
        "quantization": "Q4_K_M (GGUF)",
        "methodologyCredit": "Schaetzlogik inspiriert von LLMcalc - github.com/Raskoll2/LLMcalc",
        "privacyNote": (
            "Alle Angaben werden lokal auf diesem Rechner ermittelt. "
            "Bei Nutzung eines lokalen Sprachmodells verlassen keine Portfoliodaten das System."
        ),
    }
