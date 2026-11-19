# -*- coding: utf-8 -*-
"""瓜子 (guazi_new) - Yingxia / CatVod Python Spider.

Ported from the user-provided, obfuscated XPTV gzys.js.

Implements the original API flow:
  * device sign-up/sign-in and token refresh
  * dynamic API host list + fallback hosts
  * AES-CBC request/response encryption and RSA key wrapping
  * home/category list, search, resource tracks and play URL resolution

No account password, SMS login or user credential is required by this source.
The source generates an anonymous device identity in the same way as the JS.
"""

import base64
import hashlib
import json
import os
import re
import secrets
import threading
import time
from urllib.parse import quote

import requests

try:
    from base.spider import Spider as BaseSpider
except Exception:  # local tests outside Yingxia
    class BaseSpider(object):
        pass


# ---------------------------------------------------------------------------
# Original JS constants
# ---------------------------------------------------------------------------
API_UA = "okhttp/3.12.0"
MEDIA_UA = "Lavf/57.83.100"
MEDIA_REFERER = "http://WJiZxLXA2.com/"
FALLBACK_HOSTS = [
    "https://api.anctjd.com",
    "https://apinew.uozvr.com",
    "https://api.w32z7vtd.com",
    "https://api.6a7nnf7.com",
    "https://api.umygrx3.com",
    "https://api.rmedphk.com",
]
CONTROL_URLS = ["https://api.rqqakqyn.com"]
AES_KEY = "OITxa5OqAYjhswxx"
AES_IV = "rCMNwZASNBKZ8mXV"
DEVICE_OLD_KEY = "aLFBMWpxBrIDAD1Si/KVvm41"
CACHE_KEY = "guazi_new_auth_v3"
PHONE_MODEL = "xiaomi-25031"
APP_ID = "1"
PHONE_TYPE = "1"

RSA_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDUM5+/y8sPsWkd1/RQS64X259E
UwxFXFE5HlA65MqrxnPs0JqoSRojSDy5QhwvROlaD6TwRQHKMY2OAZ6SnQeUJsCh
TEFIR9qUkwrs3/MVUMxjsv6JS6Oe/juclyJGTgVmDhB55EafXsD0SQYVj/QXXsxR
6ewR5E2kL52yAAD4yQIDAQAB
-----END PUBLIC KEY-----"""

RSA_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGAe6hKrWLi1zQmjTT1
ozbE4QdFeJGNxubxld6GrFGximxfMsMB6BpJhpcTouAqywAFppiKetUBBbXwYsYU
1wNr648XVmPmCMCy4rY8vdliFnbMUj086DU6Z+/oXBdWU3/b1G0DN3E9wULRSwcK
ZT3wj/cCI1vsCm3gj2R5SqkA9Y0CAwEAAQKBgAJH+4CxV0/zBVcLiBCHvSANm0l7
HetybTh/j2p0Y1sTXro4ALwAaCTUeqdBjWiLSo9lNwDHFyq8zX90+gNxa7c5EqcW
V9FmlVXr8VhfBzcZo1nXeNdXFT7tQ2yah/odtdcx+vRMSGJd1t/5k5bDd9wAvYdI
DblMAg+wiKKZ5KcdAkEA1cCakEN4NexkF5tHPRrR6XOY/XHfkqXxEhMqmNbB9U34
saTJnLWIHC8IXys6Qmzz30TtzCjuOqKRRy+FMM4TdwJBAJQZFPjsGC+RqcG5UvVM
iMPhnwe/bXEehShK86yJK/g/UiKrO87h3aEu5gcJqBygTq3BBBoH2md3pr/W+hUM
WBsCQQChfhTIrdDinKi6lRxrdBnn0Ohjg2cwuqK5zzU9p/N+S9x7Ck8wUI53DKm8
jUJE8WAG7WLj/oCOWEh+ic6NIwTdAkEAj0X8nhx6AXsgCYRql1klbqtVmL8+95KZ
K7PnLWG/IfjQUy3pPGoSaZ7fdquG8bq8oyf5+dzjE/oTXcByS+6XRQJAP/5ciy1b
L3NhUhsaOVy55MHXnPjdcTX0FaLi+ybXZIfIQ2P4rb19mVq1feMbCXhz+L1rG8oa
t5lYKfpe8k83ZA==
-----END PRIVATE KEY-----"""

