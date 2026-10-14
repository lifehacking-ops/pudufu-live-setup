#!/usr/bin/env python3
"""프드프 라이브 OBS 자동 세팅.

실행하면 OBS 설치 확인 → 장면/프로필/이미지 설치 → OBS 실행 → 웹캠·모니터 자동 연결 순으로 진행한다.
송출처는 YouTube로 잡아 두고, 강사는 OBS 설정 → 방송에서 '계정 연결'로 유튜브에 로그인한 뒤 방송을 시작한다.
"""
import argparse
import configparser
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

# ──────────────────────────── 설정값 ────────────────────────────
COLLECTION_NAME = "프드프 라이브"
PROFILE_NAME = "프드프 라이브"
FILE_STEM = "pudufu_live"  # OBS 내부 파일/폴더 이름 (ASCII)

YOUTUBE_RTMP_SERVER = "rtmps://a.rtmps.youtube.com:443/live2"

VIDEO = {"base": (1920, 1080), "output": (1920, 1080), "fps": 30, "vbitrate": 6000, "abitrate": 160}

WS_PORT = 4455
WS_PASSWORD = "pudufu-live-setup"

CAMERA_SOURCE = "웹캠"
SCREEN_SOURCE = "화면 캡쳐"

IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))

# 플랫폼별 OBS 소스 타입
TYPES = {
    "camera": {"mac": "macos-avcapture", "win": "dshow_input"},
    "screen": {"mac": "screen_capture", "win": "monitor_capture"},
    "mic": {"mac": "coreaudio_input_capture", "win": "wasapi_input_capture"},
    "desktop": {"mac": "coreaudio_output_capture", "win": "wasapi_output_capture"},
}
PLATFORM = "win" if IS_WIN else "mac"


def all_types(kind):
    return set(TYPES[kind].values())


# ──────────────────────────── 경로 ────────────────────────────
def obs_config_dir() -> Path:
    if IS_WIN:
        return Path(os.environ["APPDATA"]) / "obs-studio"
    return Path.home() / "Library" / "Application Support" / "obs-studio"


def find_obs_exe():
    if IS_WIN:
        for root in (os.environ.get("ProgramFiles", r"C:\Program Files"),
                     os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")):
            p = Path(root) / "obs-studio" / "bin" / "64bit" / "obs64.exe"
            if p.exists():
                return p
        return None
    p = Path("/Applications/OBS.app/Contents/MacOS/OBS")
    return p if p.exists() else None


def obs_running() -> bool:
    if IS_WIN:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq obs64.exe"], capture_output=True, text=True).stdout
        return "obs64.exe" in out
    return subprocess.run(["pgrep", "-x", "OBS"], capture_output=True).returncode == 0


# ──────────────────────────── OBS 설치 ────────────────────────────
def ssl_context():
    """강사 PC의 Windows 인증서 저장소가 오래되면 GitHub 접속이 'unable to get local issuer certificate'로
    실패한다. 프로그램에 같이 넣은 certifi 인증서 묶음을 쓴다."""
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def install_obs(log):
    if IS_MAC:
        raise RuntimeError("Mac에는 OBS가 없습니다. https://obsproject.com 에서 설치한 뒤 다시 실행해 주세요.")
    log("OBS가 없어서 설치 파일을 내려받습니다...")
    ctx = ssl_context()
    api = "https://api.github.com/repos/obsproject/obs-studio/releases/latest"
    with urllib.request.urlopen(api, timeout=30, context=ctx) as r:
        assets = json.load(r)["assets"]
    cands = [a for a in assets if re.search(r"Windows.*Installer\.exe$", a["name"])]
    cands.sort(key=lambda a: ("x64" not in a["name"], a["name"]))
    if not cands:
        raise RuntimeError("OBS 설치 파일을 찾지 못했습니다. https://obsproject.com 에서 직접 설치해 주세요.")
    url = cands[0]["browser_download_url"]
    dst = Path(tempfile.gettempdir()) / cands[0]["name"]
    log(f"내려받는 중: {cands[0]['name']}")
    with urllib.request.urlopen(url, timeout=60, context=ctx) as r, open(dst, "wb") as f:
        shutil.copyfileobj(r, f)
    log("설치 중입니다. 관리자 권한 창이 뜨면 '예'를 눌러 주세요...")
    # 일반 실행(CreateProcess)으로는 UAC 창이 뜨지 않고 "요청한 작업에 승격이 필요합니다"로 바로 실패한다.
    # 설치 파일만 '관리자 권한으로 실행'(runas)으로 띄우고 끝날 때까지 기다린다.
    ps = f"Start-Process -FilePath '{dst}' -ArgumentList '/S' -Verb RunAs -Wait"
    r = subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                       capture_output=True, text=True, creationflags=0x08000000)  # CREATE_NO_WINDOW
    if r.returncode != 0:
        raise RuntimeError("OBS 설치가 취소됐거나 실패했습니다. 관리자 권한 창에서 '예'를 누른 뒤 다시 실행해 주세요.")
    exe = find_obs_exe()
    if not exe:
        raise RuntimeError("설치가 끝났지만 OBS 실행 파일을 찾지 못했습니다.")
    log("OBS 설치 완료")
    return exe


