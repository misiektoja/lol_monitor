"""Tests that the documentation site describes what the tool actually does, so stale claims fail here."""

import re
from pathlib import Path

import pytest

import lol_monitor as monitor


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
README = REPO_ROOT / "README.md"
MKDOCS = REPO_ROOT / "mkdocs.yml"


# Returns one value from the site configuration, which is where the published URLs are declared
def mkdocs_setting(name):
    match = re.search(rf"^{name}:\s*(\S+)\s*$", MKDOCS.read_text(encoding="utf-8"), flags=re.MULTILINE)
    assert match is not None, f"mkdocs.yml declares no {name}"
    return match.group(1).rstrip("/")


SITE_URL = mkdocs_setting("site_url")
PROJECT_URL = mkdocs_setting("repo_url")


# Returns the text of every documentation page joined together
def all_docs_text():
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(DOCS_DIR.glob("*.md")))


# Returns the anchors one documentation page defines, from headings and from explicit anchor tags
def page_anchors(path):
    text = path.read_text(encoding="utf-8")
    anchors = set(re.findall(r'<a id="([^"]+)"></a>', text))
    for line in text.splitlines():
        if not line.startswith("#"):
            continue
        title = line.lstrip("#").strip()
        anchors.add("".join(character for character in title.casefold().replace(" ", "-") if character.isalnum() or character in "-_"))
    return anchors


# Returns the page filenames the navigation lists, in order
def navigation_pages():
    navigation = MKDOCS.read_text(encoding="utf-8").split("nav:", 1)[1]
    return re.findall(r":\s*([a-z0-9-]+\.md)\s*$", navigation, flags=re.MULTILINE)


# Returns every long command-line flag one script's parser accepts
def declared_flags(*sources):
    return {flag for source in sources for flag in re.findall(r"""["'](--[a-z0-9-]+)["']""", source.read_text(encoding="utf-8"))}


# Returns the long flags one set of pages promises the reader can type
def promised_flags(*pages):
    return set(re.findall(r"(--[a-z][a-z0-9-]+)", "\n".join(page.read_text(encoding="utf-8") for page in pages)))


# Verifies every page the navigation lists exists, so a renamed file fails here rather than in the built site
def test_every_navigation_entry_exists():
    for filename in navigation_pages():
        assert (DOCS_DIR / filename).exists(), f"the navigation lists a missing page: {filename}"


# Verifies every page on disk is reachable from the navigation, so a new page cannot be orphaned
def test_every_page_is_reachable_from_the_navigation():
    listed = set(navigation_pages())

    orphans = sorted(path.name for path in DOCS_DIR.glob("*.md") if path.name not in listed)

    assert not orphans, f"pages not listed in the navigation: {orphans}"


# Verifies every internal documentation link points at a page and anchor that exist
def test_every_internal_documentation_link_resolves():
    broken = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\]\((?!https?:|mailto:)([^)]+)\)", text):
            page_part, _, anchor = target.partition("#")
            target_page = path if not page_part else (DOCS_DIR / page_part)
            if page_part and not target_page.exists():
                broken.append(f"{path.name} -> {target}")
                continue
            if anchor and anchor not in page_anchors(target_page):
                broken.append(f"{path.name} -> {target}")

    assert not broken, f"broken documentation links: {broken}"


# Verifies the README landing page links only at pages the site really publishes
def test_the_readme_links_resolve():
    text = README.read_text(encoding="utf-8")
    broken = []

    for url in re.findall(rf"{re.escape(SITE_URL)}([^\s)]*)", text):
        slug = url.split("#")[0].strip("/")
        page = DOCS_DIR / "index.md" if not slug else DOCS_DIR / f"{slug}.md"
        if not page.exists():
            broken.append(url or "/")

    assert not broken, f"the README links at missing documentation pages: {broken}"