# Shared in-process cache, matching the JS $cache lifetime as closely as
# possible in the Spider runtime.
_AUTH_CACHE = {}
_VIDEO_CACHE = {}
_CACHE_LOCK = threading.RLock()


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _text(value, default=""):
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value).strip()


def _safe_int(value, default=1):
    try:
        return max(1, int(value))
    except Exception:
        return default


def _dict_arg(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            result = json.loads(value)
            return result if isinstance(result, dict) else {}
        except Exception:
            return {}
    return {}


def _encode_payload(value):
    raw = json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_payload(value):
    text = _text(value)
    if text.startswith("gzplay:"):
        text = text[7:]
    text += "=" * ((4 - len(text) % 4) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(text.encode("ascii")).decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("播放参数无法解码") from exc


def _clean_label(value, fallback="线路"):
    text = _text(value, fallback)
    text = re.sub(r"[\r\n$#|]+", " ", text).strip()
    return text or fallback


def _urlencode_component(value):
    # JavaScript encodeURIComponent-compatible safe characters.
    return quote(_text(value), safe="-_.!~*'()")


def _form_body(values):
    return "&".join(
        _urlencode_component(key) + "=" + _urlencode_component(value)
        for key, value in values.items()
    )


# ---------------------------------------------------------------------------
# Pure-Python AES-128-CBC + PKCS7 implementation (no CryptoJS dependency)
# ---------------------------------------------------------------------------
_SBOX = [
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
]
_INV_SBOX = [0] * 256
for _i, _v in enumerate(_SBOX):
    _INV_SBOX[_v] = _i
_RCON = [0x00,0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36]


def _xtime(value):
    return ((value << 1) ^ (0x11b if value & 0x80 else 0)) & 0xff


def _gmul(a, b):
    out = 0
    while b:
        if b & 1:
            out ^= a
        a = _xtime(a)
        b >>= 1
    return out


def _aes_round_keys(key):
    if len(key) != 16:
        raise ValueError("瓜子 API AES key 必须为 16 字节")
    words = [list(key[i:i + 4]) for i in range(0, 16, 4)]
    for i in range(4, 44):
        temp = words[i - 1][:]
        if i % 4 == 0:
            temp = temp[1:] + temp[:1]
            temp = [_SBOX[x] for x in temp]
            temp[0] ^= _RCON[i // 4]
        words.append([words[i - 4][j] ^ temp[j] for j in range(4)])
    return [sum(words[i:i + 4], []) for i in range(0, 44, 4)]


def _add_round_key(state, round_key):
    for i in range(16):
        state[i] ^= round_key[i]


def _sub_bytes(state):
    for i in range(16):
        state[i] = _SBOX[state[i]]


def _inv_sub_bytes(state):
    for i in range(16):
        state[i] = _INV_SBOX[state[i]]


def _shift_rows(state):
    for row in range(1, 4):
        vals = [state[row + 4 * col] for col in range(4)]
        vals = vals[row:] + vals[:row]
        for col in range(4):
            state[row + 4 * col] = vals[col]


def _inv_shift_rows(state):
    for row in range(1, 4):
        vals = [state[row + 4 * col] for col in range(4)]
        vals = vals[-row:] + vals[:-row]
        for col in range(4):
            state[row + 4 * col] = vals[col]


def _mix_columns(state):
    for col in range(4):
        i = col * 4
        a0, a1, a2, a3 = state[i:i + 4]
        state[i] = _gmul(a0, 2) ^ _gmul(a1, 3) ^ a2 ^ a3
        state[i + 1] = a0 ^ _gmul(a1, 2) ^ _gmul(a2, 3) ^ a3
        state[i + 2] = a0 ^ a1 ^ _gmul(a2, 2) ^ _gmul(a3, 3)
        state[i + 3] = _gmul(a0, 3) ^ a1 ^ a2 ^ _gmul(a3, 2)


def _inv_mix_columns(state):
    for col in range(4):
        i = col * 4
        a0, a1, a2, a3 = state[i:i + 4]
        state[i] = _gmul(a0,14) ^ _gmul(a1,11) ^ _gmul(a2,13) ^ _gmul(a3,9)
        state[i + 1] = _gmul(a0,9) ^ _gmul(a1,14) ^ _gmul(a2,11) ^ _gmul(a3,13)
        state[i + 2] = _gmul(a0,13) ^ _gmul(a1,9) ^ _gmul(a2,14) ^ _gmul(a3,11)
        state[i + 3] = _gmul(a0,11) ^ _gmul(a1,13) ^ _gmul(a2,9) ^ _gmul(a3,14)


def _aes_encrypt_block(block, round_keys):
    state = list(block)
    _add_round_key(state, round_keys[0])
    for rnd in range(1, 10):
        _sub_bytes(state)
        _shift_rows(state)
        _mix_columns(state)
        _add_round_key(state, round_keys[rnd])
    _sub_bytes(state)
    _shift_rows(state)
    _add_round_key(state, round_keys[10])
    return bytes(state)


def _aes_decrypt_block(block, round_keys):
    state = list(block)
    _add_round_key(state, round_keys[10])
    for rnd in range(9, 0, -1):
        _inv_shift_rows(state)
        _inv_sub_bytes(state)
        _add_round_key(state, round_keys[rnd])
        _inv_mix_columns(state)
    _inv_shift_rows(state)
    _inv_sub_bytes(state)
    _add_round_key(state, round_keys[0])
    return bytes(state)


def _pkcs7_pad(data):
    n = 16 - (len(data) % 16)
    return data + bytes([n]) * n


def _pkcs7_unpad(data):
    if not data:
        raise ValueError("AES 解密结果为空")
    n = data[-1]
    if n < 1 or n > 16 or data[-n:] != bytes([n]) * n:
        raise ValueError("AES PKCS7 padding 不正确")
    return data[:-n]


def _aes_cbc_encrypt(data, key, iv):
    keys = _aes_round_keys(key)
    prev = iv
    out = bytearray()
    padded = _pkcs7_pad(data)
    for off in range(0, len(padded), 16):
        block = bytes(a ^ b for a, b in zip(padded[off:off + 16], prev))
        enc = _aes_encrypt_block(block, keys)
        out.extend(enc)
        prev = enc
    return bytes(out)


def _aes_cbc_decrypt(data, key, iv):
    if len(data) == 0 or len(data) % 16:
        raise ValueError("AES 密文长度不正确")
    keys = _aes_round_keys(key)
    prev = iv
    out = bytearray()
    for off in range(0, len(data), 16):
        block = data[off:off + 16]
        dec = _aes_decrypt_block(block, keys)
        out.extend(a ^ b for a, b in zip(dec, prev))
        prev = block
    return _pkcs7_unpad(bytes(out))


def _aes_encrypt_hex(text, key=AES_KEY, iv=AES_IV):
    encrypted = _aes_cbc_encrypt(text.encode("utf-8"), key.encode("utf-8"), iv.encode("utf-8"))
    return encrypted.hex().upper()


def _aes_decrypt_hex(cipher_hex, key=AES_KEY, iv=AES_IV):
    raw = bytes.fromhex(_text(cipher_hex))
    return _aes_cbc_decrypt(raw, key.encode("utf-8"), iv.encode("utf-8")).decode("utf-8")


def _aes_decrypt_base64(cipher_b64, key=AES_KEY, iv=AES_IV):
    # CryptoJS' default formatter treats a string ciphertext as Base64.
    raw = base64.b64decode(_text(cipher_b64))
    return _aes_cbc_decrypt(raw, key.encode("utf-8"), iv.encode("utf-8")).decode("utf-8")


# ---------------------------------------------------------------------------
# Minimal DER/RSA PKCS#1 v1.5 implementation (no JSEncrypt dependency)
# ---------------------------------------------------------------------------
def _der_length(data, pos):
    first = data[pos]
    pos += 1
    if first < 0x80:
        return first, pos
    count = first & 0x7f
    if count < 1 or count > 4:
        raise ValueError("DER length invalid")
    length = int.from_bytes(data[pos:pos + count], "big")
    return length, pos + count


def _der_tlv(data, pos):
    tag = data[pos]
    length, start = _der_length(data, pos + 1)
    end = start + length
    if end > len(data):
        raise ValueError("DER data truncated")
    return tag, data[start:end], end


def _pem_der(pem):
    lines = [x.strip() for x in pem.strip().splitlines() if not x.startswith("-----")]
    return base64.b64decode("".join(lines))


def _der_integers(sequence_der):
    tag, content, end = _der_tlv(sequence_der, 0)
    if tag != 0x30 or end != len(sequence_der):
        raise ValueError("RSA DER sequence invalid")
    values = []
    pos = 0
    while pos < len(content):
        tag, item, pos = _der_tlv(content, pos)
        if tag == 0x02:
            values.append(int.from_bytes(item, "big"))
    return values


def _rsa_public_numbers():
    der = _pem_der(RSA_PUBLIC_KEY)
    tag, outer, _ = _der_tlv(der, 0)
    if tag != 0x30:
        raise ValueError("RSA public key invalid")
    pos = 0
    _tag, _alg, pos = _der_tlv(outer, pos)  # algorithm identifier
    tag, bitstr, pos = _der_tlv(outer, pos)
    if tag != 0x03 or not bitstr or bitstr[0] != 0:
        raise ValueError("RSA public key bit string invalid")
    n, e = _der_integers(bitstr[1:])[:2]
    return n, e


def _rsa_private_numbers():
    der = _pem_der(RSA_PRIVATE_KEY)
    tag, outer, _ = _der_tlv(der, 0)
    if tag != 0x30:
        raise ValueError("RSA private key invalid")
    pos = 0
    _tag, _version, pos = _der_tlv(outer, pos)
    _tag, _algorithm, pos = _der_tlv(outer, pos)
    tag, octets, pos = _der_tlv(outer, pos)
    if tag != 0x04:
        raise ValueError("PKCS8 private key invalid")
    values = _der_integers(octets)
    # PKCS#1 sequence: version, n, e, d, p, q, dp, dq, qi
    return values[1], values[3]


def _rsa_encrypt_text(text):
    n, e = _rsa_public_numbers()
    k = (n.bit_length() + 7) // 8
    message = text.encode("utf-8")
    if len(message) > k - 11:
        raise ValueError("RSA 明文太长")
    pad = bytearray()
    while len(pad) < k - len(message) - 3:
        b = secrets.token_bytes(1)[0]
        if b:
            pad.append(b)
    encoded = b"\x00\x02" + bytes(pad) + b"\x00" + message
    encrypted = pow(int.from_bytes(encoded, "big"), e, n).to_bytes(k, "big")
    return base64.b64encode(encrypted).decode("ascii")


def _rsa_decrypt_text(cipher_b64):
    n, d = _rsa_private_numbers()
    cipher = base64.b64decode(_text(cipher_b64))
    k = (n.bit_length() + 7) // 8
    if len(cipher) != k:
        raise ValueError("RSA 密文长度不正确")
    decoded = pow(int.from_bytes(cipher, "big"), d, n).to_bytes(k, "big")
    if decoded[:2] != b"\x00\x02":
        raise ValueError("RSA PKCS1 padding 不正确")
    sep = decoded.find(b"\x00", 2)
    if sep < 10:
        raise ValueError("RSA PKCS1 separator invalid")
    return decoded[sep + 1:].decode("utf-8")


# ---------------------------------------------------------------------------
# Spider implementation
# ---------------------------------------------------------------------------
class Spider(BaseSpider):
    def getName(self):
        return "瓜子"

    def init(self, extend=""):
        self.session = requests.Session()
        self.timeout = (10, 25)
        self.hosts = list(FALLBACK_HOSTS)
        self.host_index = 0
        self._auth = _AUTH_CACHE
        self._video_cache = _VIDEO_CACHE
        self._auth_ready = False
        self._hosts_ready = False
        with _CACHE_LOCK:
            if not self._auth.get("deviceId") or not self._auth.get("deviceKey"):
                self._init_device()

    def destroy(self):
        try:
            self.session.close()
        except Exception:
            pass

    def _init_device(self):
        self._auth["deviceId"] = "".join(str(secrets.randbelow(10)) for _ in range(15))
        self._auth["deviceKey"] = "".join(secrets.choice("0123456789ABCDEF") for _ in range(40))

    def _build_headers(self, host=None):
        return {
            "User-Agent": API_UA,
            "code": "GZ0055",
            "deviceId": self._auth.get("deviceId", ""),
            "lang": "zh_cn",
            "Cache-Control": "no-cache",
            "Content-Type": "application/x-www-form-urlencoded",
            "Version": "2608011",
            "PackageName": "com.xf4a1daee2.g3520dce0d.f8a8ed889d20260813",
            "Ver": "3.0.5.2",
            "api-ver": "3.0.5.2",
            "Referer": (host or self.hosts[self.host_index]).rstrip("/"),
        }

    def _apply_auth(self, result):
        token = _text(result.get("token")) if isinstance(result, dict) else ""
        if not token:
            raise RuntimeError("认证响应没有 token")
        self._auth["token"] = token
        self._auth["tokenId"] = _text(result.get("app_user_id") or result.get("token_id"))
        self._auth["registered"] = True

    def _load_auth(self):
        if not self._auth.get("deviceId") or not self._auth.get("deviceKey"):
            self._init_device()

    def _save_auth(self):
        # Shared module-level memory cache; no user data or credentials are written to disk.
        return

    def _signup(self):
        result = self._api_request(
            "/App/Authentication/Device/signUp",
            {"new_key": self._auth["deviceKey"], "old_key": DEVICE_OLD_KEY, "phone_type": 1, "code": ""},
            is_auth=True,
        )
        self._apply_auth(result)
        self._auth["registered"] = True
        self._save_auth()

    def _signin(self):
        result = self._api_request(
            "/App/Authentication/Device/signIn",
            {"new_key": self._auth["deviceKey"], "old_key": DEVICE_OLD_KEY},
            is_auth=True,
        )
        self._apply_auth(result)
        self._auth["registered"] = True
        self._save_auth()

    def _refresh_token(self):
        result = self._api_request("/App/Authentication/Authenticator/refresh", {}, is_auth=True)
        self._apply_auth(result)
        self._save_auth()

    def _ensure_token(self, force=False):
        self._load_auth()
        if not force and self._auth_ready and self._auth.get("token"):
            return
        if not self._auth.get("token"):
            try:
                self._signup()
            except Exception:
                self._signin()
        else:
            try:
                self._refresh_token()
            except Exception:
                self._signin()
        self._auth_ready = True

    def _fetch_latest_hosts(self):
        control_headers = {"User-Agent": API_UA, "Content-Type": "application/x-www-form-urlencoded"}
        for control in CONTROL_URLS:
            try:
                response = self.session.post(
                    control.rstrip("/") + "/gz/initialize/getApiUrlList?parameter=key",
                    data="", headers=control_headers, timeout=self.timeout,
                )
                if response.status_code >= 400:
                    continue
                payload = response.json()
                if isinstance(payload, str):
                    payload = json.loads(payload)
                if not isinstance(payload, dict) or int(payload.get("code", 0)) != 200:
                    continue
                raw = _text(payload.get("data"))
                decoded = ""
                try:
                    decoded = base64.b64decode(raw).decode("utf-8")
                except Exception:
                    pass
                if not decoded:
                    try:
                        decoded = _aes_decrypt_base64(raw)
                    except Exception:
                        pass
                if not decoded:
                    continue
                obj = json.loads(decoded)
                hosts = obj if isinstance(obj, list) else None
                if hosts is None and isinstance(obj, dict):
                    for key in ("list", "urls", "data", "hosts"):
                        if isinstance(obj.get(key), list) and obj[key]:
                            hosts = obj[key]
                            break
                if hosts:
                    hosts = [_text(x).rstrip("/") for x in hosts]
                    hosts = [x for x in hosts if x.startswith(("http://", "https://"))]
                    if hosts:
                        self.hosts = hosts
                        self.host_index = 0
                        return
            except Exception:
                continue

    def _ensure_hosts(self):
        if self._hosts_ready:
            return
        self._fetch_latest_hosts()
        self._hosts_ready = True

    def _api_request(self, path, params=None, is_auth=False, auth_retried=False):
        params = dict(params or {})
        if not is_auth:
            self._ensure_token()
        self._ensure_hosts()
        # Match the JS exactly: token/token_id are copied into the encrypted
        # payload only when the caller explicitly supplied those keys.
        # The outer form body always carries the auth fields separately.
        if "token" in params:
            params["token"] = self._auth.get("token", "")
        if "token_id" in params:
            params["token_id"] = self._auth.get("tokenId", "")

        request_json = json.dumps(params, ensure_ascii=True, separators=(",", ":"))
        request_key = _aes_encrypt_hex(request_json)
        if not request_key:
            raise RuntimeError("请求参数加密失败")
        rsa_keys = _rsa_encrypt_text(json.dumps({"iv": AES_IV, "key": AES_KEY}, separators=(",", ":")))
        timestamp = str(int(time.time()))
        sign_source = (
            "token_id=" + _text(self._auth.get("tokenId"))
            + ",token=" + _text(self._auth.get("token"))
            + ",phone_type=1,request_key=" + request_key
            + ",app_id=1,time=" + timestamp
            + ",keys=" + rsa_keys
            + "*&zvdvdvddbfikkkumtmdwqppp?|4Y!s!2br"
        )
        signature = hashlib.md5(sign_source.encode("utf-8")).hexdigest().upper()
        body_values = {
            "token": self._auth.get("token", ""),
            "token_id": self._auth.get("tokenId", ""),
            "phone_type": "1",
            "time": timestamp,
            "phone_model": PHONE_MODEL,
            "keys": rsa_keys,
            "request_key": request_key,
            "signature": signature,
            "app_id": "1",
            "ad_version": "1",
        }
        body = _form_body(body_values)

        last_error = None
        for _ in range(max(1, len(self.hosts))):
            host = self.hosts[self.host_index]
            try:
                response = self.session.post(
                    host.rstrip("/") + path,
                    data=body,
                    headers=self._build_headers(host),
                    timeout=self.timeout,
                    allow_redirects=True,
                )
                if response.status_code >= 400:
                    last_error = RuntimeError("HTTP %s" % response.status_code)
                    self.host_index = (self.host_index + 1) % len(self.hosts)
                    continue
                try:
                    outer = response.json()
                except Exception:
                    outer = json.loads(response.text)
            except Exception as exc:
                last_error = exc
                self.host_index = (self.host_index + 1) % len(self.hosts)
                continue

            if not isinstance(outer, dict):
                last_error = RuntimeError("API 响应不是 JSON 对象")
                self.host_index = (self.host_index + 1) % len(self.hosts)
                continue

            code = outer.get("code")
            code_ok = True
            if code is not None:
                try:
                    code_ok = float(code) == 200
                except Exception:
                    code_ok = False
            if not code_ok:
                if not is_auth and not auth_retried:
                    self._auth_ready = False
                    try:
                        self._ensure_token(force=True)
                    except Exception:
                        pass
                    return self._api_request(path, params, is_auth=False, auth_retried=True)
                raise RuntimeError("API code %s: %s @ %s" % (code, outer.get("msg") or outer.get("message") or "", path))

            data = outer.get("data") or {}
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    data = {"_raw": data}
            if not isinstance(data, dict):
                if isinstance(data, list):
                    return {"list": data}
                data = {}
            if not data.get("response_key"):
                if data.get("list") is not None or data.get("vodInfo") is not None:
                    return data
                raise RuntimeError("响应缺少 response_key @ " + path)

            aes_key, aes_iv = AES_KEY, AES_IV
            if data.get("keys"):
                try:
                    key_info = json.loads(_rsa_decrypt_text(data["keys"]))
                    aes_key = _text(key_info.get("key"), aes_key)
                    aes_iv = _text(key_info.get("iv"), aes_iv)
                except Exception:
                    pass
            decrypted = _aes_decrypt_hex(data["response_key"], aes_key, aes_iv)
            result = json.loads(decrypted)
            if isinstance(result, dict):
                return result
            if isinstance(result, list):
                return {"list": result}
            raise RuntimeError("解密后的 API 数据格式不正确")

        raise RuntimeError("所有瓜子 API 主机均请求失败：%s (%s)" % (path, last_error or "unknown"))

    # ------------------------------------------------------------------
    # UI configuration and filters
    # ------------------------------------------------------------------
    def _filters(self):
        area = [
            ("全部", "0"), ("大陆", "大陆"), ("香港", "香港"), ("台湾", "台湾"),
            ("美国", "美国"), ("韩国", "韩国"), ("日本", "日本"), ("英国", "英国"),
            ("法国", "法国"), ("泰国", "泰国"), ("印度", "印度"), ("其他", "其他"),
        ]
        years = [("全部", "0")] + [(str(y), str(y)) for y in range(2026, 2006, -1)] + [("更早", "2004")]
        sorts = [("最新", "d_id"), ("最热", "d_hits"), ("综合", "d_score")]
        result = []
        for key, name, values in (("area", "地区", area), ("year", "年份", years), ("sort", "排序", sorts)):
            result.append({"key": key, "name": name, "value": [{"n": n, "v": v} for n, v in values]})
        return result

    def homeContent(self, filter):
        classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "64", "type_name": "短剧"},
            {"type_id": "74", "type_name": "漫剧"},
            {"type_id": "33", "type_name": "儿童"},
        ]
        filters = {str(x["type_id"]): self._filters() for x in classes} if filter else {}
        return _json({"class": classes, "filters": filters})

    def _map_card(self, item):
        item = item if isinstance(item, dict) else {}
        vod_id = _text(item.get("vod_id") or item.get("id"))
        name = _text(item.get("vod_name") or item.get("name"))
        if not vod_id or not name:
            return None
        pic = _text(item.get("vod_pic") or item.get("pic"))
        remarks = _text(item.get("new_continue") or item.get("vod_remarks"))
        mapped = {"vod_id": vod_id, "vod_name": name, "vod_remarks": remarks, "ext": {"id": vod_id}}
        if pic:
            mapped["vod_pic"] = pic
        self._video_cache[vod_id] = dict(item)
        return mapped

    def _get_cards(self, tid, page, filters=None):
        filters = _dict_arg(filters)
        is_hot = str(tid) == "hot"
        params = {
            "area": _text(filters.get("area") or "0"),
            "year": _text(filters.get("year") or "0"),
            "pageSize": "30",
            "sort": _text(filters.get("sort") or ("d_hits" if is_hot else "d_id")),
            "page": str(_safe_int(page)),
            "tid": "0" if is_hot else str(tid),
        }
        result = self._api_request("/App/IndexList/indexList", params)
        rows = result.get("list") if isinstance(result, dict) else []
        if not isinstance(rows, list):
            rows = []
        cards = []
        for row in rows:
            mapped = self._map_card(row)
            if mapped:
                cards.append(mapped)
        return cards, result

    def homeVideoContent(self):
        # 首页“推荐”跨电影、电视剧、动漫、综艺四类汇总，排除短剧、漫剧、儿童。
        # 每个分类分别请求 d_id（最新）排序，再按影片 ID 倒序合并，避免 tid=0 混入被排除的类别。
        try:
            allowed_tids = ("1", "2", "4", "3")  # 电影、电视剧、动漫、综艺
            merged = []
            seen = set()
            sequence = 0

            for tid in allowed_tids:
                _, raw = self._get_cards(tid, 1, {"sort": "d_id"})
                rows = raw.get("list", []) if isinstance(raw, dict) else []
                if not isinstance(rows, list):
                    continue

                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    card = self._map_card(row)
                    if not card:
                        continue
                    vod_id = _text(card.get("vod_id"))
                    if not vod_id or vod_id in seen:
                        continue
                    seen.add(vod_id)

                    # 优先使用接口排序字段 d_id；响应未携带时，依次回退到影片 ID。
                    sort_key = float("-inf")
                    for sort_value in (row.get("d_id"), row.get("id"), row.get("vod_id"), vod_id):
                        if sort_value in (None, ""):
                            continue
                        match = re.search(r"-?\d+(?:\.\d+)?", _text(sort_value))
                        if match:
                            try:
                                sort_key = float(match.group(0))
                                break
                            except Exception:
                                pass

                    merged.append((sort_key, sequence, card))
                    sequence += 1

            # 取四类各自最新前 30 条，合并后按 d_id 对应的数值 ID 倒序，首页最多显示 30 条。
            merged.sort(key=lambda item: (item[0], -item[1]), reverse=True)
            return _json({"list": [item[2] for item in merged[:30]]})
        except Exception as exc:
            return self._failure(exc)

    def categoryContent(self, tid, pg, filter, extend):
        try:
            ext = _dict_arg(extend)
            cards, raw = self._get_cards(tid, pg, ext)
            page = _safe_int(pg)
            total = raw.get("total") or raw.get("count") or len(cards)
            try:
                total = int(total)
            except Exception:
                total = len(cards)
            page_count = raw.get("pageCount") or raw.get("totalPage") or raw.get("pages")
            try:
                page_count = int(page_count)
            except Exception:
                page_count = page + (1 if len(cards) >= 30 else 0)
            return _json({"page": page, "pagecount": max(page, page_count), "limit": 30, "total": total, "list": cards})
        except Exception as exc:
            return self._failure(exc)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def searchContent(self, key, quick, pg="1"):
        try:
            keyword = _text(key).strip()
            if not keyword:
                return _json({"list": []})
            params = {"keywords": keyword, "order_val": "1", "page": str(_safe_int(pg))}
            result = self._api_request("/App/Index/findMoreVod", params)
            rows = result.get("list", []) if isinstance(result, dict) else []
            cards = []
            for row in rows if isinstance(rows, list) else []:
                mapped = self._map_card(row)
                if mapped:
                    cards.append(mapped)
            return _json({"page": _safe_int(pg), "pagecount": _safe_int(pg) + (1 if len(cards) >= 30 else 0), "limit": 30, "list": cards})
        except Exception as exc:
            return self._failure(exc)

    # ------------------------------------------------------------------
    # Detail and resources
    # ------------------------------------------------------------------
    def detailContent(self, ids):
        try:
            if isinstance(ids, (list, tuple)):
                vod_id = _text(ids[0]) if ids else ""
            elif isinstance(ids, dict):
                vod_id = _text(ids.get("vod_id") or ids.get("id"))
            else:
                vod_id = _text(ids)
            if not vod_id:
                raise RuntimeError("详情缺少影片 ID")

            cached = self._video_cache.get(vod_id, {})
            info = {
                "vod_id": vod_id,
                "vod_name": _text(cached.get("vod_name") or cached.get("name") or vod_id),
            }
            pic = _text(cached.get("vod_pic") or cached.get("pic"))
            remarks = _text(cached.get("new_continue") or cached.get("vod_remarks"))
            if pic:
                info["vod_pic"] = pic
            if remarks:
                info["vod_remarks"] = remarks

            # The supplied JS's getTracks() calls this endpoint; it does not
            # contain a separate synopsis/director/cast detail endpoint.
            result = self._api_request(
                "/App/Resource/Vurl/show",
                {"vurl_cloud_id": "2", "vod_d_id": vod_id},
            )
            routes = result.get("list", []) if isinstance(result, dict) else []
            if not isinstance(routes, list):
                routes = []

            route_entries = []
            seen_titles = set()
            for index, route in enumerate(routes):
                if not isinstance(route, dict):
                    continue
                title = _clean_label(route.get("title"), "线路%d" % (index + 1))
                play = route.get("play")
                if isinstance(play, str):
                    try:
                        play = json.loads(play)
                    except Exception:
                        continue
                if not isinstance(play, dict) or not play:
                    continue
                label = title
                suffix = 2
                while label in seen_titles:
                    label = "%s (%d)" % (title, suffix)
                    suffix += 1
                seen_titles.add(label)
                payload_id = "gzplay:" + _encode_payload({"play": play, "vod_id": vod_id})
                route_entries.append(label + "$" + payload_id)

            if route_entries:
                info["vod_play_from"] = "默认分组"
                info["vod_play_url"] = "#".join(route_entries)
            else:
                info["vod_play_from"] = ""
                info["vod_play_url"] = ""
                info["vod_remarks"] = info.get("vod_remarks", "")
            return _json({"list": [info]})
        except Exception as exc:
            return self._failure(exc)

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_play_params(value):
        params = {}
        for part in _text(value).split("&"):
            pos = part.find("=")
            if pos > 0:
                params[part[:pos]] = part[pos + 1:]
        return params

    def playerContent(self, flag, id, vipFlags):
        try:
            payload = _decode_payload(id)
            play = payload.get("play") if isinstance(payload, dict) else None
            if not isinstance(play, dict) or not play:
                raise RuntimeError("播放线路数据为空")
            priority = ["8k", "4k", "2160", "1440", "1080", "720", "480"]
            resolution = next((key for key in priority if play.get(key)), None)
            if resolution is None:
                resolution = next(iter(play.keys()), None)
            if not resolution:
                raise RuntimeError("播放线路没有可用清晰度")
            selected = play.get(resolution)
            if isinstance(selected, str):
                try:
                    selected = json.loads(selected)
                except Exception:
                    selected = {}
            if not isinstance(selected, dict):
                raise RuntimeError("播放清晰度参数格式不正确")
            params = self._parse_play_params(selected.get("param"))
            if not params:
                raise RuntimeError("播放参数缺少 param")
            params["resolution"] = resolution
            result = self._api_request("/App/Resource/VurlDetail/showOne", params)
            play_url = _text(result.get("url")) if isinstance(result, dict) else ""
            if not play_url:
                raise RuntimeError("播放详情接口没有返回视频地址")
            return _json({
                "parse": 0,
                "url": play_url,
                "header": {"User-Agent": MEDIA_UA, "Referer": MEDIA_REFERER},
            })
        except Exception as exc:
            return _json({"parse": 1, "url": "", "header": {}, "msg": _text(exc, "瓜子播放失败")})

    @staticmethod
    def _failure(message):
        return _json({"list": [], "msg": _text(message, "瓜子请求失败")})


TVBOX_SOURCE_CONFIG = {
    "sites": [{
        "key": "guazi_new",
        "name": "瓜子",
        "type": 3,
        "api": "./guazi.py",
        "searchable": 1,
        "quickSearch": 1,
        "filterable": 1,
        "changeable": 1,
        "timeout": 60,
        "ext": "",
    }]
}
TVBOX_SOURCE_CONFIG_JSON = _json(TVBOX_SOURCE_CONFIG)
