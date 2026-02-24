import base64
import json
from pydoc import plain
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetcher import _aes_encrypt, _build_envelope, _build_req_data



class TestAesEncrypt:
    

    def _decrypt(self, ciphertext_b64, salt_hex, iv_hex):
        from Crypto.Cipher import AES
        from Crypto.Protocol.KDF import PBKDF2
        from Crypto.Hash import HMAC, SHA1
        from Crypto.Util.Padding import unpad
        from fetcher import _PASSPHRASE

        salt   = bytes.fromhex(salt_hex)
        iv     = bytes.fromhex(iv_hex)
        key    = PBKDF2(_PASSPHRASE.encode(), salt, dkLen=16, count=1000,
                    prf=lambda p, s: HMAC.new(p, s, SHA1).digest())
        ct     = base64.b64decode(ciphertext_b64)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        plain  = unpad(cipher.decrypt(ct), 16)
        return plain.decode("utf-8")
    def test_encrypt_decrypt_roundtrip(self):
        plaintext = '{"test": "hello world"}'
        salt_hex  = "a" * 32
        iv_hex    = "b" * 32
        ct        = _aes_encrypt(plaintext, salt_hex, iv_hex)
        recovered = self._decrypt(ct, salt_hex, iv_hex)
        assert recovered == plaintext

    def test_different_ivs_produce_different_ciphertext(self):
        plaintext  = "same plaintext"
        salt_hex   = "a" * 32
        ct1 = _aes_encrypt(plaintext, salt_hex, "1" * 32)
        ct2 = _aes_encrypt(plaintext, salt_hex, "2" * 32)
        assert ct1 != ct2

    def test_output_is_valid_base64(self):
        ct = _aes_encrypt("test", "a" * 32, "b" * 32)
        # Should not raise
        decoded = base64.b64decode(ct)
        assert len(decoded) > 0

    def test_ciphertext_length_multiple_of_16(self):
        ct = _aes_encrypt("hello world", "a" * 32, "b" * 32)
        decoded = base64.b64decode(ct)
        assert len(decoded) % 16 == 0




class TestBuildEnvelope:

    def test_envelope_has_required_keys(self):
        envelope = _build_envelope({"test": 1})
        assert set(envelope.keys()) == {"jsonData", "iv", "salt", "key"}

    def test_key_field_is_fixed(self):
        envelope = _build_envelope({"test": 1})
        assert envelope["key"] == "ejdNcmw="

    def test_iv_is_32_char_hex(self):
        envelope = _build_envelope({"test": 1})
        assert len(envelope["iv"]) == 32
        int(envelope["iv"], 16)  # should not raise

    def test_salt_is_32_char_hex(self):
        envelope = _build_envelope({"test": 1})
        assert len(envelope["salt"]) == 32
        int(envelope["salt"], 16)  # should not raise

    def test_json_data_is_base64(self):
        envelope = _build_envelope({"test": 1})
        # Should not raise
        base64.b64decode(envelope["jsonData"])

    def test_each_call_produces_unique_iv(self):
        e1 = _build_envelope({"test": 1})
        e2 = _build_envelope({"test": 1})
        # Random IV means different ciphertext every call (99.999% certainty)
        assert e1["iv"] != e2["iv"]




class TestBuildReqData:

    def test_has_required_top_level_keys(self):
        data = _build_req_data(0, 50)
        assert "reqData" in data
        assert "_csrf" in data
        assert "idList" in data
        assert "id" in data

    def test_id_field_is_tenders_in_progress(self):
        data = _build_req_data(0, 50)
        assert data["id"] == "Tenders In Progress"

    def test_id_list_is_zero_string(self):
        data = _build_req_data(0, 50)
        assert data["idList"] == "0"

    def test_csrf_is_empty(self):
        data = _build_req_data(0, 50)
        assert data["_csrf"] == ""

    def test_req_data_is_list(self):
        data = _build_req_data(0, 50)
        assert isinstance(data["reqData"], list)

    def test_req_data_has_14_entries(self):
        data = _build_req_data(0, 50)
        assert len(data["reqData"]) == 14

    def test_display_start_correct(self):
        data = _build_req_data(100, 50)
        starts = [e["value"] for e in data["reqData"] if e["name"] == "iDisplayStart"]
        assert starts == [100]

    def test_display_length_correct(self):
        data = _build_req_data(0, 75)
        lengths = [e["value"] for e in data["reqData"] if e["name"] == "iDisplayLength"]
        assert lengths == [75]

    def test_all_req_data_entries_have_name_and_value(self):
        data = _build_req_data(0, 50)
        for entry in data["reqData"]:
            assert "name" in entry
            assert "value" in entry

    def test_s_echo_value_is_1(self):
        data = _build_req_data(0, 50)
        echos = [e["value"] for e in data["reqData"] if e["name"] == "sEcho"]
        assert echos == [1]

    def test_pagination_offset_applied_correctly(self):
        data = _build_req_data(50, 50)
        starts = [e["value"] for e in data["reqData"] if e["name"] == "iDisplayStart"]
        assert starts == [50]
