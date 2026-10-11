"""Detection rules, overlap resolution, and the false-positive corpus. All values are fake."""
import random

import pytest

from app import detect
from app.detect import find_spans, luhn, redact


def kinds(text, **kw):
    return [s.kind for s in find_spans(text, **kw)]


def tag(kind, value):
    return f"<{kind}>"


# Token-shaped fakes are built by concatenation so secret scanners don't flag the repo.
POSITIVES = [
    ("PRIVATE_KEY", "-----BEGIN RSA " + "PRIVATE KEY-----\nFAKEFAKE\n-----END RSA " + "PRIVATE KEY-----"),
    ("ANTHROPIC_KEY", "sk-" + "ant-api03-" + "FAKE" * 6),
    ("OPENAI_KEY", "sk-" + "proj-" + "FAKE" * 6),
    ("GITHUB_TOKEN", "ghp_" + "X" * 36),
    ("GITHUB_TOKEN", "github_" + "pat_" + "X_" * 11),
    ("AWS_KEY", "AKIA" + "FAKEFAKEFAKE0000"),
    ("STRIPE_KEY", "sk_" + "live_" + "FAKE" * 5),
    ("STRIPE_KEY", "whsec_" + "FAKE" * 5),
    ("OTHER_TOKEN", "xox" + "b-000000000-FAKEFAKEFAKE"),
    ("OTHER_TOKEN", "AIza" + "F" * 35),
    ("OTHER_TOKEN", "eyJhbGciOiJIUzI1NiJ9." + "eyJzdWIiOiJmYWtlIn0.ZmFrZXNpZw"),
    ("OTHER_TOKEN", "postgres://admin:" + "fakepass@db.example.com"),
    ("SSN", "123-45-6789"),
    ("CREDIT_CARD", "4111 1111 1111 1111"),
    ("CREDIT_CARD", "4111111111111111"),
    ("EMAIL", "jane.doe@example.com"),
]


@pytest.mark.parametrize("kind,value", POSITIVES)
def test_positive(kind, value):
    text = f"here: {value} ok"
    assert kinds(text) == [kind]
    assert redact(text, tag) == f"here: <{kind}> ok"


def test_secret_keyword_and_entropy_redacts_only_value():
    assert redact('api_secret = "Zx9Qp2Lm7Rt4Wv8K"', tag) == 'api_secret = "<SECRET>"'


def test_secret_with_slashes_still_redacted():
    text = 'aws_secret_access_key = "wJalrXUtnF/K7MDENGbPxR/fiCYFAKEKEY"'
    assert redact(text, tag) == 'aws_secret_access_key = "<SECRET>"'


def test_secret_low_entropy_not_redacted():
    text = 'password = "aaaaaaaaaaaaaaaaaaaa"'
    assert redact(text, tag) == text


def test_phone_behind_flag(monkeypatch):
    pytest.importorskip("phonenumbers")
    monkeypatch.delenv("VEIL_PHONE", raising=False)
    text = "call me at (415) 555-2671 today"
    assert redact(text, tag) == text
    assert redact(text, tag, phone=True) == "call me at <PHONE> today"


def test_anthropic_beats_openai_on_overlap():
    assert kinds("sk-" + "ant-api03-" + "FAKE" * 6) == ["ANTHROPIC_KEY"]


def test_url_credentials_beat_email():
    assert kinds("https://bob:" + "fakepass@example.com/path") == ["OTHER_TOKEN"]


def test_placeholder_lookalike_is_escaped():
    assert kinds("literal [EMAIL_1] here") == ["ESCAPED"]


def test_order_independent():
    text = ("mail jane@example.com key=" + "sk-" + "ant-api03-" + "FAKE" * 6 +
            " card 4111-1111-1111-1111 ssn 123-45-6789 [EMAIL_3]")
    expected = redact(text, tag)
    rng = random.Random(0)
    for _ in range(20):
        rules = detect.RULES[:]
        rng.shuffle(rules)
        assert redact(text, tag, rules=rules) == expected


FALSE_POSITIVES = [
    "order id 1234567812345678 shipped",                        # random 16-digit, not Luhn
    "card 4111111111111112 declined",                          # off-by-one, not Luhn
    "request 550e8400-e29b-41d4-a716-446655440000 done",       # UUID
    "key: 550e8400-e29b-41d4-a716-446655440000",               # UUID even when keyword-gated
    "commit 9fceb02d0ae598e95dc970b74767f19372d61af8",         # git SHA
    "token = " + "a3f5" * 16,                                  # pure hex 64
    "The keys to the kingdom are: patience and a good map.",   # plain English
    "See [the docs](https://example.com/guide) for details.",  # markdown link
    "Version 3.11.4 released on 2024-06-06 at 10:00.",
    "config key: /usr/local/lib/python3.14/site-packages",    # absolute path
    "token_path = ./secrets/service-account-prod.json",       # relative path
    "key_file: ~/.ssh/id_ed25519_backup_2024",                # home path
    "secret_file=src/config/production-overrides.yaml",       # path with extension
]


@pytest.mark.parametrize("text", FALSE_POSITIVES)
def test_false_positive_corpus(text):
    assert find_spans(text) == []


def test_luhn():
    assert luhn("4111111111111111")
    assert not luhn("1234567812345678")