# ──────────────────────────── 장면 컬렉션 변환 ────────────────────────────
def build_collection(template: dict, asset_dir: Path) -> dict:
    data = copy.deepcopy(template)
    data["name"] = COLLECTION_NAME
    data["saved_projectors"] = []
    sources = data["sources"]
    scenes = [s for s in sources if s["id"] == "scene"]
    current_items = {i["name"] for sc in scenes if sc["name"] == data.get("current_scene")
                     for i in sc["settings"].get("items", [])}

    rename = {}      # 옛 이름 -> 새 이름
    uuid_map = {}    # 옛 uuid -> 새 uuid
    drop = set()

    def merge(kind, new_name):
        group = [s for s in sources if s["id"] in all_types(kind)]
        if not group:
            return
        keep = next((s for s in group if s["name"] in current_items), group[0])
        for s in group:
            rename[s["name"]] = new_name
            uuid_map[s["uuid"]] = keep["uuid"]
            if s is not keep:
                drop.add(s["uuid"])
        keep["name"] = new_name
        keep["id"] = keep["versioned_id"] = TYPES[kind][PLATFORM]
        keep["settings"] = {"use_preset": True, "preset": "AVCaptureSessionPresetHigh"} if (kind == "camera" and IS_MAC) else {}

    merge("camera", CAMERA_SOURCE)
    merge("screen", SCREEN_SOURCE)
    data["sources"] = [s for s in sources if s["uuid"] not in drop]

    for sc in scenes:
        for item in sc["settings"].get("items", []):
            if item["name"] in rename:
                item["name"] = rename[item["name"]]
                item["source_uuid"] = uuid_map.get(item.get("source_uuid"), item.get("source_uuid"))

    for key, kind in (("AuxAudioDevice1", "mic"), ("DesktopAudioDevice1", "desktop")):
        dev = data.get(key)
        if dev:
            dev["id"] = dev["versioned_id"] = TYPES[kind][PLATFORM]
            dev["settings"] = {"device_id": "default"}
            dev["volume"] = 1.0
            dev["muted"] = False

    for s in data["sources"]:
        st = s.get("settings", {})
        if s["id"] == "image_source" and st.get("file"):
            st["file"] = str(asset_dir / Path(st["file"]).name)
        if s["id"] == "slideshow":
            for f in st.get("files", []):
                folder = Path(f["value"].rstrip("/\\")).name
                f["value"] = str(asset_dir / folder)
    return data


# ──────────────────────────── 파일 쓰기 ────────────────────────────
def ini_merge(path: Path, values: dict):
    cp = configparser.ConfigParser(interpolation=None)
    cp.optionxform = str
    if path.exists():
        cp.read(path, encoding="utf-8-sig")
    for section, kv in values.items():
        if not cp.has_section(section):
            cp.add_section(section)
        for k, v in kv.items():
            cp.set(section, k, str(v))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        cp.write(fp, space_around_delimiters=False)


def write_profile(cfg: Path):
    pdir = cfg / "basic" / "profiles" / FILE_STEM
    pdir.mkdir(parents=True, exist_ok=True)
    bw, bh = VIDEO["base"]
    ow, oh = VIDEO["output"]
    ini_merge(pdir / "basic.ini", {
        "General": {"Name": PROFILE_NAME},
        "Video": {"BaseCX": bw, "BaseCY": bh, "OutputCX": ow, "OutputCY": oh, "FPSType": 0, "FPSCommon": VIDEO["fps"]},
        "Output": {"Mode": "Simple"},
        "SimpleOutput": {"VBitrate": VIDEO["vbitrate"], "ABitrate": VIDEO["abitrate"], "StreamEncoder": "x264",
                         "Preset": "veryfast", "UseAdvanced": "false", "RecQuality": "Stream", "RecFormat2": "mkv"},
        "Stream1": {"IgnoreRecommended": "false"},
    })
    service = {"type": "rtmp_common", "settings": {"service": "YouTube - RTMPS", "protocol": "RTMPS",
                                                    "server": YOUTUBE_RTMP_SERVER, "key": ""}}
    (pdir / "service.json").write_text(json.dumps(service, ensure_ascii=False, indent=2), encoding="utf-8")


