import base64
import hashlib
import time

AK = "e9dd5b4322f9f7d83d009de9bfa100c3"
SK = "2e3da06ae26ba9f76a5d8d355746f2fe"


def gen_signature(method: str) -> tuple[int, str]:
    ts = int(time.time() * 1000)
    params = f"method={method.upper()}&ak={AK}&sk={SK}&time={ts}"
    b64 = base64.b64encode(params.encode()).decode()
    sig = hashlib.md5(b64.encode()).hexdigest()
    return ts, sig
