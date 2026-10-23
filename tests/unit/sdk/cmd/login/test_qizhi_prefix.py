"""Regression coverage for gateways mounting SwanLab below a URL prefix."""

import io

import pytest
import responses
from click.testing import CliRunner

from swanlab.cli.auth.login import login as login_cli
from swanlab.sdk.cmd.login import login
from swanlab.sdk.internal.core_python import client
from swanlab.sdk.internal.core_python.api.upload import upload_resource
from swanlab.sdk.internal.pkg import nrc
from swanlab.sdk.internal.pkg.client.session import create
from swanlab.sdk.internal.settings import Settings, create_settings, set_global_settings

BASE = (
    "https://nat2-notebook-inspire.sii.edu.cn/ws-test/project-test/"
    "user-test/vscode/instance-test/session-test/proxy/8000"
)
LOGIN = {
    "sid": "test-sid",
    "expiredAt": "2099-12-31T23:59:59.000Z",
    "userInfo": {"username": "tester", "name": "Tester"},
}


@pytest.mark.parametrize("source", ["argument", "environment", "saved"])
@responses.activate
def test_login_and_metric_request_keep_proxy_prefix(source, monkeypatch):
    responses.post(BASE + "/api/login/api_key", json=LOGIN)
    responses.post(BASE + "/api/house/metrics", json={"ok": True})
    if source == "argument":
        assert login(api_key="test-key", host=BASE + "/?ignored=1#fragment", save=True)
    elif source == "environment":
        monkeypatch.setenv("SWANLAB_API_HOST", BASE + "/")
        monkeypatch.setenv("SWANLAB_WEB_HOST", BASE + "/")
        assert login(api_key="test-key", save=True)
    else:
        nrc.write(Settings.get_user_config_dir() / ".netrc", BASE, BASE, "test-key")
        set_global_settings(Settings())
        assert login()
    assert create_settings().api_host == BASE
    assert create_settings().web_host == BASE
    assert client.post("/house/metrics", {"metrics": []}).data == {"ok": True}
    client.reset()
    set_global_settings(Settings())
    assert login()
    assert responses.calls[-1].request.url == BASE + "/api/login/api_key"


@responses.activate
def test_cli_host_and_persisted_credentials():
    responses.post(BASE + "/api/login/api_key", json=LOGIN)
    result = CliRunner().invoke(login_cli, ["--host", BASE + "/", "--relogin", "--api-key", "test-key"])
    assert result.exit_code == 0, result.output
    assert responses.calls[0].request.url == BASE + "/api/login/api_key"
    assert nrc.read(Settings.get_user_config_dir() / ".netrc") == ("test-key", BASE, BASE)


@pytest.mark.parametrize("prefix", [BASE, "https://example.com/service/api"])
def test_netrc_round_trip_preserves_prefix(prefix, tmp_path):
    path = tmp_path / ".netrc"
    nrc.write(path, prefix, prefix, "test-key")
    assert nrc.read(path) == ("test-key", prefix, prefix)


@pytest.mark.parametrize(
    "host, expected",
    [
        (BASE + "/?x=1#fragment", BASE),
        ("http://[::1]:8000/proxy/8000/", "http://[::1]:8000/proxy/8000"),
        ("example.com/proxy/a%2Fb/", "https://example.com/proxy/a%2Fb"),
    ],
)
def test_url_normalization(host, expected):
    assert nrc.fmt(host) == expected


@responses.activate
def test_presigned_media_upload_keeps_proxy_prefix_and_query():
    responses.post(BASE + "/api/login/api_key", json=LOGIN)
    assert login(api_key="test-key", host=BASE)
    query = "X-Amz-Signature=abc&X-Amz-Credential=a%2Fb"
    origin = "https://nat2-notebook-inspire.sii.edu.cn"
    storage_path = "/swanlab-public/test.png?" + query
    responses.post(BASE + "/api/resources/presigned/put", json={"urls": [origin + storage_path]})
    responses.put(BASE + storage_path, status=200)
    with create(storage_base_url=create_settings().api_host) as session:
        upload_resource(session, "run-id", paths=["test.png"], buffers=[io.BytesIO(b"image")])
    assert responses.calls[-1].request.url == BASE + storage_path
    assert responses.calls[-1].request.body == b"image"


@responses.activate
def test_external_signed_storage_endpoint_is_unchanged():
    external = "https://external-s3.example.com/swanlab-private/key?X-Amz-Signature=abc"
    responses.put(external, status=200)
    with create(storage_base_url=BASE) as session:
        session.put(external, data=b"file")
    assert responses.calls[0].request.url == external
