"""
MITRE ATT&CK Knowledge Base (Embedded Subset)
==============================================
Contains the tactics, techniques, groups, and valid kill-chain orderings
needed for the Cybersecurity IR case study verifier.

Source: MITRE ATT&CK v15.1 (October 2024), Apache 2.0 License
Only techniques relevant to our 12 instances are included.
"""

# ── Tactics in kill-chain order ──────────────────────────────────────────────
TACTICS_ORDER = [
    "TA0043",  # Reconnaissance
    "TA0042",  # Resource Development
    "TA0001",  # Initial Access
    "TA0002",  # Execution
    "TA0003",  # Persistence
    "TA0004",  # Privilege Escalation
    "TA0005",  # Defense Evasion
    "TA0006",  # Credential Access
    "TA0007",  # Discovery
    "TA0008",  # Lateral Movement
    "TA0009",  # Collection
    "TA0011",  # Command and Control
    "TA0010",  # Exfiltration
    "TA0040",  # Impact
]

TACTIC_NAMES = {
    "TA0043": "Reconnaissance",
    "TA0042": "Resource Development",
    "TA0001": "Initial Access",
    "TA0002": "Execution",
    "TA0003": "Persistence",
    "TA0004": "Privilege Escalation",
    "TA0005": "Defense Evasion",
    "TA0006": "Credential Access",
    "TA0007": "Discovery",
    "TA0008": "Lateral Movement",
    "TA0009": "Collection",
    "TA0011": "Command and Control",
    "TA0010": "Exfiltration",
    "TA0040": "Impact",
}

TACTIC_INDEX = {t: i for i, t in enumerate(TACTICS_ORDER)}

