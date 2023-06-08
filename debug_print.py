
_enabled = False

def set_debug(enable: bool)->None:
    global _enabled
    _enabled = enable

def log(*args)->None:
    if not _enabled: return
    print(" ".join(str(arg) for arg in args))