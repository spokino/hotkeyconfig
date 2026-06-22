"""Sonda de framing: prueba formatos de escritura con datos a CERO (init, no programa).

Imprime bytes escritos y el error de hidapi para cada variante.
"""
import hid

path = None
for d in hid.enumerate(0x1189, 0x8842):
    if d.get("usage_page") == 0xFF00:
        path = d["path"]
        break
assert path

def try_write(label, data):
    dev = hid.device()
    dev.open_path(path)
    try:
        n = dev.write(bytes(data))
        print(f"{label}: len={len(data)} -> n={n} err={dev.error()!r}")
    except Exception as e:  # noqa: BLE001
        print(f"{label}: len={len(data)} -> EXC {e!r}")
    finally:
        dev.close()

# Todas con datos a cero (mensaje init de ch57x = 64 ceros), variando el framing.
try_write("a) [00] + 64 ceros (65)", [0x00] + [0x00] * 64)
try_write("b) 64 ceros (64)", [0x00] * 64)
try_write("c) 65 ceros (65)", [0x00] * 65)
try_write("d) [00]+[03]+63 ceros (65)", [0x00, 0x03] + [0x00] * 63)
try_write("e) [03]+64 ceros (65)", [0x03] + [0x00] * 64)
