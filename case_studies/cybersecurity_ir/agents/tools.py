"""
Simulated IR Toolkit (tools.py)
================================
Pre-recorded, deterministic tool outputs for the case study.
Each tool returns data drawn from CICIDS2017/UNSW-NB15 patterns
mapped to ATT&CK techniques.

Like the PoC's tools.py — no live network calls, fully reproducible.
"""

from __future__ import annotations

import json
from typing import Any


class IRToolkit:
    """
    Simulated incident-response toolkit.
    All outputs are pre-recorded per instance; tool calls are logged.
    """

    def __init__(self, instance_data: dict):
        """
        Args:
            instance_data: The loaded instance YAML containing
                           'tool_outputs' keyed by tool_name + args hash.
        """
        self.instance_data = instance_data
        self.tool_outputs = instance_data.get("tool_outputs", {})
        self.call_log: list[dict] = []
        self._call_count = 0

    @property
    def total_calls(self) -> int:
        return self._call_count

    def _record_call(self, tool_name: str, args: dict, result: Any) -> Any:
        self._call_count += 1
        self.call_log.append({
            "call_number": self._call_count,
            "tool": tool_name,
            "args": args,
            "result_summary": str(result)[:200],
        })
        return result

    def _get_output(self, key: str, default: Any = None) -> Any:
        return self.tool_outputs.get(key, default)

    # ── Network Flow Analysis ────────────────────────────────────────────

    def query_network_flows(
        self,
        time_range: str = "last_24h",
        src_ip: str | None = None,
        dst_ip: str | None = None,
        protocol: str | None = None,
        min_bytes: int = 0,
    ) -> dict:
        """Query network flow records (CICIDS-style)."""
        key = f"network_flows_{time_range}_{src_ip}_{dst_ip}"
        default = {
            "flows": [],
            "total_count": 0,
            "summary": "No flows found matching criteria",
        }
        result = self._get_output(key, default)
        return self._record_call("query_network_flows", {
            "time_range": time_range, "src_ip": src_ip,
            "dst_ip": dst_ip, "protocol": protocol,
        }, result)

    # ── Threat Intelligence Lookup ───────────────────────────────────────

    def lookup_ioc(
        self,
        ioc_type: str,  # ip | domain | hash | email
        value: str,
    ) -> dict:
        """Look up an IOC against threat intelligence feeds."""
        key = f"ioc_lookup_{ioc_type}_{value}"
        default = {
            "found": False,
            "type": ioc_type,
            "value": value,
            "threat_score": 0,
            "attributed_groups": [],
            "tags": [],
            "first_seen": None,
            "last_seen": None,
            "related_iocs": [],
        }
        result = self._get_output(key, default)
        return self._record_call("lookup_ioc", {
            "ioc_type": ioc_type, "value": value
        }, result)

    # ── Sigma Rule Matching ──────────────────────────────────────────────

    def get_sigma_matches(
        self,
        log_source: str,  # windows_security | sysmon | proxy | dns | ids
        timeframe: str = "last_24h",
        host: str | None = None,
    ) -> dict:
        """Match Sigma detection rules against log events."""
        key = f"sigma_matches_{log_source}_{host}"
        default = {
            "matches": [],
            "total_rules_checked": 0,
            "total_matches": 0,
        }
        result = self._get_output(key, default)
        return self._record_call("get_sigma_matches", {
            "log_source": log_source, "timeframe": timeframe, "host": host,
        }, result)

    # ── ATT&CK Technique Lookup ──────────────────────────────────────────

    def query_attck(self, technique_id: str) -> dict:
        """Look up ATT&CK technique metadata directly from official STIX knowledge base."""
        from data.attck_knowledge_base import TECHNIQUES
        tech = TECHNIQUES.get(technique_id)
        if tech:
            default = {
                "id": technique_id,
                "name": tech.get("name", "Unknown"),
                "tactic": tech.get("tactic", "unknown"),
                "tactics": tech.get("tactics", []),
                "description": tech.get("description", ""),
                "platforms": tech.get("platforms", []),
                "source": "official_mitre_stix_2.1",
            }
        else:
            default = {
                "id": technique_id,
                "name": "Unknown Technique",
                "tactic": "unknown",
                "description": "Not found in MITRE ATT&CK STIX database",
                "platforms": [],
            }
        key = f"attck_{technique_id}"
        result = self._get_output(key, default)
        return self._record_call("query_attck", {"technique_id": technique_id}, result)

    # ── Asset / Endpoint Status ──────────────────────────────────────────

    def check_asset_status(self, hostname: str) -> dict:
        """Check the current status of a network asset."""
        key = f"asset_status_{hostname}"
        default = {
            "hostname": hostname,
            "status": "unknown",
            "os": "unknown",
            "last_seen": None,
            "open_ports": [],
            "running_services": [],
            "logged_in_users": [],
            "alerts": [],
        }
        result = self._get_output(key, default)
        return self._record_call("check_asset_status", {"hostname": hostname}, result)

    # ── Memory Forensics ─────────────────────────────────────────────────

    def memory_forensics(self, hostname: str) -> dict:
        """Retrieve memory forensics results for a host."""
        key = f"memory_forensics_{hostname}"
        default = {
            "hostname": hostname,
            "status": "not_available",
            "processes": [],
            "network_connections": [],
            "loaded_dlls": [],
            "injected_code": [],
            "artifacts": [],
        }
        result = self._get_output(key, default)
        return self._record_call("memory_forensics", {"hostname": hostname}, result)

    # ── Network Topology ─────────────────────────────────────────────────

    def get_network_topology(self) -> dict:
        """Get the current network topology map."""
        key = "network_topology"
        default = {
            "segments": [],
            "hosts": {},
            "connections": [],
            "firewalls": [],
        }
        result = self._get_output(key, default)
        return self._record_call("get_network_topology", {}, result)

    # ── Log Analysis ─────────────────────────────────────────────────────

    def query_logs(
        self,
        log_type: str,  # auth | dns | proxy | firewall | endpoint
        hostname: str | None = None,
        timeframe: str = "last_24h",
        search_query: str | None = None,
    ) -> dict:
        """Query specific log sources."""
        key = f"logs_{log_type}_{hostname}_{search_query}"
        default = {
            "entries": [],
            "total_count": 0,
            "summary": "No log entries found",
        }
        result = self._get_output(key, default)
        return self._record_call("query_logs", {
            "log_type": log_type, "hostname": hostname,
            "timeframe": timeframe, "search_query": search_query,
        }, result)

    # ── Tool Descriptions (for LLM system prompt) ────────────────────────

    @staticmethod
    def get_tool_descriptions() -> list[dict]:
        """Return tool descriptions in OpenAI function-calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "query_network_flows",
                    "description": "Query network flow records. Returns flows matching filters with source/dest IPs, ports, bytes, protocol, and timestamps.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "time_range": {"type": "string", "description": "Time range (e.g., 'last_24h', 'last_7d')"},
                            "src_ip": {"type": "string", "description": "Source IP filter"},
                            "dst_ip": {"type": "string", "description": "Destination IP filter"},
                            "protocol": {"type": "string", "description": "Protocol filter (TCP/UDP/ICMP)"},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "lookup_ioc",
                    "description": "Look up an Indicator of Compromise against threat intelligence feeds. Returns threat score, attribution, related IOCs.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ioc_type": {"type": "string", "enum": ["ip", "domain", "hash", "email"]},
                            "value": {"type": "string", "description": "The IOC value to look up"},
                        },
                        "required": ["ioc_type", "value"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_sigma_matches",
                    "description": "Match Sigma detection rules against log events. Returns matching rules with severity and technique mapping.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "log_source": {"type": "string", "enum": ["windows_security", "sysmon", "proxy", "dns", "ids"]},
                            "timeframe": {"type": "string"},
                            "host": {"type": "string", "description": "Specific host to check"},
                        },
                        "required": ["log_source"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "query_attck",
                    "description": "Look up MITRE ATT&CK technique details including mitigations and detection methods.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "technique_id": {"type": "string", "description": "ATT&CK technique ID (e.g., T1566.001)"},
                        },
                        "required": ["technique_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "check_asset_status",
                    "description": "Check current status of a network asset including OS, services, open ports, and active alerts.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hostname": {"type": "string", "description": "Hostname to check"},
                        },
                        "required": ["hostname"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "memory_forensics",
                    "description": "Retrieve memory forensics results for a host including running processes, network connections, injected code, and artifacts.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hostname": {"type": "string", "description": "Hostname to analyze"},
                        },
                        "required": ["hostname"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_network_topology",
                    "description": "Get the current network topology map showing segments, hosts, connections, and firewall rules.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "query_logs",
                    "description": "Query specific log sources (auth, DNS, proxy, firewall, endpoint) with optional host and search filters.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "log_type": {"type": "string", "enum": ["auth", "dns", "proxy", "firewall", "endpoint"]},
                            "hostname": {"type": "string"},
                            "timeframe": {"type": "string"},
                            "search_query": {"type": "string"},
                        },
                        "required": ["log_type"],
                    },
                },
            },
        ]
