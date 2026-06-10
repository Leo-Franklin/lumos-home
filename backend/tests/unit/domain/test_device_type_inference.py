"""Unit tests for weighted device type inference."""

from app.domain.services.device_type_inference import (
    guess_device_type_detailed,
    infer_display_vendor,
    resolve_persisted_device_type,
    should_persist_camera_type,
)


def _classify(**kwargs):
    """Shorthand for inference — device type must not depend on specific LAN IPs."""
    return guess_device_type_detailed(**kwargs)


def test_chromecast_ports_suggest_tv():
    device_type, confidence, signals = _classify(
        vendor='Unknown',
        open_ports=[8008, 8009],
        hostname=None,
    )
    assert device_type == 'tv'
    assert confidence >= 0.8
    assert any(s['source'] == 'ports' for s in signals)


def test_mqtt_port_suggests_iot():
    device_type, _, signals = _classify(
        vendor='Unknown',
        open_ports=[1883],
        hostname=None,
    )
    assert device_type == 'iot'
    assert any(s['source'] == 'ports' for s in signals)


def test_zte_gateway_is_router_not_phone():
    """ZTE CPE marked as default gateway must not be classified as phone."""
    device_type, confidence, signals = _classify(
        vendor='ZTE Corporation',
        open_ports=[80, 443],
        hostname='SuishenWiFi',
        is_gateway=True,
        mac='CC:32:65:12:34:56',
        ttl=64,
    )
    assert device_type == 'router'
    assert confidence >= 0.85
    assert any(s['source'] == 'gateway' for s in signals)
    assert any(s['source'] == 'vendor' and s['type'] == 'router' for s in signals)


def test_zte_vendor_without_gateway_still_router():
    device_type, confidence, _ = _classify(
        vendor='ZTE Corporation',
        open_ports=[80, 443],
        hostname='SuishenWiFi',
        is_gateway=False,
        mac='CC:32:65:12:34:56',
    )
    assert device_type == 'router'
    assert confidence >= 0.8


def test_honor_vendor_classifies_phone():
    device_type, confidence, signals = _classify(
        vendor='Honor Device Co.,Ltd.',
        open_ports=[],
        hostname=None,
        is_gateway=False,
        mac='AA:BB:CC:DD:EE:FF',
    )
    assert device_type == 'phone'
    assert confidence >= 0.65
    assert any(s['source'] == 'vendor' for s in signals)


def test_huawei_technologies_phone_not_gateway():
    device_type, confidence, _ = _classify(
        vendor='Huawei Technologies Co.,Ltd',
        open_ports=[],
        hostname=None,
        is_gateway=False,
        mac='AA:BB:CC:DD:EE:FF',
        ttl=64,
    )
    assert device_type == 'phone'
    assert confidence >= 0.65


def test_huawei_technologies_gateway_is_router():
    device_type, _, signals = _classify(
        vendor='Huawei Technologies Co.,Ltd',
        open_ports=[80, 443],
        hostname='gateway',
        is_gateway=True,
        http_banners={80: {'server': 'httpd', 'title': 'Wireless Router'}},
    )
    assert device_type == 'router'
    assert any(s['type'] == 'router' for s in signals)


def test_honor_hostname_classifies_phone():
    device_type, confidence, signals = _classify(
        vendor='Unknown',
        open_ports=[],
        hostname='HONOR-Magic6-Pro',
    )
    assert device_type == 'phone'
    assert confidence >= 0.65
    assert any(s['source'] == 'hostname' for s in signals)


def test_random_mac_and_android_ttl_classifies_phone():
    """Honor phone with privacy MAC often has vendor=Unknown — use MAC+TTL stack."""
    device_type, confidence, signals = _classify(
        vendor='Unknown',
        open_ports=[],
        hostname=None,
        is_gateway=False,
        mac='02:11:22:33:44:55',
        ttl=64,
    )
    assert device_type == 'phone'
    assert confidence >= 0.55
    sources = {s['source'] for s in signals}
    assert 'mac' in sources
    assert 'ttl' in sources


def test_gateway_flag_blocks_phone_from_ttl_alone():
    device_type, _, signals = _classify(
        vendor='Unknown',
        open_ports=[],
        hostname=None,
        is_gateway=True,
        mac='02:11:22:33:44:55',
        ttl=64,
    )
    assert device_type == 'router'
    assert any(s['source'] == 'gateway' for s in signals)


def test_non_dot_one_gateway_ip_with_flag():
    """Gateway at .254 must be recognized via is_gateway, not x.x.x.1 heuristic."""
    device_type, confidence, signals = _classify(
        vendor='Unknown',
        open_ports=[80, 443],
        hostname='gateway',
        is_gateway=True,
        http_banners={80: {'server': 'httpd', 'title': 'Wireless Router'}},
    )
    assert device_type == 'router'
    assert confidence >= 0.75
    assert any(s['source'] == 'gateway' for s in signals)


def test_dot_one_ip_without_gateway_flag_is_not_router():
    """Legacy .1 heuristic removed — .1 alone must not imply router."""
    device_type, _, signals = _classify(
        vendor='Unknown',
        open_ports=[],
        hostname=None,
        is_gateway=False,
        mac='02:11:22:33:44:55',
        ttl=64,
    )
    assert device_type == 'phone'
    assert not any(s['source'] == 'gateway' for s in signals)


def test_ip_camera_rtsp_port():
    device_type, confidence, signals = _classify(
        vendor='Unknown',
        open_ports=[554, 80],
        hostname=None,
        http_banners={80: {'server': 'App-webs', 'title': 'IP Camera'}},
    )
    assert device_type == 'camera'
    assert confidence >= 0.85
    assert any(s['source'] == 'ports' for s in signals)
    assert any(s['source'] == 'http' for s in signals)