# Every markdown file outside the site that links into the repository, and which a docs move can silently break
REPOSITORY_MARKDOWN = ("README.md", "SUPPORT.md", "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "THIRD_PARTY_NOTICES.md", ".github/pull_request_template.md")

# The issue templates link out of YAML rather than markdown, which is where the last README anchors survive
ISSUE_TEMPLATES = (".github/ISSUE_TEMPLATE/config.yml", ".github/ISSUE_TEMPLATE/bug_report.yml", ".github/ISSUE_TEMPLATE/feature_request.yml")


# Returns the local link targets one repository file names, reading a link to the project page as a README anchor
def repository_link_targets(text):
    targets = re.findall(r"\]\((?!https?:|mailto:)([^)]+)\)", text)
    return list(targets) + [f"README.md#{anchor}" for anchor in re.findall(rf"{re.escape(PROJECT_URL)}/?#([^\s)\"']+)", text)]


# Verifies no repository document still points at a README section, which is how a docs move leaves dead links behind
def test_no_repository_document_links_at_a_missing_local_target():
    broken = []
    for relative_path in REPOSITORY_MARKDOWN + ISSUE_TEMPLATES:
        path = REPO_ROOT / relative_path
        if not path.exists():
            continue
        for target in repository_link_targets(path.read_text(encoding="utf-8")):
            page_part, _, anchor = target.partition("#")
            target_page = path if not page_part else (REPO_ROOT / page_part)
            if page_part and not target_page.exists():
                broken.append(f"{relative_path} -> {target}")
                continue
            if anchor and anchor not in page_anchors(target_page):
                broken.append(f"{relative_path} -> {target}")

    assert not broken, f"repository documents linking at missing targets: {broken}"


# Verifies each user-facing command is documented, since an undocumented one may as well not exist
@pytest.mark.parametrize("flag", ["--config-file", "--generate-config", "--env-file", "--riot-api-key", "--send-test-email", "--list-recent-matches", "--csv-file", "--disable-logging", "--include-forbidden-matches"])
def test_user_facing_flags_are_documented(flag):
    text = all_docs_text()
    short = {"--riot-api-key": "-r", "--send-test-email": None, "--list-recent-matches": "-l", "--csv-file": "-b", "--disable-logging": "-d", "--include-forbidden-matches": "-f"}.get(flag)

    assert flag in text or (short and f"`{short}`" in text), f"{flag} is not documented on the site"


# Flags belonging to programs this project does not own, each named so the exemption cannot grow silently
THIRD_PARTY_FLAGS = {
    "--refresh",
    "--strict",  # mkdocs build --strict, the documentation gate described on the testing page
}


# Verifies the pages about the monitor promise no flag its parser does not accept, which is how a sentence copied from a sibling rots
def test_the_documentation_does_not_promise_flags_that_do_not_exist():
    pages = [path for path in sorted(DOCS_DIR.glob("*.md")) if path.name != "tools.md"]
    accepted = declared_flags(REPO_ROOT / "lol_monitor.py") | {"--help", "--version"} | THIRD_PARTY_FLAGS

    promised = promised_flags(*pages)

    assert promised - accepted == set(), f"the documentation names flags the parser does not accept: {sorted(promised - accepted)}"


# Verifies the Utility Tools page promises no flag those scripts do not accept, since they have parsers of their own
def test_the_utility_tools_page_does_not_promise_flags_that_do_not_exist():
    accepted = declared_flags(*sorted((REPO_ROOT / "tools").glob("*.py"))) | {"--help"}

    promised = promised_flags(DOCS_DIR / "tools.md")

    assert promised - accepted == set(), f"the Utility Tools page names flags the scripts do not accept: {sorted(promised - accepted)}"


# Verifies the README stayed a landing page rather than growing back into the full documentation
def test_the_readme_is_a_landing_page():
    text = README.read_text(encoding="utf-8")

    assert len(text) < 8000, "the README has grown back into full documentation"
    assert SITE_URL in text, "the README does not link to the documentation site"


# Verifies the documentation build is a step CI runs, rather than only a job name that says so
def test_the_documentation_build_is_a_ci_gate():
    workflow = (REPO_ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    commands = [match.strip() for match in re.findall(r"^\s*run:\s*(.+)$", workflow, flags=re.MULTILINE)]

    assert any("mkdocs build --strict" in command for command in commands), "CI does not build the documentation site"
    assert any("docs/requirements.txt" in command for command in commands), "CI does not install the documentation dependencies"


# Verifies a published site can actually be built, since the workflow that deploys it must have somewhere to deploy from
def test_the_site_has_a_publishing_workflow():
    workflow = REPO_ROOT / ".github" / "workflows" / "docs.yml"

    assert workflow.exists(), "there is no workflow to publish the documentation"
    assert "mkdocs gh-deploy" in workflow.read_text(encoding="utf-8")


# Returns one page's markdown with fenced code blocks removed, so shell comments are not read as headings
def prose_lines(path):
    text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
    return text.splitlines()


# Verifies each page has exactly one title, which a mechanical split silently breaks
def test_each_page_has_exactly_one_title():
    for path in sorted(DOCS_DIR.glob("*.md")):
        titles = [line for line in prose_lines(path) if line.startswith("# ")]
        assert len(titles) == 1, f"{path.name} has {len(titles)} titles: {titles}"


# Verifies no section is documented on two pages, since a reader who finds one will not know the other exists
def test_no_section_is_duplicated_across_pages():
    seen = {}
    duplicates = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        for line in prose_lines(path):
            if not line.startswith("## "):
                continue
            title = line[3:].strip()
            if title in seen:
                duplicates.append(f"'{title}' in both {seen[title]} and {path.name}")
            seen[title] = path.name

    assert not duplicates, f"sections documented twice: {duplicates}"


# Verifies the set of pages is what the project intends, so a page cannot appear or vanish unnoticed
def test_the_page_set_is_deliberate():
    expected = {"index.md", "installation.md", "setup-and-first-run.md", "configuration.md", "usage.md", "tools.md", "troubleshooting.md", "testing.md", "about.md"}

    assert {path.name for path in DOCS_DIR.glob("*.md")} == expected


# Verifies a page is never named after something this project does not have
def test_no_page_promises_tooling_that_does_not_exist():
    # The Utility Tools page documents the standalone scripts under tools/, and it is the only page named after a directory
    if not (REPO_ROOT / "tools").is_dir():
        assert not (DOCS_DIR / "tools.md").exists(), "there is a Utility Tools page but no utilities to document"

    # The sibling tools have a Debugging Tools page because they ship standalone utilities in a debug directory
    if not (REPO_ROOT / "debug").is_dir():
        assert not (DOCS_DIR / "debugging.md").exists(), "there is a Debugging Tools page but no debug utilities to document"


# Verifies every script the Utility Tools page documents is actually in the repository
def test_the_utility_tools_page_names_scripts_that_exist():
    text = (DOCS_DIR / "tools.md").read_text(encoding="utf-8")
    present = {path.name for path in (REPO_ROOT / "tools").glob("*.py")}
    named = set(re.findall(r"(lol_[a-z_]+\.py)", text))

    assert named == present, f"the Utility Tools page and tools/ disagree: page names {sorted(named)}, directory holds {sorted(present)}"


# Verifies each section sits on the page a reader would look for it on, matching the sibling tools
@pytest.mark.parametrize("section,page", [
    ("Requirements", "installation.md"),
    ("Quick Start", "setup-and-first-run.md"),
    ("Riot API Key", "setup-and-first-run.md"),
    ("Region Codes", "setup-and-first-run.md"),
    ("Configuration File", "configuration.md"),
    ("SMTP Settings", "configuration.md"),
    ("Storing Secrets", "configuration.md"),
    ("Check Intervals", "configuration.md"),
    ("Monitoring Mode", "usage.md"),
    ("Listing Mode", "usage.md"),
    ("Email Notifications", "usage.md"),
    ("CSV Export", "usage.md"),
    ("Coloring Log Output with GRC", "usage.md"),
    ("When Something Goes Wrong", "troubleshooting.md"),
])
def test_sections_sit_on_the_page_a_reader_expects(section, page):
    located = [path.name for path in sorted(DOCS_DIR.glob("*.md")) if f"## {section}" in "\n".join(prose_lines(path))]

    assert located == [page], f"'{section}' is on {located}, expected {page}"


# A guide that lists the test files goes stale the moment one is added and nothing else notices
def test_the_test_suite_guide_lists_every_test_file():
    listed = set(re.findall(r"^\| `([^`]+)` \|", (REPO_ROOT / "tests" / "README.md").read_text(encoding="utf-8"), re.M))
    present = {path.name for path in (REPO_ROOT / "tests").glob("test_*.py")} | {path.name for path in (REPO_ROOT / "tests").glob("conftest.py")}

    assert present - listed == set(), f"test files missing from tests/README.md: {sorted(present - listed)}"
    assert {name for name in listed if name.endswith(".py")} - present == set(), f"tests/README.md names files that do not exist: {sorted({name for name in listed if name.endswith('.py')} - present)}"


# Verifies the documented doctor sections are exactly the ones the report renders
def test_the_documented_doctor_sections_match_the_code():
    text = (DOCS_DIR / "troubleshooting.md").read_text(encoding="utf-8")

    for section in monitor.DOCTOR_SECTIONS:
        assert f"**{section}**" in text, f"the {section} doctor section is not documented"


# Verifies every setting the config template ships is described somewhere on the site, since an undocumented setting is one nobody can use
def test_every_configuration_setting_is_documented():
    settings = sorted(set(re.findall(r"(?m)^([A-Z][A-Z0-9_]*) =", monitor.CONFIG_BLOCK)))
    documented = all_docs_text()

    assert settings, "the sweep found no settings in the config template"
    missing = [name for name in settings if name not in documented]
    assert not missing, f"settings the documentation never mentions: {', '.join(missing)}"