# ── Techniques (id → metadata) ──────────────────────────────────────────────
TECHNIQUES = {
    # Initial Access
    "T1566.001": {
        "name": "Phishing: Spearphishing Attachment",
        "tactic": "TA0001",
        "description": "Adversary sends spearphishing email with malicious attachment",
        "platforms": ["Windows", "macOS", "Linux"],
        "data_sources": ["email_gateway", "endpoint_detection"],
    },
    "T1566.002": {
        "name": "Phishing: Spearphishing Link",
        "tactic": "TA0001",
        "description": "Adversary sends spearphishing email with malicious link",
        "platforms": ["Windows", "macOS", "Linux"],
        "data_sources": ["email_gateway", "proxy_logs"],
    },
    "T1190": {
        "name": "Exploit Public-Facing Application",
        "tactic": "TA0001",
        "description": "Adversary exploits vulnerability in internet-facing application",
        "platforms": ["Windows", "Linux", "Network"],
        "data_sources": ["application_logs", "network_flows", "ids_alerts"],
    },
    "T1078": {
        "name": "Valid Accounts",
        "tactic": "TA0001",
        "tactics": ["TA0001", "TA0003", "TA0004", "TA0005", "TA0008"],
        "description": "Adversary uses stolen or compromised credentials",
        "platforms": ["Windows", "Linux", "Cloud"],
        "data_sources": ["auth_logs", "active_directory"],
    },
    "T1078.002": {
        "name": "Valid Accounts: Domain Accounts",
        "tactic": "TA0001",
        "tactics": ["TA0001", "TA0003", "TA0004", "TA0005", "TA0008"],
        "description": "Adversary uses compromised domain credentials",
        "platforms": ["Windows"],
        "data_sources": ["auth_logs", "active_directory"],
    },
    "T1195.002": {
        "name": "Supply Chain Compromise: Software Supply Chain",
        "tactic": "TA0001",
        "description": "Adversary compromises software supply chain to deliver malware",
        "platforms": ["Windows", "Linux", "macOS"],
        "data_sources": ["software_inventory", "endpoint_detection"],
    },
    # Execution
    "T1059.001": {
        "name": "Command and Scripting Interpreter: PowerShell",
        "tactic": "TA0002",
        "tactics": ["TA0002", "TA0008"],
        "description": "Adversary uses PowerShell for execution (locally or after lateral movement)",
        "platforms": ["Windows"],
        "data_sources": ["process_monitoring", "powershell_logs", "command_line"],
    },
    "T1059.003": {
        "name": "Command and Scripting Interpreter: Windows Command Shell",
        "tactic": "TA0002",
        "description": "Adversary uses cmd.exe for execution",
        "platforms": ["Windows"],
        "data_sources": ["process_monitoring", "command_line"],
    },
    "T1204.002": {
        "name": "User Execution: Malicious File",
        "tactic": "TA0002",
        "description": "User opens malicious file delivered via phishing",
        "platforms": ["Windows", "macOS", "Linux"],
        "data_sources": ["endpoint_detection", "process_monitoring"],
    },
    # Persistence
    "T1547.001": {
        "name": "Boot or Logon Autostart Execution: Registry Run Keys",
        "tactic": "TA0003",
        "description": "Adversary adds registry run keys for persistence",
        "platforms": ["Windows"],
        "data_sources": ["registry_monitoring", "endpoint_detection"],
    },
    "T1053.005": {
        "name": "Scheduled Task/Job: Scheduled Task",
        "tactic": "TA0003",
        "description": "Adversary creates scheduled tasks for persistence",
        "platforms": ["Windows"],
        "data_sources": ["scheduled_tasks", "process_monitoring"],
    },
    "T1505.003": {
        "name": "Server Software Component: Web Shell",
        "tactic": "TA0003",
        "description": "Adversary installs web shell on server for persistence",
        "platforms": ["Windows", "Linux"],
        "data_sources": ["web_server_logs", "file_monitoring"],
    },
    # Privilege Escalation
    "T1068": {
        "name": "Exploitation for Privilege Escalation",
        "tactic": "TA0004",
        "description": "Adversary exploits software vulnerability for privilege escalation",
        "platforms": ["Windows", "Linux"],
        "data_sources": ["process_monitoring", "endpoint_detection"],
    },
    # Defense Evasion
    "T1070.004": {
        "name": "Indicator Removal: File Deletion",
        "tactic": "TA0005",
        "description": "Adversary deletes files to remove indicators",
        "platforms": ["Windows", "Linux", "macOS"],
        "data_sources": ["file_monitoring", "endpoint_detection"],
    },
    "T1027": {
        "name": "Obfuscated Files or Information",
        "tactic": "TA0005",
        "description": "Adversary obfuscates payloads to evade detection",
        "platforms": ["Windows", "Linux", "macOS"],
        "data_sources": ["endpoint_detection", "file_monitoring"],
    },
    "T1036.005": {
        "name": "Masquerading: Match Legitimate Name or Location",
        "tactic": "TA0005",
        "description": "Adversary names files to match legitimate software",
        "platforms": ["Windows", "Linux"],
        "data_sources": ["file_monitoring", "process_monitoring"],
    },
    # Credential Access
    "T1003.001": {
        "name": "OS Credential Dumping: LSASS Memory",
        "tactic": "TA0006",
        "description": "Adversary dumps LSASS process memory for credentials",
        "platforms": ["Windows"],
        "data_sources": ["process_monitoring", "endpoint_detection"],
    },
    "T1110.003": {
        "name": "Brute Force: Password Spraying",
        "tactic": "TA0006",
        "description": "Adversary uses password spraying against many accounts",
        "platforms": ["Windows", "Linux", "Cloud"],
        "data_sources": ["auth_logs", "active_directory"],
    },
    "T1555": {
        "name": "Credentials from Password Stores",
        "tactic": "TA0006",
        "description": "Adversary extracts credentials from password managers/stores",
        "platforms": ["Windows", "macOS", "Linux"],
        "data_sources": ["process_monitoring", "file_monitoring"],
    },
    # Discovery
    "T1087.002": {
        "name": "Account Discovery: Domain Account",
        "tactic": "TA0007",
        "description": "Adversary enumerates domain accounts",
        "platforms": ["Windows"],
        "data_sources": ["active_directory", "process_monitoring", "command_line"],
    },
    "T1046": {
        "name": "Network Service Discovery",
        "tactic": "TA0007",
        "description": "Adversary scans for services on remote hosts",
        "platforms": ["Windows", "Linux"],
        "data_sources": ["network_flows", "process_monitoring"],
    },
    "T1082": {
        "name": "System Information Discovery",
        "tactic": "TA0007",
        "description": "Adversary gathers system configuration information",
        "platforms": ["Windows", "Linux", "macOS"],
        "data_sources": ["process_monitoring", "command_line"],
    },
    # Lateral Movement
    "T1021.001": {
        "name": "Remote Services: Remote Desktop Protocol",
        "tactic": "TA0008",
        "description": "Adversary uses RDP for lateral movement",
        "platforms": ["Windows"],
        "data_sources": ["auth_logs", "network_flows", "rdp_logs"],
    },
    "T1021.002": {
        "name": "Remote Services: SMB/Windows Admin Shares",
        "tactic": "TA0008",
        "description": "Adversary uses SMB shares for lateral movement",
        "platforms": ["Windows"],
        "data_sources": ["network_flows", "smb_logs"],
    },
    "T1021.006": {
        "name": "Remote Services: Windows Remote Management",
        "tactic": "TA0008",
        "description": "Adversary uses WinRM for lateral movement",
        "platforms": ["Windows"],
        "data_sources": ["network_flows", "winrm_logs"],
    },
    "T1570": {
        "name": "Lateral Tool Transfer",
        "tactic": "TA0008",
        "description": "Adversary transfers tools between compromised systems",
        "platforms": ["Windows", "Linux"],
        "data_sources": ["network_flows", "file_monitoring"],
    },
    "T1091": {
        "name": "Replication Through Removable Media",
        "tactic": "TA0008",
        "description": "Adversary moves laterally via USB / removable media",
        "platforms": ["Windows", "Linux"],
        "data_sources": ["file_monitoring", "usb_logs"],
    },
    # Collection
    "T1005": {
        "name": "Data from Local System",
        "tactic": "TA0009",
        "description": "Adversary collects data from local system",
        "platforms": ["Windows", "Linux", "macOS"],
        "data_sources": ["file_monitoring", "process_monitoring"],
    },
    "T1039": {
        "name": "Data from Network Shared Drive",
        "tactic": "TA0009",
        "description": "Adversary collects data from network shares",
        "platforms": ["Windows", "Linux"],
        "data_sources": ["network_flows", "smb_logs", "file_monitoring"],
    },
    "T1114.002": {
        "name": "Email Collection: Remote Email Collection",
        "tactic": "TA0009",
        "description": "Adversary collects email from exchange/mail servers",
        "platforms": ["Windows", "Office 365"],
        "data_sources": ["email_logs", "network_flows"],
    },
    # Command and Control
    "T1071.001": {
        "name": "Application Layer Protocol: Web Protocols",
        "tactic": "TA0011",
        "description": "Adversary uses HTTP/HTTPS for C2",
        "platforms": ["Windows", "Linux", "macOS"],
        "data_sources": ["network_flows", "proxy_logs"],
    },
    "T1071.004": {
        "name": "Application Layer Protocol: DNS",
        "tactic": "TA0011",
        "description": "Adversary uses DNS for C2 communication",
        "platforms": ["Windows", "Linux"],
        "data_sources": ["dns_logs", "network_flows"],
    },
    "T1105": {
        "name": "Ingress Tool Transfer",
        "tactic": "TA0011",
        "description": "Adversary downloads tools to compromised host",
        "platforms": ["Windows", "Linux", "macOS"],
        "data_sources": ["network_flows", "endpoint_detection"],
    },
    "T1573.002": {
        "name": "Encrypted Channel: Asymmetric Cryptography",
        "tactic": "TA0011",
        "description": "Adversary uses asymmetric encryption for C2",
        "platforms": ["Windows", "Linux"],
        "data_sources": ["network_flows", "ssl_inspection"],
    },
    # Exfiltration
    "T1041": {
        "name": "Exfiltration Over C2 Channel",
        "tactic": "TA0010",
        "description": "Adversary exfiltrates data over existing C2 channel",
        "platforms": ["Windows", "Linux", "macOS"],
        "data_sources": ["network_flows", "proxy_logs"],
    },
    "T1048.003": {
        "name": "Exfiltration Over Alternative Protocol: Unencrypted Non-C2",
        "tactic": "TA0010",
        "description": "Adversary exfiltrates data via non-C2 protocol like FTP",
        "platforms": ["Windows", "Linux"],
        "data_sources": ["network_flows"],
    },
    "T1567.002": {
        "name": "Exfiltration Over Web Service: to Cloud Storage",
        "tactic": "TA0010",
        "description": "Adversary exfiltrates data to cloud storage services",
        "platforms": ["Windows", "Linux", "macOS"],
        "data_sources": ["network_flows", "proxy_logs"],
    },
    # Impact
    "T1486": {
        "name": "Data Encrypted for Impact",
        "tactic": "TA0040",
        "description": "Adversary encrypts data for ransomware",
        "platforms": ["Windows", "Linux"],
        "data_sources": ["file_monitoring", "endpoint_detection"],
    },
    "T1489": {
        "name": "Service Stop",
        "tactic": "TA0040",
        "description": "Adversary stops services to impact availability",
        "platforms": ["Windows", "Linux"],
        "data_sources": ["process_monitoring", "service_logs"],
    },
    "T1529": {
        "name": "System Shutdown/Reboot",
        "tactic": "TA0040",
        "description": "Adversary shuts down/reboots systems",
        "platforms": ["Windows", "Linux"],
        "data_sources": ["process_monitoring", "event_logs"],
    },
}