def test_dahua_service_port_detects_camera():
    device_type, confidence, _ = _classify(
        vendor='Zhejiang Dahua Technology Co., Ltd.',
        open_ports=[37777, 80],
        hostname='IPC',
    )
    assert device_type == 'camera'
    assert confidence >= 0.85


def test_upnp_security_camera_type():
    device_type, confidence, signals = _classify(
        vendor='Unknown',
        open_ports=[],
        hostname=None,
        upnp={
            'device_type': 'urn:schemas-upnp-org:device:DigitalSecurityCamera:1',
            'manufacturer': 'Hikvision',
            'model_name': 'DS-2CD2142',
            'friendly_name': 'Camera 01',
        },
    )
    assert device_type == 'camera'
    assert confidence >= 0.8
    assert any(s['source'] == 'upnp' for s in signals)


def test_hikvision_mac_vendor_detects_camera():
    device_type, confidence, signals = _classify(
        vendor='Hangzhou Hikvision Digital Technology Co.,Ltd.',
        open_ports=[],
        hostname=None,
    )
    assert device_type == 'camera'
    assert confidence >= 0.8
    assert any(s['source'] == 'vendor' for s in signals)


def test_infer_display_vendor_from_upnp_when_mac_unknown():
    label = infer_display_vendor(
        'Unknown',
        upnp={'manufacturer': 'Hikvision', 'model_name': 'DS-2CD2042'},
    )
    assert label == 'Hikvision DS-2CD2042'


def test_infer_display_vendor_from_http_banner():
    label = infer_display_vendor(
        'Unknown',
        http_banners={80: {'server': 'Webs', 'title': 'hikvision digital technology'}},
    )
    assert label == 'Hikvision'


def test_should_persist_camera_when_confident():
    assert should_persist_camera_type(
        'camera',
        0.9,
        [{'source': 'ports', 'type': 'camera', 'reason': 'camera service ports: [554]'}],
    )


def test_resolve_persisted_device_type_keeps_confident_camera():
    data = {
        'device_type': 'camera',
        'scan_metadata': {
            'type_confidence': 0.9,
            'type_signals': [{'source': 'ports', 'type': 'camera', 'reason': '554'}],
        },
    }
    assert resolve_persisted_device_type(data) == 'camera'


def test_resolve_persisted_device_type_downgrades_weak_camera():
    data = {
        'device_type': 'camera',
        'scan_metadata': {
            'type_confidence': 0.4,
            'type_signals': [{'source': 'ports', 'type': 'camera', 'reason': '554'}],
        },
    }
    assert resolve_persisted_device_type(data) == 'unknown'


def test_tplink_ipc682_with_rtsp_is_camera_not_router():
    """TP-Link IPC must not lose to router signals from vendor + port 80."""
    device_type, confidence, signals = _classify(
        vendor='TP-LINK TECHNOLOGIES CO.,LTD.',
        open_ports=[554, 80],
        hostname=None,
        is_gateway=False,
        http_banners={80: {'server': 'App-webs', 'title': 'IP Camera'}},
    )
    assert device_type == 'camera'
    assert confidence >= 0.85
    assert any(s['source'] == 'vendor' and s['type'] == 'camera' for s in signals)
    assert not any(s['source'] == 'vendor' and s['type'] == 'router' for s in signals)


def test_tplink_onvif_port_2020_detects_camera():
    device_type, confidence, signals = _classify(
        vendor='TP-LINK TECHNOLOGIES CO.,LTD.',
        open_ports=[80, 2020],
        hostname=None,
        is_gateway=False,
    )
    assert device_type == 'camera'
    assert confidence >= 0.85
    assert any(s['source'] == 'ports' for s in signals)


def test_tplink_web_only_without_router_banner_is_camera():
    """IPC with only HTTP admin UI — no RTSP/ONVIF in scan result."""
    device_type, confidence, signals = _classify(
        vendor='TP-LINK TECHNOLOGIES CO.,LTD.',
        open_ports=[80],
        hostname=None,
        is_gateway=False,
        http_banners={80: {'server': 'httpd', 'title': 'Login'}},
    )
    assert device_type == 'camera'
    assert confidence >= 0.65
    assert any(s['source'] in ('vendor', 'http') and s['type'] == 'camera' for s in signals)


def test_tplink_wireless_router_stays_router():
    device_type, confidence, signals = _classify(
        vendor='TP-LINK TECHNOLOGIES CO.,LTD.',
        open_ports=[80, 443],
        hostname='tplink-router',
        is_gateway=True,
        http_banners={80: {'server': 'httpd', 'title': 'TP-LINK Wireless Router'}},
    )
    assert device_type == 'router'
    assert confidence >= 0.85
    assert any(s['source'] == 'vendor' and s['type'] == 'router' for s in signals)


def test_tplink_tapo_hostname_detects_camera():
    device_type, confidence, signals = _classify(
        vendor='TP-LINK TECHNOLOGIES CO.,LTD.',
        open_ports=[80],
        hostname='Tapo_C200',
        is_gateway=False,
    )
    assert device_type == 'camera'
    assert confidence >= 0.75
    assert any(s['source'] == 'hostname' for s in signals)


def test_infer_display_vendor_normalizes_tplink_mac_oui():
    label = infer_display_vendor('TP-LINK TECHNOLOGIES CO.,LTD.')
    assert label == 'TP-Link'


def test_infer_display_vendor_tplink_tapo_from_http():
    label = infer_display_vendor(
        'Unknown',
        http_banners={80: {'server': 'httpd', 'title': 'Tapo Camera Login'}},
    )
    assert label == 'TP-Link Tapo'
