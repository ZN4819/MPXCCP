def test_widgets_package_exports_shared_widgets():
    from mpxccp.ui import widgets

    assert widgets.RiskWidget
    assert widgets.ProductListWidget
    assert widgets.EvidenceDialog
    assert widgets.ImageUploadWidget
    assert widgets.KnowledgePicker
