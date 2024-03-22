import pytest
from cli import Cli

from clan_vm_manager import main

def test_help(capsys: pytest.CaptureFixture) -> None:
    cli = Cli()
    with pytest.raises(SystemExit):
        cli.run(["clan-vm-manager", "--help"])
    captured = capsys.readouterr()
    with capsys.disabled():
        print("output not captured, going directly to sys.stdout")
    assert captured.out.startswith("Usage:")
