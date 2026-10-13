"""The integration is often updated before the service: it must still load with a service one release behind, and say so.
These tests keep that true. Every route of the service is declared in compat_routes.json with the API level that introduced it; a route newer than
the minimum level the integration supports must be tolerated (a fallback, or only called after a user action the panel offers when the service has it)."""
import ast
import json
import pathlib

import pytest

import fake_service as fs
from test_integration import fake_service, setup_entry  # noqa: F401  (fake_service is autouse)
from custom_components.sound_recognition import api as client_mod
from custom_components.sound_recognition.api import SoundRecClient, SoundRecError
from custom_components.sound_recognition.const import MIN_API_LEVEL
from soundrec import api as service_api
from soundrec import API_LEVEL

ROUTES = json.loads((pathlib.Path(__file__).parent / "compat_routes.json").read_text())["routes"]


def norm(path: str) -> str:
    out, depth = "", 0
    for ch in path:
        if ch == "{":
            depth += 1
            if depth == 1:
                out += "{}"
        elif ch == "}":
            depth -= 1
        elif depth == 0:
            out += ch
    return out


def service_routes() -> set[str]:
    app = service_api.make_app(None, updater=object())
    found = set()
    for route in app.router.routes():
        path = route.resource.canonical.removeprefix(service_api.VERSION_PREFIX)
        if route.method != "HEAD":
            found.add(f"{route.method} {norm(path)}")
    return found


def client_routes() -> dict[str, str]:
    """method name -> 'VERB /path' for every self._request("VERB", "/path") of the client."""
    out = {}
    for fn in ast.walk(ast.parse(pathlib.Path(client_mod.__file__).read_text())):
        if not isinstance(fn, ast.AsyncFunctionDef):
            continue
        for call in ast.walk(fn):
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == "_request" and len(call.args) >= 2:
                verb, path = call.args[0], call.args[1]
                text = verb.value + " " + ("".join(p.value if isinstance(p, ast.Constant) else "{}" for p in path.values) if isinstance(path, ast.JoinedStr) else path.value)
                out.setdefault(fn.name, text)
    return out


def test_every_route_of_the_service_is_declared():
    missing = service_routes() - set(ROUTES)
    assert not missing, f"declare {sorted(missing)} in tests/compat_routes.json (with the API level that introduces it)"
    assert set(ROUTES) - service_routes() == set(), "a declared route no longer exists in the service"


def test_every_route_of_the_client_is_declared_under_its_method():
    for method, route in client_routes().items():
        assert route in ROUTES, f"{method} calls {route}, which is not declared in tests/compat_routes.json"
        assert ROUTES[route]["client"] == method, f"{route} is declared for {ROUTES[route]['client']}, not {method}"


def test_no_route_is_newer_than_the_service():
    assert max(r["since"] for r in ROUTES.values()) <= API_LEVEL


def test_a_route_newer_than_the_minimum_level_is_tolerated():
    for route, e in ROUTES.items():
        if e["since"] > MIN_API_LEVEL:
            assert e.get("tolerance") in ("fallback", "on_demand"), (
                f"{route} needs API level {e['since']} but the integration supports {MIN_API_LEVEL}: "
                "give the client a fallback and declare tolerance 'fallback', or call it only on user action and declare 'on_demand'")


@pytest.mark.parametrize("route", [r for r, e in ROUTES.items() if e.get("tolerance") == "fallback"])
async def test_a_fallback_route_does_not_break_the_client(route):
    """The real client method, against a service that answers 404 on that route and works elsewhere."""
    name = ROUTES[route]["client"]
    client = SoundRecClient(None, "h", 1, "t")
    seen = []

    async def request(method, path, **kw):
        seen.append(f"{method} {path}")
        if f"{method} {path}" == route:
            raise SoundRecError(f"HTTP 404 on {path}")
        return {}
    client._request = request
    await getattr(client, name)()                      # must not raise
    assert len(seen) >= 2, "the method should have fallen back on another route"


async def test_the_integration_loads_with_the_service_one_release_behind(hass, hass_ws_client):
    """Panel, update entity and the repair that leads to the update are there; the panel's first calls answer."""
    from homeassistant.helpers import issue_registry as ir
    from custom_components.sound_recognition.const import DOMAIN
    fs.STATE.api_level = API_LEVEL - 1
    entry = await setup_entry(hass)
    assert entry.state.name == "LOADED"
    assert hass.data.get(f"{DOMAIN}_panel"), "the sidebar panel is registered"
    assert hass.states.get("update.sound_recognition_service") is not None
    assert (ir.async_get(hass).async_get_issue(DOMAIN, f"service_outdated_{entry.entry_id}") is not None) == (API_LEVEL - 1 < MIN_API_LEVEL)
    ws = await hass_ws_client(hass)
    for n, cmd in enumerate(("overview", "config", "storage", "update"), 1):
        await ws.send_json({"id": n, "type": f"{DOMAIN}/{cmd}"})
        reply = await ws.receive_json()
        assert reply["success"], f"{cmd}: {reply}"
    await ws.send_json({"id": 9, "type": f"{DOMAIN}/catalog", "language": "en"})
    assert (await ws.receive_json())["success"]
