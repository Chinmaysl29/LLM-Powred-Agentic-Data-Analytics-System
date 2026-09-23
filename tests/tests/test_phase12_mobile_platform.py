"""
Phase 12.8 — Mobile Platform Tests
Validates:
1. 12.8.1 Mobile Architecture (App Startup, API Connectivity, State Management Schema)
2. 12.8.2 Mobile Authentication (Login, Logout, Token Refresh, Biometrics)
3. 12.8.3 Mobile Dashboard (Rendering, KPI Loading, Decimated Chart Rendering)
4. 12.8.4 Mobile AI Chat (Chat Request/Response, Voice Query, Streaming)
5. 12.8.5 Mobile Reports (Open Report, Share Report, Download Report, Multi-format)
6. 12.8.6 Mobile Forecasting (Load Forecast, Compare Scenarios, Alert Generation)
7. 12.8.7 Mobile Notifications (Push Delivery APNs/FCM, Notification Read, History)
8. 12.8.8 Mobile Offline Sync Engine (Offline Access, Sync Operation, Conflict Handling)
9. 12.8.9 Mobile Analytics (Event Tracking, Metrics Collection, Performance Monitoring, Crashes)
10. 12.8.10 Mobile Integration Certification Report
"""

import json
import pytest
from backend.mobile.architecture import (
    MobileArchitectureManager,
    MobileAppConfig,
    MobileDeviceProfile,
    MobileOS,
    DeviceType,
)
from backend.mobile.auth import MobileAuthManager
from backend.mobile.dashboard import MobileDashboardService
from backend.mobile.chat import MobileAIChatService
from backend.mobile.reports import MobileReportsService
from backend.mobile.forecasting import MobileForecastingService
from backend.mobile.notifications import MobileNotificationService
from backend.mobile.offline_sync import OfflineSyncEngine, ConflictStrategy
from backend.mobile.analytics import MobileAnalyticsEngine


def test_12_8_1_mobile_architecture_startup():
    """Test mobile app startup, device profile registration, API connectivity, and state contracts."""
    arch = MobileArchitectureManager(
        config=MobileAppConfig(app_version="2.4.0", environment="staging")
    )

    # 1. Device Registration (Phone)
    phone_profile = MobileDeviceProfile(
        device_id="iphone-15-pro-max",
        os=MobileOS.IOS,
        os_version="17.4",
        device_type=DeviceType.PHONE,
        screen_width=430,
        screen_height=932
    )
    reg_phone = arch.register_device(phone_profile)
    assert reg_phone["registered"] is True
    assert reg_phone["is_tablet"] is False

    # 2. Device Registration (Tablet)
    tablet_profile = MobileDeviceProfile(
        device_id="ipad-pro-12",
        os=MobileOS.IOS,
        os_version="17.4",
        device_type=DeviceType.TABLET,
        screen_width=1024,
        screen_height=1366
    )
    reg_tablet = arch.register_device(tablet_profile)
    assert reg_tablet["is_tablet"] is True

    # 3. API Connectivity Check
    conn = arch.check_api_connectivity("/api/v1/health")
    assert conn["status"] == "connected"
    assert conn["latency_ms"] > 0

    # 4. State Management Contract
    schema = arch.get_state_management_schema()
    assert "auth" in schema["slices"]
    assert "dashboard" in schema["slices"]
    assert "offlineSync" in schema["slices"]


def test_12_8_2_mobile_authentication():
    """Test mobile login, token refresh, biometric enrollment, and session logout."""
    auth = MobileAuthManager(access_token_ttl_sec=300)

    # 1. Login
    login_res = auth.login(
        username="executive@analystos.com",
        password="ValidPassword123!",
        device_id="device-ios-99"
    )
    assert login_res["success"] is True
    session_id = login_res["session_id"]
    access_token = login_res["access_token"]
    refresh_token = login_res["refresh_token"]
    assert access_token.startswith("jwt-access-")
    assert refresh_token.startswith("jwt-refresh-")

    # 2. Token Refresh
    refresh_res = auth.refresh_access_token(refresh_token)
    assert refresh_res["success"] is True
    new_access = refresh_res["access_token"]
    new_refresh = refresh_res["refresh_token"]
    assert new_access != access_token
    assert new_refresh != refresh_token

    # 3. Biometric Authentication
    enrolled = auth.enroll_biometrics(session_id, "mock-pubkey-faceid-777")
    assert enrolled is True
    bio_res = auth.authenticate_biometric(session_id, "mock-signature-payload")
    assert bio_res["success"] is True

    # 4. Logout
    logout_ok = auth.logout(session_id)
    assert logout_ok is True
    assert auth.get_session(session_id).is_active is False

    # Refresh after logout should fail
    bad_refresh = auth.refresh_access_token(new_refresh)
    assert bad_refresh["success"] is False


