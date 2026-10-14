#!/usr/bin/env python3
"""프드프 라이브 OBS 자동 세팅.

실행하면 OBS 설치 확인 → 장면/프로필/이미지 설치 → OBS 실행 → 웹캠·모니터 자동 연결 순으로 진행한다.
강사는 송출처와 스트림 키만 입력하면 된다.
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
PUDUFU_RTMP_SERVER = ""  # 예: "rtmp://live.pudufu.com/app"  비워 두면 실행 시 입력창이 뜬다.

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
    subprocess.run([str(dst), "/S"], check=True)
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


def write_profile(cfg: Path, dest: str, server: str, key: str):
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
    if dest == "youtube":
        service = {"type": "rtmp_common", "settings": {"service": "YouTube - RTMPS", "protocol": "RTMPS",
                                                        "server": YOUTUBE_RTMP_SERVER, "key": key}}
    else:
        service = {"type": "rtmp_custom", "settings": {"server": server, "key": key, "use_auth": False, "bwtest": False}}
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
def run_setup(dest: str, key: str, server: str, log):
    if dest == "pudufu" and not server.strip():
        raise RuntimeError("pudufu 송출 서버 주소가 필요합니다.")
    if obs_running():
        raise RuntimeError("OBS가 이미 켜져 있습니다. OBS를 완전히 종료한 뒤 다시 실행해 주세요.")

    exe = find_obs_exe() or install_obs(log)
    cfg = obs_config_dir()

    asset_dir = cfg / FILE_STEM / "assets"
    shutil.copytree(BASE / "assets", asset_dir, dirs_exist_ok=True)
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

    write_profile(cfg, dest, server, key)
    write_globals(cfg)
    write_websocket_config(cfg)
    log("송출 프로필 설치 완료")

    # 직전 OBS가 비정상 종료됐으면 '안전 모드로 실행?' 창이 떠서 세팅이 멈춘다. 그 표식을 지운다.
    shutil.rmtree(cfg / ".sentinel", ignore_errors=True)
    log("OBS를 실행합니다...")
    args = [str(exe), "--collection", COLLECTION_NAME, "--profile", PROFILE_NAME]
    subprocess.Popen(args, cwd=str(exe.parent), start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    cl = connect_ws(log)
    attach_devices(cl, log)
    try:
        cl.set_current_program_scene(collection["current_scene"])
    except Exception:
        pass
    if key.strip():
        log("✅ 세팅 완료. OBS 창에서 '방송 시작'을 누르면 됩니다.")
    else:
        log("✅ 세팅 완료. 스트림 키는 OBS 설정 → 방송에서 입력한 뒤 '방송 시작'을 누르면 됩니다.")


# ──────────────────────────── GUI ────────────────────────────
def gui():
    import threading
    import tkinter as tk
    from tkinter import messagebox, scrolledtext, ttk

    root = tk.Tk()
    root.title("프드프 라이브 세팅")
    root.resizable(False, False)
    frm = ttk.Frame(root, padding=16)
    frm.grid()

    ttk.Label(frm, text="송출처").grid(row=0, column=0, sticky="w")
    dest = tk.StringVar(value="youtube")
    box = ttk.Frame(frm)
    box.grid(row=0, column=1, sticky="w")
    ttk.Radiobutton(box, text="YouTube", variable=dest, value="youtube").pack(side="left")
    ttk.Radiobutton(box, text="pudufu", variable=dest, value="pudufu").pack(side="left", padx=(12, 0))

    ttk.Label(frm, text="스트림 키").grid(row=1, column=0, sticky="w", pady=(8, 0))
    key = ttk.Entry(frm, width=44, show="•")
    key.grid(row=1, column=1, pady=(8, 0))

    server_label = ttk.Label(frm, text="pudufu 서버")
    server = ttk.Entry(frm, width=44)
    server.insert(0, PUDUFU_RTMP_SERVER)

    def on_dest(*_):
        if dest.get() == "pudufu" and not PUDUFU_RTMP_SERVER:
            server_label.grid(row=2, column=0, sticky="w", pady=(8, 0))
            server.grid(row=2, column=1, pady=(8, 0))
        else:
            server_label.grid_remove()
            server.grid_remove()
    dest.trace_add("write", on_dest)
    on_dest()

    logbox = scrolledtext.ScrolledText(frm, width=58, height=12, state="disabled", font=("Menlo" if IS_MAC else "Consolas", 10))
    logbox.grid(row=4, column=0, columnspan=2, pady=(12, 0))

    def log(msg):
        def _append():
            logbox.configure(state="normal")
            logbox.insert("end", msg + "\n")
            logbox.see("end")
            logbox.configure(state="disabled")
        root.after(0, _append)

    def start():
        btn.configure(state="disabled")

        def work():
            try:
                run_setup(dest.get(), key.get(), server.get(), log)
                root.after(0, lambda: messagebox.showinfo("완료", "세팅이 끝났습니다.\nOBS 창에서 '방송 시작'을 누르세요."))
            except Exception as e:
                log(f"❌ {e}")
                root.after(0, lambda: messagebox.showerror("오류", str(e)))
            finally:
                root.after(0, lambda: btn.configure(state="normal"))
        threading.Thread(target=work, daemon=True).start()

    btn = ttk.Button(frm, text="세팅 시작", command=start)
    btn.grid(row=3, column=0, columnspan=2, pady=(12, 0), sticky="ew")
    root.mainloop()


def main():
    ap = argparse.ArgumentParser(description="프드프 라이브 OBS 자동 세팅")
    ap.add_argument("--dest", choices=["youtube", "pudufu"], default="youtube")
    ap.add_argument("--key", help="스트림 키. 지정하면 창 없이 바로 실행 (빈 문자열이면 키 없이 세팅)")
    ap.add_argument("--server", default=PUDUFU_RTMP_SERVER, help="pudufu RTMP 서버 주소")
    a = ap.parse_args()
    if a.key is not None:
        run_setup(a.dest, a.key, a.server, print)
    else:
        gui()


if __name__ == "__main__":
    main()
