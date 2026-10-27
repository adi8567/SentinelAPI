"""SentinelAPI Policy-as-Code Loader.

Loads, validates, and serializes declarative security policies defined in YAML or JSON.
Ensures schema adherence, priority sorting, and integrity.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from backend.app.schemas.policy import PolicyCondition, PolicyRule

logger = logging.getLogger("sentinelapi.policy.loader")


class PolicyLoader:
    """Parses, validates, and loads Policy-as-Code definitions."""

    @staticmethod
    def load_from_yaml_file(file_path: str) -> List[PolicyRule]:
        """Loads and parses policy rules from a YAML file."""
        p = Path(file_path)
        if not p.exists():
            logger.warning(f"Policy file '{file_path}' not found.")
            return []

        try:
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return PolicyLoader.parse_policy_dict(data)
        except Exception as e:
            logger.error(f"Failed to parse policy YAML '{file_path}': {e}", exc_info=True)
            raise ValueError(f"Invalid policy YAML format: {e}") from e

    @staticmethod
    def load_from_yaml_string(yaml_content: str) -> List[PolicyRule]:
        """Loads and parses policy rules from a YAML string."""
        try:
            data = yaml.safe_load(yaml_content)
            return PolicyLoader.parse_policy_dict(data)
        except Exception as e:
            logger.error(f"Failed to parse policy YAML string: {e}")
            raise ValueError(f"Invalid policy YAML content: {e}") from e

    @staticmethod
    def parse_policy_dict(data: Any) -> List[PolicyRule]:
        """Converts raw dict/list structure into validated PolicyRule objects."""
        if not data:
            return []

        raw_rules = []
        if isinstance(data, dict):
            raw_rules = data.get("policies", [])
        elif isinstance(data, list):
            raw_rules = data
        else:
            raise ValueError("Policy document must be an object with 'policies' list or a list of rules.")

        rules: List[PolicyRule] = []
        seen_ids = set()

        for raw_rule in raw_rules:
            if not isinstance(raw_rule, dict):
                continue

            rule = PolicyRule(**raw_rule)
            if rule.policy_id in seen_ids:
                logger.warning(f"Duplicate policy_id '{rule.policy_id}' encountered; overwriting.")
                rules = [r for r in rules if r.policy_id != rule.policy_id]

            seen_ids.add(rule.policy_id)
            rules.append(rule)

        # Sort by priority ascending (1 is highest priority)
        rules.sort(key=lambda r: r.priority)
        logger.info(f"Loaded {len(rules)} validated policy rules.")
        return rules

    @staticmethod
    def export_to_yaml(rules: List[PolicyRule]) -> str:
        """Serializes a list of PolicyRule objects to formatted YAML."""
        data = {
            "version": "1.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "policies": [r.model_dump(mode="json") for r in rules],
        }
        return yaml.dump(data, sort_keys=False, default_flow_style=False)

    @staticmethod
    def export_to_json(rules: List[PolicyRule]) -> str:
        """Serializes a list of PolicyRule objects to JSON string."""
        data = {
            "version": "1.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "policies": [r.model_dump(mode="json") for r in rules],
        }
        return json.dumps(data, indent=2)