def test_12_8_3_mobile_dashboard():
    """Test dashboard rendering, responsive phone vs tablet layout, KPI loading, and chart decimation."""
    dashboard = MobileDashboardService()

    # 1. Phone Dashboard
    phone_dash = dashboard.get_dashboard(tenant_id="tenant-acme", is_tablet=False, max_chart_points=30)
    assert phone_dash.layout_type == "phone_stack"
    assert len(phone_dash.kpis) == 4
    assert any(k.title == "Monthly Recurring Revenue" for k in phone_dash.kpis)
    assert len(phone_dash.charts) >= 1

    chart = phone_dash.charts[0]
    assert chart.decimated is True
    assert len(chart.points) == 30
    assert chart.total_data_points == 300

    # 2. Tablet Dashboard
    tablet_dash = dashboard.get_dashboard(tenant_id="tenant-acme", is_tablet=True, max_chart_points=100)
    assert tablet_dash.layout_type == "tablet_grid"
    assert len(tablet_dash.charts[0].points) == 100

    # 3. Alert Ribbon & Forecast Highlight
    assert len(phone_dash.alerts) >= 1
    assert phone_dash.forecast_summary["status"] == "on_track"


def test_12_8_4_mobile_ai_chat():
    """Test mobile AI chat querying, voice query processing, streaming tokens, and history."""
    chat = MobileAIChatService()
    thread = chat.create_thread(tenant_id="tenant-acme", user_id="usr-exec-1")

    # 1. Text Query
    post_res = chat.post_message(
        thread_id=thread.thread_id,
        user_id="usr-exec-1",
        text="What is our revenue trend in EMEA?"
    )
    assert "EMEA" in post_res["assistant_message"]["content"]
    assert post_res["assistant_message"]["role"] == "assistant"

    # 2. Voice Query
    voice_res = chat.process_voice_query(
        thread_id=thread.thread_id,
        user_id="usr-exec-1",
        audio_bytes=b"VOICE_M4A_SAMPLES",
        audio_format="m4a"
    )
    assert voice_res["user_message"]["is_voice"] is True
    assert "transcription" in voice_res

    # 3. Streaming Response Chunks
    sample_text = "The churn rate is stable at 1.45 percent this month."
    chunks = list(chat.stream_response(sample_text))
    reconstructed = "".join(chunks).strip()
    assert reconstructed == sample_text

    # 4. History
    history = chat.get_history(thread.thread_id)
    assert len(history) >= 4


def test_12_8_5_mobile_reports():
    """Test mobile report opening, PDF/Excel/PPT previewing, deep link sharing, and downloading."""
    reports_svc = MobileReportsService()

    # 1. List Reports
    items = reports_svc.list_reports()
    assert len(items) >= 3

    # 2. Open Report
    pdf_open = reports_svc.open_report("rep-pdf-q3")
    assert pdf_open is not None
    assert pdf_open["viewer_type"] == "mobile_pdf_viewer"
    assert pdf_open["report"]["preview_data"]["page_count"] == 14

    # 3. Share Report
    share_res = reports_svc.share_report("rep-pdf-q3", share_target="slack")
    assert share_res["success"] is True
    assert share_res["deep_link"].startswith("analystos://reports/")

    # 4. Download Report
    down_res = reports_svc.download_report("rep-xls-sales")
    assert down_res["success"] is True
    assert down_res["filename"].endswith(".excel")
    assert down_res["cacheable"] is True


