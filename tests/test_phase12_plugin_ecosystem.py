"""
Phase 12.10 — Plugin & Extension Ecosystem Tests
Validates:
1. 12.10.1 Plugin Framework (Load, Unload, Version Compatibility)
2. 12.10.2 Plugin Registry (Register, Activate, Disable)
3. 12.10.3 Agent Plugin SDK (Create Custom Agent, Execute, Validate Output)
4. 12.10.4 Connector Plugin SDK (Create Connector, Execute Query, Validate)
5. 12.10.5 Workflow Plugin SDK (Register Workflow, Execute Chain, Validate State)
6. 12.10.6 Dashboard Plugin SDK (Register Widget, Render Payload, Layout Spec)
7. 12.10.7 Marketplace Engine (Publish, Search, Install, Upgrade, Rate)
8. 12.10.8 Plugin Sandbox (Isolation, Resource Guard, Static Security Filter)
9. 12.10.9 Plugin Monitoring (Invocation Metrics, Latencies, Error Budgets)
10. 12.10.10 Full Ecosystem Certification Report
"""

import json
import pytest
from backend.plugins.framework import PluginFramework, PluginMetadata, PluginState
from backend.plugins.registry import PluginRegistry
from backend.plugins.agent_sdk import BaseAgentPlugin, AgentPluginResult
from backend.plugins.connector_sdk import BaseConnectorPlugin, ConnectorQueryResult
from backend.plugins.workflow_sdk import BaseWorkflowPlugin, WorkflowExecutionResult
from backend.plugins.dashboard_sdk import BaseDashboardWidgetPlugin, DashboardWidgetRender
from backend.plugins.marketplace import MarketplaceEngine
from backend.plugins.sandbox import PluginSandbox, SandboxPermissions
from backend.plugins.monitoring import PluginMonitoringEngine


def test_12_10_1_plugin_framework():
    """Test dynamic plugin loading, version compatibility checks, and unloading."""
    fw = PluginFramework()

    # 1. Valid Plugin Load
    meta_valid = PluginMetadata(
        plugin_id="plg-risk-evaluator",
        plugin_name="Enterprise Risk Evaluator",
        plugin_type="agent",
        version="1.2.0",
        min_platform_version="2.0.0"
    )
    loaded = fw.load_plugin(meta_valid)
    assert loaded is True
    assert fw.get_plugin_state(meta_valid.plugin_id) == PluginState.LOADED

    # 2. Version Incompatible Plugin Load
    meta_incompat = PluginMetadata(
        plugin_id="plg-future-tool",
        plugin_name="Future AI Platform Engine",
        plugin_type="agent",
        version="3.0.0",
        min_platform_version="3.5.0" # Platform is 2.4.0
    )
    loaded_incompat = fw.load_plugin(meta_incompat)
    assert loaded_incompat is False
    assert fw.get_plugin_state(meta_incompat.plugin_id) == PluginState.ERROR

    # 3. Activation & Unload
    assert fw.activate_plugin(meta_valid.plugin_id) is True
    assert fw.get_plugin_state(meta_valid.plugin_id) == PluginState.ACTIVE

    assert fw.unload_plugin(meta_valid.plugin_id) is True
    assert fw.get_plugin_state(meta_valid.plugin_id) == PluginState.UNLOADED


def test_12_10_2_plugin_registry():
    """Test plugin registration, status tracking, activation, and deactivation."""
    reg = PluginRegistry()

    # 1. Register
    record = reg.register_plugin(
        plugin_name="Postgres Timescale Connector",
        plugin_type="connector",
        version="2.1.0",
        author="Database Core Team"
    )
    assert record.plugin_id.startswith("plg-")
    assert record.status == "active"

    # 2. Disable
    disabled = reg.disable_plugin(record.plugin_id)
    assert disabled is True
    assert reg.get_plugin(record.plugin_id).status == "disabled"

    # 3. Re-activate
    activated = reg.activate_plugin(record.plugin_id)
    assert activated is True
    assert reg.get_plugin(record.plugin_id).status == "active"

    # 4. List by type
    connectors = reg.list_plugins(plugin_type="connector")
    assert len(connectors) == 1


def test_12_10_3_agent_plugin_sdk():
    """Test authoring, initializing, executing, and validating a custom agent plugin."""
    class CustomHealthcareAgent(BaseAgentPlugin):
        def analyze(self, dataset, query):
            return AgentPluginResult(
                agent_id=self.agent_id,
                insights=["Readmission rate decreased by 4.2% following protocol update."],
                recommendations=["Scale preventive telehealth outreach across clinical cohort."],
                metrics={"cohort_size": len(dataset), "delta_pct": -4.2},
                confidence=0.98
            )

    agent = CustomHealthcareAgent(
        agent_id="agent-clinical-analytics",
        name="Clinical Readmission Agent",
        domain="healthcare"
    )
    assert agent.initialize() is True

    sample_dataset = [{"patient_id": i, "readmitted": False} for i in range(50)]
    result = agent.analyze(sample_dataset, "Analyze 30-day readmissions")

    assert len(result.insights) == 1
    assert result.confidence == 0.98
    assert agent.validate_output(result) is True


