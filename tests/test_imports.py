def test_package_imports() -> None:
    import ai_impact_research
    from ai_impact_research.config import load_settings
    from ai_impact_research.logging import get_logger

    assert ai_impact_research.PACKAGE_NAME == "ai_impact_research"
    assert ai_impact_research.__version__ == "0.1.0"
    assert load_settings(env_file=None).project_name == "ai-impact-research"
    assert get_logger().name == "ai_impact_research"
