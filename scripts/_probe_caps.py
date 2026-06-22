"""Sonda de solo-lectura: lee las HID caps de MI_00 para conocer el framing exacto.

No escribe nada al dispositivo. Usa la API HID de Windows vía ctypes.
"""
import ctypes
from ctypes import wintypes

import hid

# Localiza la ruta de MI_00 (usage_page 0xff00).
path = None
for d in hid.enumerate(0x1189, 0x8842):
    if d.get("usage_page") == 0xFF00:
        path = d["path"]
        break
assert path, "no encuentro MI_00 (usage_page 0xff00)"
print("MI_00 path:", path.decode(errors="replace"))

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
OPEN_EXISTING = 3

k32 = ctypes.windll.kernel32
hiddll = ctypes.windll.hid

CreateFileW = k32.CreateFileW
CreateFileW.restype = wintypes.HANDLE
CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                        ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]

h = CreateFileW(path.decode(), GENERIC_READ | GENERIC_WRITE,
                FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None)
if h == wintypes.HANDLE(-1).value or not h:
    raise OSError("CreateFileW falló: %s" % ctypes.GetLastError())


class HIDP_CAPS(ctypes.Structure):
    _fields_ = [
        ("Usage", ctypes.c_ushort),
        ("UsagePage", ctypes.c_ushort),
        ("InputReportByteLength", ctypes.c_ushort),
        ("OutputReportByteLength", ctypes.c_ushort),
        ("FeatureReportByteLength", ctypes.c_ushort),
        ("Reserved", ctypes.c_ushort * 17),
        ("NumberLinkCollectionNodes", ctypes.c_ushort),
        ("NumberInputButtonCaps", ctypes.c_ushort),
        ("NumberInputValueCaps", ctypes.c_ushort),
        ("NumberInputDataIndices", ctypes.c_ushort),
        ("NumberOutputButtonCaps", ctypes.c_ushort),
        ("NumberOutputValueCaps", ctypes.c_ushort),
        ("NumberOutputDataIndices", ctypes.c_ushort),
        ("NumberFeatureButtonCaps", ctypes.c_ushort),
        ("NumberFeatureValueCaps", ctypes.c_ushort),
        ("NumberFeatureDataIndices", ctypes.c_ushort),
    ]


pp = ctypes.c_void_p()
if not hiddll.HidD_GetPreparsedData(h, ctypes.byref(pp)):
    raise OSError("HidD_GetPreparsedData falló")
caps = HIDP_CAPS()
HIDP_STATUS_SUCCESS = 0x00110000
rc = hiddll.HidP_GetCaps(pp, ctypes.byref(caps))
print("HidP_GetCaps rc=0x%08x (ok=0x%08x)" % (rc & 0xFFFFFFFF, HIDP_STATUS_SUCCESS))
print("UsagePage=0x%04x Usage=0x%02x" % (caps.UsagePage, caps.Usage))
print("InputReportByteLength  =", caps.InputReportByteLength)
print("OutputReportByteLength =", caps.OutputReportByteLength)
print("FeatureReportByteLength=", caps.FeatureReportByteLength)
print("NumberOutputValueCaps  =", caps.NumberOutputValueCaps)
print("NumberFeatureValueCaps =", caps.NumberFeatureValueCaps)

hiddll.HidD_FreePreparsedData(pp)
k32.CloseHandle(h)