# ── Threat Actor Groups (subset for our instances) ──────────────────────────
GROUPS = {
    "G0007": {
        "name": "APT28",
        "aliases": ["Fancy Bear", "Sofacy", "Sednit", "STRONTIUM"],
        "origin": "Russia",
        "motivation": "political_intelligence",
        "common_techniques": [
            "T1566.001", "T1204.002", "T1059.001", "T1547.001", "T1078", "T1003.001",
            "T1110.003", "T1021.001", "T1021.002", "T1071.001", "T1041",
        ],
        "common_targets": ["government", "military", "media"],
        "typical_c2_patterns": ["cozy_bear_https", "encrypted_dns"],
    },
    "G0016": {
        "name": "APT29",
        "aliases": ["Cozy Bear", "The Dukes", "NOBELIUM"],
        "origin": "Russia",
        "motivation": "political_intelligence",
        "common_techniques": [
            "T1566.002", "T1078.002", "T1003.001", "T1570", "T1059.001", "T1053.005",
            "T1021.002", "T1087.002", "T1071.001", "T1573.002", "T1041",
        ],
        "common_targets": ["government", "think_tanks", "technology"],
        "typical_c2_patterns": ["tor_exit_nodes", "domain_fronting"],
    },
    "G0096": {
        "name": "APT41",
        "aliases": ["Winnti", "Barium", "Wicked Panda"],
        "origin": "China",
        "motivation": "ip_theft_and_financial",
        "common_techniques": [
            "T1190", "T1195.002", "T1078", "T1059.001", "T1505.003", "T1078.002",
            "T1082", "T1005", "T1021.001", "T1021.006", "T1091", "T1039", "T1048.003",
            "T1053.005", "T1071.001", "T1041",
        ],
        "common_targets": ["technology", "healthcare", "gaming", "telecom"],
        "typical_c2_patterns": ["shadowpad_c2", "cobalt_strike_malleable"],
    },
    "G0046": {
        "name": "FIN7",
        "aliases": ["Carbanak", "Carbon Spider"],
        "origin": "Russia",
        "motivation": "financial",
        "common_techniques": [
            "T1566.001", "T1204.002", "T1059.001", "T1059.003",
            "T1555", "T1005", "T1071.001", "T1041",
        ],
        "common_targets": ["retail", "hospitality", "financial"],
        "typical_c2_patterns": ["carbanak_http", "js_backdoor"],
    },
    "G0032": {
        "name": "Lazarus Group",
        "aliases": ["Hidden Cobra", "ZINC", "Labyrinth Chollima"],
        "origin": "North Korea",
        "motivation": "financial_and_espionage",
        "common_techniques": [
            "T1566.001", "T1566.002", "T1204.002", "T1195.002", "T1059.001", "T1547.001",
            "T1027", "T1046", "T1021.002", "T1005", "T1071.001", "T1071.004", "T1048.003", "T1486",
        ],
        "common_targets": ["financial", "cryptocurrency", "defense"],
        "typical_c2_patterns": ["custom_rat_https", "steganography_c2"],
    },
    "G0010": {
        "name": "Turla",
        "aliases": ["Snake", "Venomous Bear", "KRYPTON"],
        "origin": "Russia",
        "motivation": "political_intelligence",
        "common_techniques": [
            "T1190", "T1566.002", "T1059.001", "T1053.005", "T1068", "T1036.005",
            "T1003.001", "T1082", "T1021.006", "T1071.001", "T1071.004", "T1567.002", "T1041",
        ],
        "common_targets": ["government", "military", "embassy"],
        "typical_c2_patterns": ["satellite_c2", "dns_tunneling", "compromised_infrastructure"],
    },
    "INSIDER": {
        "name": "Insider Threat",
        "aliases": [],
        "origin": "internal",
        "motivation": "financial_or_grudge",
        "common_techniques": [
            "T1078", "T1005", "T1039", "T1567.002",
        ],
        "common_targets": ["own_organization"],
        "typical_c2_patterns": ["none_or_cloud_exfil"],
    },
}


