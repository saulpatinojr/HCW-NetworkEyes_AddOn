import pytest

from network_assessment.config import MAX_SETTING, Settings


def test_defaults_from_empty_env():
    s = Settings.from_env({})
    assert s.port == 8080 and s.frame_ancestors == "'none'" and s.ttl_minutes == 120 and s.max_items == 200
    assert s.rate_limit_posts == 10 and s.rate_limit_window_minutes == 10 and s.max_concurrent == 2
    assert not s.trust_proxy and not s.allow_no_turnstile and s.turnstile_secret is None and s.public_host is None
    assert s.turnstile_enforced and not s.turnstile_required, (
        "fail closed: no secret and no override means uploads answer 503"
    )
    assert s.static_dir.name == "web" and s.samples_dir.name == "samples"
    assert MAX_SETTING == 1_000_000_000


def test_full_env():
    s = Settings.from_env(
        {
            "PORT": "9000",
            "NA_ALLOWED_ORIGINS": "https://a.example, https://b.example/ https://a.example",
            "NA_FRAME_ANCESTORS": "https://hybridcloudworks.com https://www.hybridcloudworks.com",
            "NA_SITE_ORIGINS": "https://hybridcloudworks.com",
            "TURNSTILE_SECRET": " s3 ",
            "NA_TURNSTILE_SITE_KEY": "k",
            "NA_PUBLIC_HOST": "Network-Assessment.lab.hybridcloudworks.com",
            "NA_ALLOW_NO_TURNSTILE": "true",
            "NA_TTL_MINUTES": "5",
            "NA_MAX_ITEMS": "3",
            "NA_RATE_LIMIT_POSTS": "2",
            "NA_RATE_LIMIT_WINDOW_MINUTES": "1",
            "NA_MAX_CONCURRENT": "1",
            "NA_TRUST_PROXY": "1",
            "NA_LOG_SILENT": "yes",
            "NA_STATIC_DIR": "/tmp/web",
            "NA_SAMPLES_DIR": "/tmp/samples",
        }
    )
    assert s.port == 9000 and s.allowed_origins == ("https://a.example", "https://b.example")
    assert s.site_origins == ("https://hybridcloudworks.com",) and s.turnstile_secret == "s3" and s.turnstile_required
    assert s.public_host == "network-assessment.lab.hybridcloudworks.com"
    assert s.turnstile_enforced and s.trust_proxy and s.log_silent and str(s.static_dir) == "/tmp/web"
    assert "s3" not in repr(s), "the secret never appears in repr"


def test_override_only_applies_without_secret():
    s = Settings.from_env({"NA_ALLOW_NO_TURNSTILE": "1"})
    assert not s.turnstile_enforced and not s.turnstile_required


@pytest.mark.parametrize(
    "env",
    [
        {"PORT": "abc"},
        {"PORT": "0"},
        {"NA_TTL_MINUTES": "-1"},
        {"NA_TTL_MINUTES": "9" * 400},
        {"NA_RATE_LIMIT_POSTS": "1000000001"},
        {"NA_MAX_CONCURRENT": "1.5"},
        {"NA_ALLOWED_ORIGINS": "example.com"},
        {"NA_FRAME_ANCESTORS": "'self'; script-src *"},
        {"NA_PUBLIC_HOST": "https://host/"},
    ],
)
def test_invalid_values_raise(env):
    with pytest.raises(ValueError):
        Settings.from_env(env)