def test_12_8_6_mobile_forecasting():
    """Test mobile forecast curves, scenario comparisons (Base vs Optimistic vs Conservative), and alerts."""
    fcst_svc = MobileForecastingService()

    # 1. Load Forecast
    model = fcst_svc.load_forecast("Gross Revenue", horizon_days=90)
    assert model.metric == "Gross Revenue"
    assert "base" in model.scenarios
    assert "optimistic" in model.scenarios
    assert "conservative" in model.scenarios
    assert len(model.scenarios["base"].trajectory_points) == 10

    # 2. Compare Scenarios
    comp = fcst_svc.compare_scenarios(model)
    assert comp["comparison"]["optimistic"]["projected"] > comp["comparison"]["base"]["projected"]
    assert comp["comparison"]["base"]["projected"] > comp["comparison"]["conservative"]["projected"]

    # 3. Alert Generation
    alerts = fcst_svc.generate_alerts(
        metric="Gross Revenue",
        scenario=model.scenarios["conservative"],
        target_threshold=1500000.0
    )
    assert len(alerts) >= 1
    assert alerts[0]["severity"] == "critical"


def test_12_8_7_mobile_notifications():
    """Test push notification delivery (iOS APNs & Android FCM), read status, and history."""
    notif_svc = MobileNotificationService()

    # 1. iOS Push Delivery
    ios_delivery = notif_svc.send_push_notification(
        tenant_id="tenant-acme",
        user_id="usr-exec-1",
        title="Critical Anomaly Detected",
        body="Conversion rate dropped 12% in EU region",
        category="risk_alert",
        target_os="ios"
    )
    assert ios_delivery["delivered"] is True
    assert "aps" in ios_delivery["transport_payload"]
    notif_id = ios_delivery["notification_id"]

    # 2. Android Push Delivery
    android_delivery = notif_svc.send_push_notification(
        tenant_id="tenant-acme",
        user_id="usr-exec-1",
        title="Weekly Forecast Ready",
        body="Q4 Forecast exceeds target by 8%",
        category="forecast_alert",
        target_os="android"
    )
    assert android_delivery["delivered"] is True
    assert "android" in android_delivery["transport_payload"]

    # 3. Notification History & Read Status
    history = notif_svc.get_notification_history("usr-exec-1", unread_only=True)
    assert len(history) == 2

    # Mark Read
    marked = notif_svc.mark_as_read(notif_id)
    assert marked is True
    unread_history = notif_svc.get_notification_history("usr-exec-1", unread_only=True)
    assert len(unread_history) == 1


def test_12_8_8_mobile_offline_sync():
    """Test offline cache seeding, queuing changes offline, and multi-strategy conflict resolution."""
    sync_engine = OfflineSyncEngine(default_strategy=ConflictStrategy.LAST_WRITE_WINS)

    # 1. Offline Access
    seeded = sync_engine.seed_offline_cache(tenant_id="tenant-1", workspace_id="ws-1")
    assert seeded["offline_storage_kb"] > 0
    cached = sync_engine.get_offline_cache(tenant_id="tenant-1", workspace_id="ws-1")
    assert cached is not None
    assert len(cached["dashboard"]["kpis"]) == 2

    # 2. Enqueue Offline Changes
    q1 = sync_engine.enqueue_client_change(
        entity_type="comment",
        entity_id="comment-101",
        action="create",
        client_payload={"text": "Review requested by CFO"},
        client_timestamp=100.0
    )
    assert q1.sync_status == "pending"

    # 3. Sync Operation (No conflict)
    sync_res = sync_engine.sync_pending_changes()
    assert sync_res["success"] is True
    assert sync_res["synced_count"] == 1
    server_comment = sync_engine.get_server_entity("comment-101")
    assert server_comment["text"] == "Review requested by CFO"

    # 4. Conflict Handling (Last-Write-Wins vs Server-Wins)
    # Enqueue concurrent change with newer client timestamp
    sync_engine.enqueue_client_change(
        entity_type="comment",
        entity_id="comment-101",
        action="update",
        client_payload={"text": "CFO approved changes"},
        client_timestamp=200.0
    )
    conflict_res = sync_engine.sync_pending_changes(strategy=ConflictStrategy.LAST_WRITE_WINS)
    assert conflict_res["conflicts_resolved"] == 1
    updated_comment = sync_engine.get_server_entity("comment-101")
    assert updated_comment["text"] == "CFO approved changes"
    assert updated_comment["conflict_winner"] == "client"