def get_tactic_for_technique(technique_id: str) -> str | None:
    """Returns the tactic ID for a given technique."""
    tech = TECHNIQUES.get(technique_id)
    return tech["tactic"] if tech else None


def get_tactic_order(tactic_id: str) -> int:
    """Returns the ordinal position of a tactic in the kill chain."""
    return TACTIC_INDEX.get(tactic_id, -1)


def get_techniques_for_group(group_id: str) -> list[str]:
    """Returns the list of common technique IDs for a threat actor group."""
    group = GROUPS.get(group_id)
    return group["common_techniques"] if group else []


def is_technique_consistent_with_group(technique_id: str, group_id: str) -> bool:
    """Checks if a technique is commonly used by a specific threat actor group."""
    return technique_id in get_techniques_for_group(group_id)


TACTIC_STAGES = {
    "TA0043": [0],         # Reconnaissance
    "TA0042": [0],         # Resource Development
    "TA0001": [1],         # Initial Access
    "TA0002": [2],         # Execution
    "TA0003": [2, 3],      # Persistence
    "TA0004": [2, 3],      # Privilege Escalation
    "TA0005": [2, 3],      # Defense Evasion
    "TA0006": [2, 3],      # Credential Access
    "TA0007": [2, 3],      # Discovery
    "TA0008": [2, 3],      # Lateral Movement
    "TA0009": [3, 4],      # Collection
    "TA0011": [2, 3, 4],   # Command and Control (active throughout post-execution lifecycle)
    "TA0010": [4],         # Exfiltration
    "TA0040": [4],         # Impact
}


