from mpxccp.bootstrap import run_app


def test_run_app_returns_zero_for_bootstrap_stub():
    assert run_app() == 0
