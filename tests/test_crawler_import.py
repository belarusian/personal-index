"""Tests for crawler package import and self-import fix."""



def test_crawler_package_imports():
    """Test that the crawler package can be imported without circular import errors."""
    import sys
    
    # Clear cached modules
    for k in list(sys.modules.keys()):
        if k.startswith("personal_index.crawler"):
            del sys.modules[k]
    
    import personal_index.crawler
    assert hasattr(personal_index.crawler, "Crawler")
    assert hasattr(personal_index.crawler, "CrawlerConfig")
    assert hasattr(personal_index.crawler, "WebCrawler")


def test_crawler_config_class():
    """Test that CrawlerConfig can be instantiated."""
    from personal_index.crawler import CrawlerConfig
    
    config = CrawlerConfig(max_depth=5, delay=0.5)
    assert config.max_depth == 5
    assert config.delay == 0.5


def test_webcrawler_uses_local_crawlerconfig():
    """Test that WebCrawler correctly references CrawlerConfig without self-import."""
    from personal_index.crawler import CrawlerConfig, WebCrawler
    
    config = CrawlerConfig(max_depth=2)
    crawler = WebCrawler(config=config)
    assert crawler.crawler.config.max_depth == 2
    crawler.close()


def test_no_self_import_in_source():
    """Test that crawler/__init__.py does not import from itself."""
    with open("personal_index/crawler/__init__.py") as f:
        source = f.read()
    
    assert "from personal_index.crawler.__init__ import" not in source
    assert "import personal_index.crawler.__init__" not in source