def validate_kill_chain_order(techniques: list[str]) -> tuple[bool, list[str]]:
    """
    Validates that a sequence of techniques follows valid tactical ordering.
    A technique may span multiple tactical phases (e.g., T1078 Valid Accounts spans
    Initial Access, Persistence, Privilege Escalation, and Lateral Movement).
    Returns (is_valid, list_of_ordering_violations).
    """
    violations = []
    prev_stage = -1
    prev_tech = None

    for tech_id in techniques:
        tech = TECHNIQUES.get(tech_id)
        if tech is None:
            violations.append(f"unknown_technique_{tech_id}")
            continue

        tactics_list = tech.get("tactics", [tech["tactic"]])
        valid_stages = set()
        for t in tactics_list:
            stages = TACTIC_STAGES.get(t, [TACTIC_INDEX.get(t, 3)])
            valid_stages.update(stages)

        possible_next = [s for s in valid_stages if s >= prev_stage]

        if possible_next:
            prev_stage = min(possible_next)
        else:
            violations.append(
                f"ordering_violation_{prev_tech}_before_{tech_id}"
            )
            prev_stage = max(valid_stages)
        prev_tech = tech_id

    return len(violations) == 0, violations


# ── Dynamic Loader for Official MITRE ATT&CK STIX 2.1 Dataset ────────────────
import os, json

OFFICIAL_STIX_FILE = os.path.join(os.path.dirname(__file__), "enterprise-attack.json")

PHASE_TO_TACTIC_ID = {
    "reconnaissance": "TA0043",
    "resource-development": "TA0042",
    "initial-access": "TA0001",
    "execution": "TA0002",
    "persistence": "TA0003",
    "privilege-escalation": "TA0004",
    "defense-evasion": "TA0005",
    "credential-access": "TA0006",
    "discovery": "TA0007",
    "lateral-movement": "TA0008",
    "collection": "TA0009",
    "command-and-control": "TA0011",
    "exfiltration": "TA0010",
    "impact": "TA0040",
}


