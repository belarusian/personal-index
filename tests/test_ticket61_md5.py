"""Test TICKET-61: No md5 usage for content fingerprinting."""



def test_content_dedup_no_md5():
    """content_dedup.py should not use hashlib.md5."""
    with open('personal_index/content_dedup.py', 'r') as f:
        content = f.read()
    assert 'hashlib.md5' not in content, "content_dedup.py should not use hashlib.md5"
    # Should use sha256 instead
    assert 'hashlib.sha256' in content, "content_dedup.py should use hashlib.sha256"


def test_versioning_no_md5():
    """versioning.py should not use hashlib.md5."""
    with open('personal_index/versioning.py', 'r') as f:
        content = f.read()
    assert 'hashlib.md5' not in content, "versioning.py should not use hashlib.md5"
    # Should use sha256 instead
    assert 'hashlib.sha256' in content, "versioning.py should use hashlib.sha256"


def test_content_dedup_fingerprint_works():
    """compute_fingerprint should still work after replacing md5 with sha256."""
    from personal_index.content_dedup import DocumentHash
    fp = DocumentHash.compute_fingerprint("test content")
    assert isinstance(fp, str)
    assert len(fp) == 16  # Still 16 chars
    # Deterministic
    assert DocumentHash.compute_fingerprint("test content") == fp


def test_versioning_generate_version_id_works():
    """generate_version_id should still work after replacing md5 with sha256."""
    from personal_index.versioning import VersionTracker
    vid = VersionTracker.generate_version_id("http://example.com", "abc123")
    assert isinstance(vid, str)
    assert len(vid) == 12  # Still 12 chars
    # Deterministic
    assert VersionTracker.generate_version_id("http://example.com", "abc123") == vid
