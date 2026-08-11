"""Tests to verify all modules import correctly after unused import cleanup."""

import importlib
import sys
import pytest


def get_all_modules():
    """Get all importable modules from personal_index."""
    import os
    modules = []
    for root, dirs, files in os.walk("personal_index"):
        for f in files:
            if f.endswith(".py") and f != "__init__.py":
                mod_path = os.path.join(root, f)[:-3].replace("/", ".")
                modules.append(mod_path)
    return sorted(modules)


# Known pre-existing syntax errors - skip these
SKIP_MODULES = {


}


@pytest.mark.parametrize("mod_name", get_all_modules())
def test_module_imports(mod_name):
    """Test that each module can be imported without errors."""
    if mod_name in SKIP_MODULES:
        pytest.skip(f"Pre-existing syntax error in {mod_name}")
    
    # Clear cached modules
    for k in list(sys.modules.keys()):
        if k.startswith("personal_index"):
            del sys.modules[k]
    
    importlib.import_module(mod_name)


def test_url_utils_imports():
    """Test that url_utils module imports all expected functions."""
    from personal_index.url_utils import (
        normalize_url,
        extract_domain,
        get_domain,
        get_path,
        get_query_string,
        get_fragment,
        is_canonical,
        urls_are_equivalent,
        strip_tracking_params,
        resolve_relative_url,
        is_valid_url,
        extract_subdomain,
        get_tld,
        is_same_domain,
        is_internal_link,
        remove_query_params,
        url_to_path,
        join_urls,
        extract_all_urls,
        is_robotstxt,
        is_sitemap,
        is_excluded_url,
    )
    assert callable(normalize_url)
    assert callable(extract_domain)
    assert get_domain is extract_domain


def test_url_normalizer_removed():
    """Test that url_normalizer module has been removed."""
    with pytest.raises(ModuleNotFoundError):
        import personal_index.url_normalizer  # noqa: F401


def test_similarity_removed():
    """Test that similarity module has been removed."""
    with pytest.raises(ModuleNotFoundError):
        import personal_index.similarity  # noqa: F401
