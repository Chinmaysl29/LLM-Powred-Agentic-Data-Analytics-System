"""
Phase 15.1 — Business Knowledge Graph
Connects every business entity (KPIs, Datasets, Departments, Agents, Decisions,
Reports, Teams, Connectors) into a living semantic web of relationships.
"""

from __future__ import annotations

import uuid
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timezone
from pydantic import BaseModel, Field

logger = logging.getLogger("backend.autonomous.knowledge_graph")


# ---------------------------------------------------------------------------
# Node & Edge Schemas
# ---------------------------------------------------------------------------

class NodeType(str, Enum):
    DATASET    = "dataset"
    KPI        = "kpi"
    DEPARTMENT = "department"
    AGENT      = "agent"
    DECISION   = "decision"
    REPORT     = "report"
    TEAM       = "team"
    CONNECTOR  = "connector"
    WORKFLOW   = "workflow"
    METRIC     = "metric"


class EdgeType(str, Enum):
    FEEDS_INTO      = "feeds_into"
    OWNED_BY        = "owned_by"
    CORRELATED_WITH = "correlated_with"
    DEPENDS_ON      = "depends_on"
    GENERATES       = "generates"
    MONITORS        = "monitors"
    BELONGS_TO      = "belongs_to"
    INFORMED_BY     = "informed_by"
    EXECUTES        = "executes"
    TRIGGERS        = "triggers"


class KnowledgeNode(BaseModel):
    node_id:     str       = Field(default_factory=lambda: str(uuid.uuid4()))
    name:        str
    node_type:   NodeType
    properties:  Dict[str, Any] = Field(default_factory=dict)
    tags:        List[str]      = Field(default_factory=list)
    created_at:  str            = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class KnowledgeEdge(BaseModel):
    edge_id:    str     = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id:  str
    target_id:  str
    edge_type:  EdgeType
    weight:     float   = 1.0
    metadata:   Dict[str, Any] = Field(default_factory=dict)


class SubgraphResult(BaseModel):
    root_node:   KnowledgeNode
    neighbours:  List[KnowledgeNode]
    edges:       List[KnowledgeEdge]
    depth:       int


# ---------------------------------------------------------------------------
# Business Knowledge Graph
# ---------------------------------------------------------------------------