def test_12_10_4_connector_plugin_sdk():
    """Test authoring, validating, and querying a custom connector plugin."""
    class CustomCassandraConnector(BaseConnectorPlugin):
        def connect(self, credentials):
            self.is_connected = True
            return True

        def validate_connection(self):
            return self.is_connected

        def execute_query(self, query, parameters=None):
            return ConnectorQueryResult(
                connector_id=self.connector_id,
                rows=[{"sensor_id": "temp-01", "reading": 24.5}, {"sensor_id": "temp-02", "reading": 25.1}],
                total_records=2,
                schema_fields=["sensor_id", "reading"],
                query_latency_ms=14.2
            )

    conn = CustomCassandraConnector("conn-iot-cassandra", "IoT Sensor Cassandra")
    assert conn.connect({"host": "10.0.0.1", "keyspace": "telemetry"}) is True
    assert conn.validate_connection() is True

    res = conn.execute_query("SELECT * FROM telemetry.sensors")
    assert res.total_records == 2
    assert "reading" in res.schema_fields
    assert res.query_latency_ms > 0


def test_12_10_5_workflow_plugin_sdk():
    """Test registering and running a custom multi-step workflow plugin."""
    class AnomalyTriageWorkflow(BaseWorkflowPlugin):
        def __init__(self):
            super().__init__("wf-anomaly-triage", "Automated Anomaly Triage Pipeline")
            self.steps = ["detect_anomaly", "correlate_logs", "dispatch_jira_ticket"]

        def run(self, initial_state):
            state = dict(initial_state)
            state["anomaly_detected"] = True
            state["ticket_id"] = "DATA-1049"
            return WorkflowExecutionResult(
                workflow_id=self.workflow_id,
                status="COMPLETED",
                output_state=state,
                steps_executed=self.steps,
                execution_time_sec=0.45
            )

    wf = AnomalyTriageWorkflow()
    assert wf.validate_workflow() is True

    execution = wf.run({"metric": "error_rate", "value": 0.14})
    assert execution.status == "COMPLETED"
    assert execution.output_state["ticket_id"] == "DATA-1049"
    assert len(execution.steps_executed) == 3


def test_12_10_6_dashboard_plugin_sdk():
    """Test authoring and rendering a custom dashboard visualization widget."""
    class CustomFunnelWidget(BaseDashboardWidgetPlugin):
        def render(self, input_data):
            return DashboardWidgetRender(
                widget_id=self.widget_id,
                title=self.title,
                component_type="react_funnel_chart",
                rendered_payload={
                    "stages": ["Visits", "Signups", "Activations", "Paid"],
                    "counts": [10000, 2500, 1200, 450]
                },
                width_units=6
            )

    widget = CustomFunnelWidget("widget-funnel-01", "User Conversion Funnel")
    render_out = widget.render({"date_range": "30d"})
    assert render_out.width_units == 6
    assert len(render_out.rendered_payload["stages"]) == 4

    layout = widget.get_layout_spec()
    assert layout["resizable"] is True


def test_12_10_7_marketplace_engine():
    """Test marketplace publishing, discovery, tenant installation, upgrades, and reviews."""
    market = MarketplaceEngine()

    # 1. Publish
    item = market.publish_plugin(
        item_id="plg-inventory-optimizer",
        name="Supply Chain Inventory Optimizer",
        category="agents",
        version="1.0.0",
        author="Logistics AI Co",
        description="Optimizes warehouse safety stocks."
    )
    assert item.item_id == "plg-inventory-optimizer"

    # 2. Search
    found = market.search_plugins(query="inventory", category="agents")
    assert len(found) == 1
    assert found[0].name == "Supply Chain Inventory Optimizer"

    # 3. Install
    inst = market.install_plugin("tenant-walmart", "plg-inventory-optimizer")
    assert inst["success"] is True
    assert inst["installed_version"] == "1.0.0"

    # 4. Upgrade
    market.publish_plugin("plg-inventory-optimizer", "Supply Chain Inventory Optimizer", "agents", "1.1.0", "Logistics AI Co")
    upgrade_res = market.upgrade_plugin("tenant-walmart", "plg-inventory-optimizer")
    assert upgrade_res["success"] is True
    assert upgrade_res["new_version"] == "1.1.0"

    # 5. Rating
    assert market.add_rating("plg-inventory-optimizer", 5.0) is True
    assert item.average_rating == 5.0


