"""The image says which licences it carries, and carries their texts.

The lab image installs the engine wheel `network-assessment-azure-engine`, whose metadata declares Apache-2.0, beside
this repository's MIT code. Its label `org.opencontainers.image.licenses` once said only `MIT`, and the image held no
licence text at all, although MIT asks for its notice with every copy and Apache-2.0 section 4 asks for the licence
and the NOTICE. These static checks pin the label, the bundled engine licence files, the COPY lines that put both
pairs into the image, and the two workflow steps that check the built image. That the files really are in the image
is proven by building it (the `image` job of ci.yml and the dry run of publish-images.yml).
"""

import importlib.metadata
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "infrastructure" / "docker" / "Dockerfile"
ENGINE_LICENCES = ROOT / "third_party" / "network-assessment-azure-engine"
EXPRESSION = "MIT AND Apache-2.0"
LABEL = re.compile(r'org\.opencontainers\.image\.licenses\s*=\s*"(?P<value>[^"]*)"')


def test_the_label_names_both_licences():
    labels = LABEL.findall(DOCKERFILE.read_text(encoding="utf-8"))
    assert labels == [EXPRESSION]


def test_the_licences_in_the_label_are_the_ones_the_code_declares():
    assert (ROOT / "LICENSE").read_text(encoding="utf-8").splitlines()[0].strip() == "MIT License"
    assert 'license = "MIT"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    meta = importlib.metadata.metadata("network-assessment-azure-engine")
    assert meta["License-Expression"] == "Apache-2.0"


def test_the_engine_licence_text_and_notice_are_bundled():
    licence = (ENGINE_LICENCES / "LICENSE").read_text(encoding="utf-8")
    assert "Apache License" in licence[:400] and "Version 2.0, January 2004" in licence[:400]
    assert "END OF TERMS AND CONDITIONS" in licence  # the whole text, not a pointer to it
    notice = (ENGINE_LICENCES / "NOTICE").read_text(encoding="utf-8")
    assert "network-assessment-azure-engine" in notice
    assert "Copyright 2026 Hybrid Cloud Works" in notice.splitlines()


def test_the_lab_stage_copies_both_licence_pairs_into_the_image():
    text = DOCKERFILE.read_text(encoding="utf-8")
    lab = text[text.index(" AS lab") :]
    assert "COPY LICENSE NOTICE /usr/share/licenses/hcw-networkeyes-addon/" in lab
    # third_party/<component>/ lands in /usr/share/licenses/<component>/; the folder is copied whole because the
    # edition-boundary test allows no cloud name on a code line of the Dockerfile.
    assert "COPY third_party/ /usr/share/licenses/" in lab
    assert sorted(p.name for p in (ROOT / "third_party").iterdir()) == ["network-assessment-azure-engine"]
    assert sorted(p.name for p in ENGINE_LICENCES.iterdir()) == ["LICENSE", "NOTICE"]
    ignored = (ROOT / ".dockerignore").read_text(encoding="utf-8").split()
    assert not any(entry.strip("/") in {"third_party", "LICENSE", "NOTICE"} for entry in ignored)


def test_notice_points_at_the_bundled_engine_licence():
    notice = " ".join((ROOT / "NOTICE").read_text(encoding="utf-8").split())
    assert f'"{EXPRESSION}"' in notice
    assert "third_party/network-assessment-azure-engine/" in notice
    assert "/usr/share/licenses/network-assessment-azure-engine/" in notice


def test_both_workflows_check_the_built_image_for_the_expression():
    for name in ("ci.yml", "publish-images.yml"):
        text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        assert f'= "{EXPRESSION}"' in text, name
        assert "/usr/share/licenses/" in text and "network-assessment-azure-engine/LICENSE" in text, name


def test_the_bundled_engine_licence_files_match_the_installed_wheel_when_it_ships_them():
    """From engine 0.1.3 the wheel ships LICENSE and NOTICE in its .dist-info/licenses/. Then the copies bundled here
    must be the same bytes, so a NOTICE changed upstream cannot drift from the one in the image unnoticed. Older wheels
    ship neither file, and there is nothing to compare."""
    dist = importlib.metadata.distribution("network-assessment-azure-engine")
    shipped = {Path(str(f)).name: f for f in dist.files or [] if Path(str(f)).parent.name == "licenses"}
    for name in ("LICENSE", "NOTICE"):
        if name in shipped:
            assert dist.locate_file(shipped[name]).read_bytes() == (ENGINE_LICENCES / name).read_bytes(), name
