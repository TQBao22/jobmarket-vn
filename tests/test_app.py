from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

APP = Path(__file__).parent.parent / "app.py"


@pytest.mark.skipif(not Path("data/public/skill_counts.csv").exists(), reason="chưa chạy jobmarket.aggregate")
def test_dashboard_renders_without_error():
    at = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not at.exception
    assert int(at.metric[0].value) > 0
