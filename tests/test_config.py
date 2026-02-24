import os
import pytest
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import build_config
import argparse


def make_args(**kwargs):
    defaults = {
        "limit":       None,
        "rate_limit":  1.5,
        "concurrency": 1,
        "retries":     3,
        "timeout":     60,
        "output":      "sample-output.json",
        "metadata_db": "runs_metadata.db",
        "user_agent":  "TestAgent/1.0",
        "page_size":   50,
        "dry_run":     False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


class TestBuildConfig:

    def test_all_keys_present(self):
        config = build_config(make_args())
        expected = ["limit", "rate_limit", "concurrency", "retries", "timeout",
                    "output", "metadata_db", "user_agent", "page_size", "dry_run"]
        for key in expected:
            assert key in config

    def test_limit_none_by_default(self):
        config = build_config(make_args())
        assert config["limit"] is None

    def test_limit_set(self):
        config = build_config(make_args(limit=50))
        assert config["limit"] == 50

    def test_dry_run_false_by_default(self):
        config = build_config(make_args())
        assert config["dry_run"] is False

    def test_dry_run_true(self):
        config = build_config(make_args(dry_run=True))
        assert config["dry_run"] is True

    def test_rate_limit_default(self):
        config = build_config(make_args())
        assert config["rate_limit"] == 1.5

    def test_rate_limit_custom(self):
        config = build_config(make_args(rate_limit=2.0))
        assert config["rate_limit"] == 2.0

    def test_output_path_set(self):
        config = build_config(make_args(output="tenders.ndjson"))
        assert config["output"] == "tenders.ndjson"

    def test_page_size_default(self):
        config = build_config(make_args())
        assert config["page_size"] == 50

    def test_retries_default(self):
        config = build_config(make_args())
        assert config["retries"] == 3
