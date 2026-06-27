from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from licenciamento.machine import machine_id
from licenciamento.client import DEFAULT_SERVER_URL, normalize_config
from licenciamento.paths import CONFIG_FILE, STATE_FILE
from licenciamento.runtime import check_application_access
from licenciamento.store import clear_license_state, iso_utc, save_license_state, utcnow, validate_state


class LicensingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.previous = os.environ.get("GUIMMA_LICENSE_DIR")
        os.environ["GUIMMA_LICENSE_DIR"] = self.tempdir.name

    def tearDown(self) -> None:
        if self.previous is None:
            os.environ.pop("GUIMMA_LICENSE_DIR", None)
        else:
            os.environ["GUIMMA_LICENSE_DIR"] = self.previous
        self.tempdir.cleanup()

    def test_valid_active_license_is_accepted(self) -> None:
        save_license_state(
            {
                "status": "active",
                "machine_id": machine_id(),
                "valid_until": iso_utc(utcnow() + timedelta(days=30)),
            }
        )

        result = validate_state()

        self.assertTrue(result.ok)

    def test_expired_license_is_rejected(self) -> None:
        save_license_state(
            {
                "status": "active",
                "machine_id": machine_id(),
                "valid_until": iso_utc(utcnow() - timedelta(days=1)),
            }
        )

        result = validate_state()

        self.assertFalse(result.ok)
        self.assertIn("expirada", result.message.lower())

    def test_tampered_license_is_rejected(self) -> None:
        save_license_state(
            {
                "status": "expired",
                "machine_id": machine_id(),
                "valid_until": iso_utc(utcnow() - timedelta(days=1)),
            }
        )
        state_path = Path(self.tempdir.name) / STATE_FILE
        data = json.loads(state_path.read_text(encoding="utf-8"))
        data["status"] = "active"
        data["valid_until"] = iso_utc(utcnow() + timedelta(days=30))
        state_path.write_text(json.dumps(data), encoding="utf-8")

        result = validate_state()

        self.assertFalse(result.ok)
        self.assertIn("alterado", result.message.lower())

    def test_clear_license_state_removes_local_license(self) -> None:
        save_license_state(
            {
                "status": "active",
                "machine_id": machine_id(),
                "valid_until": iso_utc(utcnow() + timedelta(days=30)),
            }
        )

        removed = clear_license_state()
        result = validate_state()

        self.assertEqual(removed, 1)
        self.assertFalse(result.ok)
        self.assertIn("nenhuma", result.message.lower())

    def test_license_is_required_by_default(self) -> None:
        result = check_application_access(try_online=False)

        self.assertFalse(result.allowed)
        self.assertIn("licenca", result.title.lower())

    def test_config_always_enforces_license(self) -> None:
        config = normalize_config({"enabled": False, "server_url": DEFAULT_SERVER_URL})

        self.assertTrue(config["enabled"])

    def test_config_uses_ten_minute_poll_interval(self) -> None:
        config = normalize_config({"poll_interval_minutes": 1440})

        self.assertEqual(config["poll_interval_minutes"], 10)


if __name__ == "__main__":
    unittest.main()
