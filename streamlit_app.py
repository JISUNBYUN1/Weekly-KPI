"""PP3G W37 browser-upload bootstrap. All payload files must stay beside this file."""
import base64
import json
import sys
import types
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
parts = sorted(ROOT.glob("__pp3g_w37r8_*.txt"))
if not parts:
    raise RuntimeError("W37 R8 구성 파일이 없습니다. __pp3g_w37r8_*.txt 파일을 모두 업로드해주세요.")
try:
    payload = json.loads(zlib.decompress(base64.b85decode("".join(p.read_text(encoding="ascii") for p in parts))).decode("utf-8"))
except Exception as error:
    raise RuntimeError("W37 구성 파일이 불완전합니다. 모든 조각 파일을 같은 폴더에 올려주세요.") from error

def install(name):
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / (name + ".py"))
    sys.modules[name] = module
    exec(compile(payload["modules"][name], module.__file__, "exec"), module.__dict__)
    return module

report_data = install("report_data")
report_data.EMBEDDED_SNAPSHOT = payload["snapshot"]
for module_name in ("executive_report", "partner_views", "dashboard_views", "compact_report"):
    install(module_name)
exec(compile(payload["modules"]["streamlit_app"], str(ROOT / "streamlit_app_w37.py"), "exec"),
     {"__name__": "__main__", "__file__": str(ROOT / "streamlit_app.py")})
