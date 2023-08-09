import pytest


class KeyPair:
    def __init__(self, pubkey: str, privkey: str) -> None:
        self.pubkey = pubkey
        self.privkey = privkey


KEYS = [
    KeyPair(
        "age1dhwqzkah943xzc34tc3dlmfayyevcmdmxzjezdgdy33euxwf59vsp3vk3c",
        "AGE-SECRET-KEY-1KF8E3SR3TTGL6M476SKF7EEMR4H9NF7ZWYSLJUAK8JX276JC7KUSSURKFK",
    ),
    KeyPair(
        "age14tva0txcrl0zes05x7gkx56qd6wd9q3nwecjac74xxzz4l47r44sv3fz62",
        "AGE-SECRET-KEY-1U5ENXZQAY62NC78Y2WC0SEGRRMAEEKH79EYY5TH4GPFWJKEAY0USZ6X7YQ",
    ),
    KeyPair(
        "age1dhuh9xtefhgpr2sjjf7gmp9q2pr37z92rv4wsadxuqdx48989g7qj552qp",
        "AGE-SECRET-KEY-169N3FT32VNYQ9WYJMLUSVTMA0TTZGVJF7YZWS8AHTWJ5RR9VGR7QCD8SKF",
    ),
]


@pytest.fixture
def test_keys() -> list[KeyPair]:
    """
    Root directory of the tests
    """
    return KEYS