class BusinessKnowledgeGraph:
    """
    In-memory directed semantic graph representing the entire business knowledge
    landscape.  Uses adjacency lists for O(1) neighbourhood lookups.
    """

    def __init__(self) -> None:
        self._nodes:     Dict[str, KnowledgeNode] = {}       # node_id → node
        self._edges:     Dict[str, KnowledgeEdge] = {}       # edge_id → edge
        self._adj:       Dict[str, List[str]]     = {}       # node_id → [edge_id]
        self._rev_adj:   Dict[str, List[str]]     = {}       # node_id → [edge_id] (in-bound)
        self._name_idx:  Dict[str, str]           = {}       # name   → node_id
        logger.info("BusinessKnowledgeGraph initialised.")

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_node(self, node: KnowledgeNode) -> KnowledgeNode:
        """Register a knowledge node."""
        self._nodes[node.node_id]     = node
        self._adj[node.node_id]       = []
        self._rev_adj[node.node_id]   = []
        self._name_idx[node.name]     = node.node_id
        logger.debug("Node added: %s (%s)", node.name, node.node_type)
        return node

    def add_edge(self, edge: KnowledgeEdge) -> KnowledgeEdge:
        """Register a directed edge; both endpoints must exist."""
        if edge.source_id not in self._nodes or edge.target_id not in self._nodes:
            raise ValueError(
                f"Edge endpoints not found: {edge.source_id} → {edge.target_id}"
            )
        self._edges[edge.edge_id] = edge
        self._adj[edge.source_id].append(edge.edge_id)
        self._rev_adj[edge.target_id].append(edge.edge_id)
        return edge

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        return self._nodes.get(node_id)

    def get_node_by_name(self, name: str) -> Optional[KnowledgeNode]:
        nid = self._name_idx.get(name)
        return self._nodes.get(nid) if nid else None

    def find_nodes_by_type(self, node_type: NodeType) -> List[KnowledgeNode]:
        return [n for n in self._nodes.values() if n.node_type == node_type]

    def find_related_entities(
        self,
        node_id:   str,
        edge_type: Optional[EdgeType] = None,
        direction: str = "out",          # "out" | "in" | "both"
    ) -> List[KnowledgeNode]:
        """Return all entities directly connected to a node."""
        results: List[KnowledgeNode] = []
        edge_ids: Set[str] = set()

        if direction in ("out", "both"):
            edge_ids.update(self._adj.get(node_id, []))
        if direction in ("in", "both"):
            edge_ids.update(self._rev_adj.get(node_id, []))

        for eid in edge_ids:
            edge = self._edges[eid]
            if edge_type and edge.edge_type != edge_type:
                continue
            other_id = edge.target_id if edge.source_id == node_id else edge.source_id
            node = self._nodes.get(other_id)
            if node:
                results.append(node)
        return results

    def query_subgraph(
        self,
        root_id: str,
        depth:   int = 2,
    ) -> SubgraphResult:
        """BFS subgraph traversal up to a given depth."""
        if root_id not in self._nodes:
            raise ValueError(f"Root node not found: {root_id}")

        visited_nodes: Set[str]  = {root_id}
        frontier:      List[str] = [root_id]
        collected_edges: List[KnowledgeEdge] = []

        for _ in range(depth):
            next_frontier: List[str] = []
            for nid in frontier:
                for eid in self._adj.get(nid, []):
                    edge = self._edges[eid]
                    collected_edges.append(edge)
                    if edge.target_id not in visited_nodes:
                        visited_nodes.add(edge.target_id)
                        next_frontier.append(edge.target_id)
            frontier = next_frontier

        neighbours = [self._nodes[nid] for nid in visited_nodes if nid != root_id]
        return SubgraphResult(
            root_node=self._nodes[root_id],
            neighbours=neighbours,
            edges=collected_edges,
            depth=depth,
        )

    def get_kpi_dependencies(self, kpi_name: str) -> List[KnowledgeNode]:
        """Trace which datasets and metrics drive a given KPI."""
        kpi_node = self.get_node_by_name(kpi_name)
        if not kpi_node:
            return []
        return self.find_related_entities(
            kpi_node.node_id, edge_type=EdgeType.FEEDS_INTO, direction="in"
        )

    def get_department_relationships(self, dept_name: str) -> Dict[str, List[KnowledgeNode]]:
        """Return all inbound and outbound relationships for a department node."""
        dept_node = self.get_node_by_name(dept_name)
        if not dept_node:
            return {"inbound": [], "outbound": []}
        return {
            "inbound":  self.find_related_entities(dept_node.node_id, direction="in"),
            "outbound": self.find_related_entities(dept_node.node_id, direction="out"),
        }

    def find_cross_system_relationships(self) -> List[Dict[str, Any]]:
        """Identify edges that cross NodeType boundaries (cross-system links)."""
        cross_system = []
        for edge in self._edges.values():
            src  = self._nodes.get(edge.source_id)
            tgt  = self._nodes.get(edge.target_id)
            if src and tgt and src.node_type != tgt.node_type:
                cross_system.append({
                    "from_entity": src.name,
                    "from_type":   src.node_type,
                    "to_entity":   tgt.name,
                    "to_type":     tgt.node_type,
                    "relationship": edge.edge_type,
                })
        return cross_system

    # ------------------------------------------------------------------
    # Export / Stats
    # ------------------------------------------------------------------

    def export_schema(self) -> Dict[str, Any]:
        """Serialisable snapshot of the entire graph."""
        return {
            "nodes": [n.model_dump() for n in self._nodes.values()],
            "edges": [e.model_dump() for e in self._edges.values()],
            "stats": self.get_stats(),
        }

    def get_stats(self) -> Dict[str, Any]:
        type_counts: Dict[str, int] = {}
        for node in self._nodes.values():
            type_counts[node.node_type] = type_counts.get(node.node_type, 0) + 1

        edge_counts: Dict[str, int] = {}
        for edge in self._edges.values():
            edge_counts[edge.edge_type] = edge_counts.get(edge.edge_type, 0) + 1

        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "node_type_distribution": type_counts,
            "edge_type_distribution": edge_counts,
        }

    def build_default_enterprise_graph(self) -> None:
        """
        Seed a representative enterprise knowledge graph with canonical
        departments, KPIs, datasets, agents, and connectors.
        """
        # --- Departments ---
        finance   = self.add_node(KnowledgeNode(name="Finance",       node_type=NodeType.DEPARTMENT))
        sales     = self.add_node(KnowledgeNode(name="Sales",         node_type=NodeType.DEPARTMENT))
        marketing = self.add_node(KnowledgeNode(name="Marketing",     node_type=NodeType.DEPARTMENT))
        hr        = self.add_node(KnowledgeNode(name="HR",            node_type=NodeType.DEPARTMENT))
        ops       = self.add_node(KnowledgeNode(name="Operations",    node_type=NodeType.DEPARTMENT))

        # --- KPIs ---
        revenue    = self.add_node(KnowledgeNode(name="Revenue",          node_type=NodeType.KPI))
        ebitda     = self.add_node(KnowledgeNode(name="EBITDA",           node_type=NodeType.KPI))
        churn      = self.add_node(KnowledgeNode(name="Churn Rate",       node_type=NodeType.KPI))
        cac        = self.add_node(KnowledgeNode(name="CAC",              node_type=NodeType.KPI))
        headcount  = self.add_node(KnowledgeNode(name="Headcount",        node_type=NodeType.KPI))

        # --- Datasets ---
        crm_ds     = self.add_node(KnowledgeNode(name="CRM Dataset",      node_type=NodeType.DATASET))
        finance_ds = self.add_node(KnowledgeNode(name="Finance Dataset",  node_type=NodeType.DATASET))
        hr_ds      = self.add_node(KnowledgeNode(name="HR Dataset",       node_type=NodeType.DATASET))

        # --- Agents ---
        fin_agent  = self.add_node(KnowledgeNode(name="Finance Agent",    node_type=NodeType.AGENT))
        sales_agent= self.add_node(KnowledgeNode(name="Sales Agent",      node_type=NodeType.AGENT))
        hr_agent   = self.add_node(KnowledgeNode(name="HR Agent",         node_type=NodeType.AGENT))

        # --- Connectors ---
        salesforce = self.add_node(KnowledgeNode(name="Salesforce",       node_type=NodeType.CONNECTOR))
        snowflake  = self.add_node(KnowledgeNode(name="Snowflake",        node_type=NodeType.CONNECTOR))

        # --- Edges ---
        edges = [
            # Datasets → KPIs
            KnowledgeEdge(source_id=crm_ds.node_id,     target_id=revenue.node_id,   edge_type=EdgeType.FEEDS_INTO),
            KnowledgeEdge(source_id=crm_ds.node_id,     target_id=churn.node_id,     edge_type=EdgeType.FEEDS_INTO),
            KnowledgeEdge(source_id=finance_ds.node_id, target_id=ebitda.node_id,    edge_type=EdgeType.FEEDS_INTO),
            KnowledgeEdge(source_id=finance_ds.node_id, target_id=revenue.node_id,   edge_type=EdgeType.FEEDS_INTO),
            KnowledgeEdge(source_id=hr_ds.node_id,      target_id=headcount.node_id, edge_type=EdgeType.FEEDS_INTO),
            # Agents → Datasets
            KnowledgeEdge(source_id=fin_agent.node_id,  target_id=finance_ds.node_id, edge_type=EdgeType.MONITORS),
            KnowledgeEdge(source_id=sales_agent.node_id,target_id=crm_ds.node_id,    edge_type=EdgeType.MONITORS),
            KnowledgeEdge(source_id=hr_agent.node_id,   target_id=hr_ds.node_id,     edge_type=EdgeType.MONITORS),
            # Departments → KPIs
            KnowledgeEdge(source_id=finance.node_id,    target_id=ebitda.node_id,    edge_type=EdgeType.OWNED_BY),
            KnowledgeEdge(source_id=sales.node_id,      target_id=revenue.node_id,   edge_type=EdgeType.OWNED_BY),
            KnowledgeEdge(source_id=marketing.node_id,  target_id=cac.node_id,       edge_type=EdgeType.OWNED_BY),
            KnowledgeEdge(source_id=hr.node_id,         target_id=headcount.node_id, edge_type=EdgeType.OWNED_BY),
            # Connectors → Datasets
            KnowledgeEdge(source_id=salesforce.node_id, target_id=crm_ds.node_id,   edge_type=EdgeType.FEEDS_INTO),
            KnowledgeEdge(source_id=snowflake.node_id,  target_id=finance_ds.node_id,edge_type=EdgeType.FEEDS_INTO),
            # Cross-dept correlations
            KnowledgeEdge(source_id=marketing.node_id,  target_id=sales.node_id,    edge_type=EdgeType.CORRELATED_WITH),
            KnowledgeEdge(source_id=revenue.node_id,    target_id=ebitda.node_id,   edge_type=EdgeType.CORRELATED_WITH),
        ]
        for edge in edges:
            self.add_edge(edge)

        logger.info(
            "Default enterprise graph seeded: %d nodes, %d edges.",
            len(self._nodes), len(self._edges),
        )
