def test_publish_returns_non_zero_code_for_upload_errors(app, app_tester, http):
    http.register_uri(
        http.POST, "https://upload.pypi.org/legacy/", status=400, body="Bad Request"
    )

    exit_code = app_tester.execute("publish --username foo --password bar")

    assert 1 == exit_code

    expected = """
Publishing simple-project (1.2.3) to PyPI


[UploadError]
HTTP Error 400: Bad Request
"""

    assert app_tester.io.fetch_output() == expected