def test_12_8_9_mobile_analytics():
    """Test mobile event tracking, telemetry metrics collection, session duration, and crash reporting."""
    analytics = MobileAnalyticsEngine()

    # 1. Event Tracking
    ev1 = analytics.track_event(
        session_id="sess-01",
        user_id="usr-exec-1",
        event_name="screen_view",
        properties={"screen": "ExecutiveDashboard"}
    )
    assert ev1.event_name == "screen_view"

    ev2 = analytics.track_event(
        session_id="sess-01",
        user_id="usr-exec-1",
        event_name="voice_query",
        properties={"audio_duration_sec": 3.4}
    )
    assert ev2.event_name == "voice_query"

    # 2. Performance Metrics
    metric = analytics.record_performance_metric(
        metric_name="chart_render_latency_ms",
        value=16.8,
        unit="ms",
        device_id="iphone-15"
    )
    assert metric.value == 16.8

    # 3. Session Duration
    analytics.record_session_duration("sess-01", 340.5)

    # 4. Crash Reporting
    crash = analytics.log_crash(
        session_id="sess-01",
        user_id="usr-exec-1",
        os_version="iOS 17.4",
        exception_type="MemoryWarningException",
        stack_trace="Thread 1: Fatal exception at line 42"
    )
    assert crash.exception_type == "MemoryWarningException"

    summary = analytics.get_summary()
    assert summary["total_events"] == 2
    assert summary["feature_usage"]["screen_view"] == 1
    assert summary["total_crashes"] == 1


def test_12_8_10_mobile_full_integration_certification():
    """
    Validate 100% Mobile Platform certification report matching required format:
    {
      "authentication": true,
      "dashboard": true,
      "chat": true,
      "reports": true,
      "forecasting": true,
      "notifications": true,
      "offline_sync": true
    }
    """
    # 1. Authentication
    auth = MobileAuthManager()
    l = auth.login("user@analystos.com", "secret", "dev-1")
    auth_ok = l["success"] is True and bool(l["access_token"])

    # 2. Dashboard
    dash = MobileDashboardService()
    d = dash.get_dashboard("tenant-1")
    dash_ok = len(d.kpis) > 0 and len(d.charts) > 0

    # 3. Chat
    chat = MobileAIChatService()
    t = chat.create_thread("tenant-1", "user-1")
    c = chat.post_message(t.thread_id, "user-1", "Analyze sales")
    chat_ok = bool(c["assistant_message"]["content"])

    # 4. Reports
    reports_svc = MobileReportsService()
    rep = reports_svc.open_report("rep-pdf-q3")
    rep_ok = rep is not None and rep["viewer_type"] == "mobile_pdf_viewer"

    # 5. Forecasting
    fcst_svc = MobileForecastingService()
    f = fcst_svc.load_forecast("ARR")
    fcst_ok = len(f.scenarios) >= 3

    # 6. Notifications
    notif_svc = MobileNotificationService()
    n = notif_svc.send_push_notification("tenant-1", "user-1", "Title", "Body")
    notif_ok = n["delivered"] is True

    # 7. Offline Sync
    sync_engine = OfflineSyncEngine()
    s = sync_engine.seed_offline_cache("tenant-1", "ws-1")
    offline_ok = s["offline_storage_kb"] > 0

    report = {
        "authentication": auth_ok,
        "dashboard": dash_ok,
        "chat": chat_ok,
        "reports": rep_ok,
        "forecasting": fcst_ok,
        "notifications": notif_ok,
        "offline_sync": offline_ok,
    }

    print("\nMOBILE PLATFORM CERTIFICATION REPORT:")
    print(json.dumps(report, indent=2))

    for key, status in report.items():
        assert status is True, f"Certification failed for: {key}"