def write_globals(cfg: Path):
    values = {
        "General": {"FirstRun": "true"},
        "Basic": {"Profile": PROFILE_NAME, "ProfileDir": FILE_STEM,
                  "SceneCollection": COLLECTION_NAME, "SceneCollectionFile": FILE_STEM},
    }
    for name in ("global.ini", "user.ini"):
        ini_merge(cfg / name, values)


def write_websocket_config(cfg: Path):
    p = cfg / "plugin_config" / "obs-websocket" / "config.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"alerts_enabled": False, "auth_required": True, "first_load": False,
                             "server_enabled": True, "server_password": WS_PASSWORD, "server_port": WS_PORT}, indent=2),
                 encoding="utf-8")


# ──────────────────────────── 장치 자동 연결 ────────────────────────────
def mac_main_display_uuid() -> str:
    """macOS 주 모니터의 UUID. screen_capture 소스는 이 값이 비어 있으면 아무것도 잡지 않는다."""
    import ctypes
    cg = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
    cf = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    cs = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/ColorSync.framework/ColorSync")
    cg.CGMainDisplayID.restype = ctypes.c_uint32
    make_uuid = cs.CGDisplayCreateUUIDFromDisplayID  # 최신 macOS는 ColorSync가 이 심볼을 가진다
    make_uuid.restype = ctypes.c_void_p
    make_uuid.argtypes = [ctypes.c_uint32]
    cf.CFUUIDCreateString.restype = ctypes.c_void_p
    cf.CFUUIDCreateString.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    cf.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_uint32]
    ref = make_uuid(cg.CGMainDisplayID())
    cfstr = cf.CFUUIDCreateString(None, ref)
    buf = ctypes.create_string_buffer(64)
    cf.CFStringGetCString(cfstr, buf, 64, 0x08000100)  # kCFStringEncodingUTF8
    return buf.value.decode()


