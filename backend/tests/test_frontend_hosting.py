import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.app.services.frontend import mount_frontend


@pytest.fixture
def site(tmp_path):
    (tmp_path / 'index.html').write_text('<html>ScamShield shell</html>')
    (tmp_path / 'assets').mkdir()
    (tmp_path / 'assets' / 'app.js').write_text('console.log("asset")')
    (tmp_path / '.env').write_text('PRIVATE_SECRET=never-serve')
    app = FastAPI()
    @app.get('/api/test')
    def api():
        return {'real': True}
    mount_frontend(app, tmp_path)
    return TestClient(app)


def test_real_api_and_static_assets(site):
    assert site.get('/api/test').json() == {'real': True}
    assert 'ScamShield shell' in site.get('/').text
    assert 'console.log' in site.get('/assets/app.js').text


@pytest.mark.parametrize('path', ['/family', '/verify-email', '/history', '/settings'])
def test_spa_refresh_routes(site, path):
    response = site.get(path, headers={'Accept': 'text/html'})
    assert response.status_code == 200
    assert 'ScamShield shell' in response.text


@pytest.mark.parametrize('path', ['/api/missing', '/assets/missing.js', '/.env', '/.git/config', '/health', '/openapi.json/missing'])
def test_missing_or_private_paths_never_become_html(site, path):
    response = site.get(path, headers={'Accept': 'text/html'})
    assert response.status_code == 404
    assert 'PRIVATE_SECRET' not in response.text
    assert 'ScamShield shell' not in response.text


def test_json_client_does_not_receive_spa(site):
    assert site.get('/unknown', headers={'Accept': 'application/json'}).status_code == 404
    assert site.post('/family').status_code == 405


def test_missing_build_fails_explicitly(tmp_path):
    with pytest.raises(RuntimeError, match='Frontend build missing'):
        mount_frontend(FastAPI(), tmp_path)