def test_12_10_8_plugin_sandbox():
    """Test sandbox execution, timeout prevention, and static security validation."""
    sandbox = PluginSandbox(default_permissions=SandboxPermissions(timeout_sec=0.2))

    # 1. Safe Execution
    def safe_calc():
        return sum(i * 2 for i in range(1000))

    safe_res = sandbox.execute_sandboxed("plg-calc", safe_calc)
    assert safe_res["success"] is True
    assert safe_res["result"] == 999000

    # 2. Timeout Enforcement
    def slow_loop():
        import time
        time.sleep(0.3)
        return "done"

    slow_res = sandbox.execute_sandboxed("plg-slow", slow_loop)
    assert slow_res["success"] is False
    assert slow_res["timed_out"] is True

    # 3. Static Code Safety Inspection
    unsafe_code = "import os; os.system('rm -rf /')"
    scan_unsafe = sandbox.validate_code_safety(unsafe_code)
    assert scan_unsafe["is_safe"] is False
    assert "Forbidden pattern" in scan_unsafe["violation"]

    safe_code = "def process(data): return [x * 2 for x in data]"
    scan_safe = sandbox.validate_code_safety(safe_code)
    assert scan_safe["is_safe"] is True


def test_12_10_9_plugin_monitoring():
    """Test telemetry collection, execution latencies, and error budget tracking."""
    monitor = PluginMonitoringEngine()

    # Record 4 successful calls and 1 failure
    for lat in [12.0, 14.5, 11.8, 15.2]:
        monitor.record_invocation("plg-analytics-fast", latency_ms=lat, is_error=False)
    monitor.record_invocation("plg-analytics-fast", latency_ms=50.0, is_error=True)

    metrics = monitor.get_plugin_metrics("plg-analytics-fast")
    assert metrics["invocations"] == 5
    assert metrics["errors"] == 1
    assert metrics["error_rate"] == 0.2
    assert metrics["mean_latency_ms"] > 10.0

    summary = monitor.get_system_summary()
    assert summary["monitored_plugins"] == 1
    assert summary["total_invocations"] == 5


def test_12_10_10_ecosystem_certification():
    """
    Validate 100% Plugin & Extension Ecosystem certification report matching required format:
    {
      "plugin_framework": true,
      "plugin_registry": true,
      "agent_sdk": true,
      "connector_sdk": true,
      "workflow_sdk": true,
      "dashboard_sdk": true,
      "marketplace": true,
      "sandbox": true,
      "monitoring": true
    }
    """
    # 1. Framework
    fw = PluginFramework()
    fw_ok = fw.check_version_compatibility("2.0.0", "2.4.0")

    # 2. Registry
    reg = PluginRegistry()
    r = reg.register_plugin("Test", "agent")
    reg_ok = r is not None and reg.count() == 1

    # 3. Agent SDK
    class MockAgent(BaseAgentPlugin):
        def analyze(self, dataset, query):
            return AgentPluginResult(agent_id=self.agent_id, insights=["Test"], recommendations=[])

    a = MockAgent("a1", "Test", "general")
    agent_ok = a.initialize() is True

    # 4. Connector SDK
    class MockConn(BaseConnectorPlugin):
        def connect(self, creds): return True
        def validate_connection(self): return True
        def execute_query(self, q, p=None):
            return ConnectorQueryResult(connector_id=self.connector_id, rows=[], total_records=0, schema_fields=[], query_latency_ms=1.0)

    c = MockConn("c1", "Test")
    connector_ok = c.connect({}) is True

    # 5. Workflow SDK
    class MockWf(BaseWorkflowPlugin):
        def run(self, s):
            return WorkflowExecutionResult(workflow_id=self.workflow_id, status="COMPLETED", output_state=s, steps_executed=["step1"], execution_time_sec=0.1)

    w = MockWf("w1", "Test")
    w.steps = ["step1"]
    wf_ok = w.validate_workflow() is True

    # 6. Dashboard SDK
    class MockDash(BaseDashboardWidgetPlugin):
        def render(self, d):
            return DashboardWidgetRender(widget_id=self.widget_id, title=self.title, component_type="test", rendered_payload={})

    d = MockDash("d1", "Test")
    dash_ok = d.render({}) is not None

    # 7. Marketplace
    m = MarketplaceEngine()
    item = m.publish_plugin("p1", "Test", "agents", "1.0.0", "Author")
    market_ok = item is not None and len(m.search_plugins("Test")) == 1

    # 8. Sandbox
    sb = PluginSandbox()
    sb_res = sb.execute_sandboxed("p1", lambda: 42)
    sandbox_ok = sb_res["success"] is True and sb_res["result"] == 42

    # 9. Monitoring
    mon = PluginMonitoringEngine()
    mon.record_invocation("p1", 10.0)
    mon_ok = mon.get_plugin_metrics("p1")["invocations"] == 1

    report = {
        "plugin_framework": fw_ok,
        "plugin_registry": reg_ok,
        "agent_sdk": agent_ok,
        "connector_sdk": connector_ok,
        "workflow_sdk": wf_ok,
        "dashboard_sdk": dash_ok,
        "marketplace": market_ok,
        "sandbox": sandbox_ok,
        "monitoring": mon_ok,
    }

    print("\nPLUGIN & EXTENSION ECOSYSTEM CERTIFICATION REPORT:")
    print(json.dumps(report, indent=2))

    for key, status in report.items():
        assert status is True, f"Certification failed for: {key}"