def connect_ws(log, timeout=90):
    import logging
    import obsws_python as obs
    for name in ("obsws_python", "websocket"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    deadline = time.time() + timeout
    last = None
    cl = None
    while time.time() < deadline:
        try:
            cl = cl or obs.ReqClient(host="localhost", port=WS_PORT, password=WS_PASSWORD, timeout=5)
            cl.get_scene_list()  # websocket은 OBS 본체보다 먼저 열린다(코드 207). 실제 응답이 올 때까지 기다린다.
            return cl
        except Exception as e:  # OBS가 아직 뜨는 중
            last = e
            time.sleep(2)
    raise RuntimeError(f"OBS에 연결하지 못했습니다: {last}")


def pick_device(cl, source, prop, log, skip=("OBS",)):
    items = cl.get_input_properties_list_property_items(source, prop).property_items
    items = [i for i in items if i.get("itemEnabled", True) and i.get("itemValue")
             and not any(s in str(i.get("itemName", "")) for s in skip)]
    if not items:
        return None
    return items[0]


def attach_devices(cl, log):
    cam_prop = "video_device_id" if IS_WIN else "device"
    cam = pick_device(cl, CAMERA_SOURCE, cam_prop, log)
    if cam:
        settings = ({"video_device_id": cam["itemValue"], "last_video_device_id": cam["itemValue"], "active": True}
                    if IS_WIN else {"device": cam["itemValue"], "device_name": cam["itemName"]})
        cl.set_input_settings(CAMERA_SOURCE, settings, True)
        log(f"웹캠 연결: {cam['itemName']}")
    else:
        log("⚠ 웹캠을 찾지 못했습니다. OBS에서 '웹캠' 소스를 더블클릭해 직접 골라 주세요.")

    if IS_WIN:
        # macOS는 이 조회에서 OBS가 죽으므로 실행 전에 JSON에 직접 넣는다(run_setup 참고).
        try:
            scr = pick_device(cl, SCREEN_SOURCE, "monitor_id", log, skip=())
            if scr:
                cl.set_input_settings(SCREEN_SOURCE, {"monitor_id": scr["itemValue"]}, True)
                log(f"화면 캡쳐 연결: {scr['itemName']}")
            else:
                log("⚠ 모니터를 찾지 못했습니다. OBS에서 '화면 캡쳐' 소스를 더블클릭해 골라 주세요.")
        except Exception as e:
            log(f"⚠ 모니터 자동 연결 실패({e}). 기본 모니터로 동작합니다.")


# ──────────────────────────── 전체 흐름 ────────────────────────────
STEPS = ["OBS 설치 확인", "배너·장면 설치", "송출 설정", "OBS 실행", "웹캠·모니터 연결"]


def run_setup(log, step=lambda i: None):
    """step(i): i번째(1부터) 단계 시작을 알린다. GUI가 진행 표시에 쓴다."""
    if obs_running():
        raise RuntimeError("OBS가 이미 켜져 있습니다. OBS를 완전히 종료한 뒤 다시 실행해 주세요.")

    step(1)
    exe = find_obs_exe() or install_obs(log)
    cfg = obs_config_dir()

    step(2)
    asset_dir = cfg / FILE_STEM / "assets"
    # 프로그램 전용 폴더. 비우고 새로 복사해야 이름이 바뀐 옛 배너 폴더가 남지 않는다.
    shutil.rmtree(asset_dir, ignore_errors=True)
    shutil.copytree(BASE / "assets", asset_dir)
    log(f"이미지 설치: {asset_dir}")

    template = json.loads((BASE / "template" / "scenes.json").read_text(encoding="utf-8"))
    collection = build_collection(template, asset_dir)
    if IS_MAC:
        uuid = mac_main_display_uuid()
        for src in collection["sources"]:
            if src["name"] == SCREEN_SOURCE:
                src["settings"] = {"display_uuid": uuid, "type": 0}
        log(f"화면 캡쳐: 주 모니터 {uuid[:8]}…")
    scenes_dir = cfg / "basic" / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)
    (scenes_dir / f"{FILE_STEM}.json").write_text(json.dumps(collection, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"장면 설치: {len(collection['scene_order'])}개 장면")

    step(3)
    write_profile(cfg)
    write_globals(cfg)
    write_websocket_config(cfg)
    log("송출 프로필 설치 완료")

    # 직전 OBS가 비정상 종료됐으면 '안전 모드로 실행?' 창이 떠서 세팅이 멈춘다. 그 표식을 지운다.
    shutil.rmtree(cfg / ".sentinel", ignore_errors=True)
    step(4)
    log("OBS를 실행합니다...")
    args = [str(exe), "--collection", COLLECTION_NAME, "--profile", PROFILE_NAME]
    subprocess.Popen(args, cwd=str(exe.parent), start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    cl = connect_ws(log)
    step(5)
    attach_devices(cl, log)
    try:
        cl.set_current_program_scene(collection["current_scene"])
    except Exception:
        pass
    log("✅ 세팅 완료. OBS 설정 → 방송에서 '계정 연결'로 유튜브에 로그인한 뒤 '방송 시작'을 누르면 됩니다.")


# ──────────────────────────── GUI ────────────────────────────
def gui():
    import threading
    import tkinter as tk
    from tkinter import scrolledtext, ttk

    fam = "Malgun Gothic" if IS_WIN else "Helvetica"
    GREY, BLUE, GREEN, ORANGE, RED = "#9a9a9a", "#2962ff", "#2e7d32", "#ef6c00", "#c62828"

    root = tk.Tk()
    root.title("프드프 라이브 세팅")
    root.resizable(False, False)
    style = ttk.Style()
    style.configure("Big.TButton", font=(fam, 13, "bold"), padding=(0, 10))
    frm = ttk.Frame(root, padding=24)
    frm.grid(sticky="nsew")
    frm.columnconfigure(0, weight=1)

    ttk.Label(frm, text="프드프 라이브 OBS 세팅", font=(fam, 18, "bold")).grid(row=0, column=0, sticky="w")
    ttk.Label(frm, text="아래 버튼 하나로 강의 방송 준비를 끝냅니다. 보통 1~2분 걸려요.",
              foreground="#666").grid(row=1, column=0, sticky="w", pady=(2, 16))

    # 진행 단계
    box = ttk.Frame(frm)
    box.grid(row=2, column=0, sticky="w")
    icons, names = [], []
    for i, name in enumerate(STEPS):
        ic = ttk.Label(box, text="○", width=3, foreground=GREY, font=(fam, 13))
        ic.grid(row=i, column=0, sticky="w", pady=2)
        nm = ttk.Label(box, text=f"{i + 1}. {name}", foreground=GREY, font=(fam, 12))
        nm.grid(row=i, column=1, sticky="w", pady=2)
        icons.append(ic)
        names.append(nm)

    def mark(i, icon, color):
        icons[i].configure(text=icon, foreground=color)
        names[i].configure(foreground=color if color != GREY else "#333")

    btn = ttk.Button(frm, text="세팅 시작", style="Big.TButton")
    btn.grid(row=3, column=0, sticky="ew", pady=(20, 10))

    status = ttk.Label(frm, text="", wraplength=440, font=(fam, 11))
    status.grid(row=4, column=0, sticky="w")

    # 완료 후 안내
    nxt = ttk.LabelFrame(frm, text=" 다음 할 일 ", padding=12)
    ttk.Label(nxt, text="1. OBS 메뉴 [설정] → [방송] → '계정 연결'을 눌러 유튜브에 로그인하세요.",
              wraplength=420, font=(fam, 11)).grid(row=0, column=0, sticky="w", pady=2)
    ttk.Label(nxt, text="2. OBS 오른쪽 아래 '방송 시작'을 누르면 송출이 시작됩니다.",
              wraplength=420, font=(fam, 11)).grid(row=1, column=0, sticky="w", pady=2)

    # 자세한 기록 (접힘)
    detail = ttk.Button(frm, text="자세한 기록 보기 ▾")
    detail.grid(row=6, column=0, sticky="w", pady=(12, 0))
    logbox = scrolledtext.ScrolledText(frm, width=58, height=8, state="disabled",
                                       font=("Consolas" if IS_WIN else "Menlo", 10))

    def toggle():
        if logbox.winfo_ismapped():
            logbox.grid_remove()
            detail.configure(text="자세한 기록 보기 ▾")
        else:
            logbox.grid(row=7, column=0, sticky="ew", pady=(6, 0))
            detail.configure(text="자세한 기록 닫기 ▴")
    detail.configure(command=toggle)

    state = {"cur": -1, "warn": ""}

    def ui(fn):
        root.after(0, fn)

    def log(msg):
        def _():
            logbox.configure(state="normal")
            logbox.insert("end", msg + "\n")
            logbox.see("end")
            logbox.configure(state="disabled")
            if msg.startswith("⚠") and state["cur"] >= 0:
                mark(state["cur"], "⚠", ORANGE)
                state["warn"] = msg
                status.configure(text=msg, foreground=ORANGE)
        ui(_)

    def step(i):
        def _():
            if state["cur"] >= 0 and icons[state["cur"]].cget("text") == "▶":
                mark(state["cur"], "✔", GREEN)
            state["cur"] = i - 1
            mark(i - 1, "▶", BLUE)
            status.configure(text=f"{STEPS[i - 1]} 중…", foreground=BLUE)
        ui(_)

    def start():
        btn.configure(state="disabled")
        nxt.grid_remove()
        for i in range(len(STEPS)):
            mark(i, "○", GREY)
        state["cur"], state["warn"] = -1, ""

        def work():
            try:
                run_setup(log, step)

                def done():
                    if icons[state["cur"]].cget("text") == "▶":
                        mark(state["cur"], "✔", GREEN)
                    if state["warn"]:
                        status.configure(text="세팅이 끝났습니다. " + state["warn"], foreground=ORANGE)
                    else:
                        status.configure(text="세팅이 끝났습니다. OBS 창이 열려 있어요.", foreground=GREEN)
                    nxt.grid(row=5, column=0, sticky="ew", pady=(12, 0))
                ui(done)
            except Exception as e:
                def fail():
                    if state["cur"] >= 0:
                        mark(state["cur"], "✖", RED)
                    status.configure(text=f"문제가 생겼습니다: {e}", foreground=RED)
                    if not logbox.winfo_ismapped():
                        toggle()
                ui(fail)
                log(f"❌ {e}")
            finally:
                ui(lambda: btn.configure(state="normal"))
        threading.Thread(target=work, daemon=True).start()

    btn.configure(command=start)
    root.mainloop()


def main():
    ap = argparse.ArgumentParser(description="프드프 라이브 OBS 자동 세팅")
    ap.add_argument("--no-gui", action="store_true", help="창 없이 바로 실행")
    a = ap.parse_args()
    if a.no_gui:
        run_setup(print)
    else:
        gui()


if __name__ == "__main__":
    main()