def load_official_stix_dataset() -> bool:
    """
    Dynamically loads and overlays the official MITRE ATT&CK Enterprise STIX 2.1
    dataset (51MB) directly into TECHNIQUES and GROUPS.
    Enables zero-latency inference directly against the canonical knowledge graph.
    Auto-downloads dataset if not present locally.
    """
    import urllib.request

    if not os.path.exists(OFFICIAL_STIX_FILE):
        try:
            print("Downloading official MITRE ATT&CK STIX dataset (51MB)...")
            url = "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json"
            urllib.request.urlretrieve(url, OFFICIAL_STIX_FILE)
            print("Official MITRE ATT&CK STIX dataset downloaded successfully.")
        except Exception as e:
            print(f"Notice: Could not download official STIX dataset ({e}), using embedded knowledge base.")
            return False

    try:
        with open(OFFICIAL_STIX_FILE, "r", encoding="utf-8") as f:
            bundle = json.load(f)

        id_to_mitre = {}
        for o in bundle.get("objects", []):
            if o.get("revoked", False) or o.get("x_mitre_deprecated", False):
                continue
            ext_refs = o.get("external_references", [])
            mitre_id = next((r["external_id"] for r in ext_refs if r.get("source_name") == "mitre-attack"), None)
            if mitre_id:
                id_to_mitre[o["id"]] = (o["type"], mitre_id)

                if o.get("type") == "attack-pattern":
                    phases = [
                        PHASE_TO_TACTIC_ID.get(p["phase_name"], "TA0001")
                        for p in o.get("kill_chain_phases", [])
                        if p.get("kill_chain_name") == "mitre-attack"
                    ]
                    primary_tactic = phases[0] if phases else "TA0001"
                    if mitre_id not in TECHNIQUES:
                        TECHNIQUES[mitre_id] = {
                            "name": o.get("name", ""),
                            "tactic": primary_tactic,
                            "tactics": phases,
                            "description": o.get("description", ""),
                            "platforms": o.get("x_mitre_platforms", ["Windows"]),
                        }
                    else:
                        TECHNIQUES[mitre_id]["name"] = o.get("name", TECHNIQUES[mitre_id]["name"])
                        TECHNIQUES[mitre_id]["description"] = o.get("description", TECHNIQUES[mitre_id]["description"])
                        TECHNIQUES[mitre_id]["platforms"] = o.get("x_mitre_platforms", TECHNIQUES[mitre_id]["platforms"])
                        if phases:
                            existing_tactics = TECHNIQUES[mitre_id].get("tactics", [TECHNIQUES[mitre_id]["tactic"]])
                            TECHNIQUES[mitre_id]["tactics"] = list(set(existing_tactics + phases))

                elif o.get("type") == "intrusion-set":
                    if mitre_id not in GROUPS:
                        GROUPS[mitre_id] = {
                            "name": o.get("name", ""),
                            "aliases": o.get("aliases", []),
                            "origin": "unknown",
                            "motivation": "espionage",
                            "common_techniques": [],
                            "common_targets": [],
                            "typical_c2_patterns": [],
                        }

        # Parse transitive STIX relationships (Group -> Technique + Group -> Tool -> Technique)
        group_to_tools = {}
        tool_to_techs = {}
        group_to_techs = {}

        for o in bundle.get("objects", []):
            if o.get("type") == "relationship" and o.get("relationship_type") == "uses":
                src = id_to_mitre.get(o.get("source_ref"))
                tgt = id_to_mitre.get(o.get("target_ref"))
                if src and tgt:
                    src_type, src_id = src
                    tgt_type, tgt_id = tgt
                    if src_type == "intrusion-set" and tgt_type == "attack-pattern":
                        group_to_techs.setdefault(src_id, set()).add(tgt_id)
                    elif src_type == "intrusion-set" and tgt_type in ["tool", "malware"]:
                        group_to_tools.setdefault(src_id, set()).add(tgt_id)
                    elif src_type in ["tool", "malware"] and tgt_type == "attack-pattern":
                        tool_to_techs.setdefault(src_id, set()).add(tgt_id)

        for gid, group_data in GROUPS.items():
            if gid == "INSIDER":
                continue
            direct = group_to_techs.get(gid, set())
            indirect = set()
            for tool_id in group_to_tools.get(gid, []):
                indirect.update(tool_to_techs.get(tool_id, []))
            official_techs = direct.union(indirect)
            existing = set(group_data.get("common_techniques", []))
            group_data["common_techniques"] = list(existing.union(official_techs))

        return True
    except Exception as e:
        print(f"Warning: Failed loading official STIX bundle: {e}")
        return False


# Automatically load official STIX dataset upon import
IS_OFFICIAL_STIX_LOADED = load_official_stix_dataset()

