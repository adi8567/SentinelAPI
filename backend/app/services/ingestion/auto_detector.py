"""Parser Registry & Format Auto-Detector.

Provides automatic detection and routing of incoming log streams to the appropriate parser.
"""

from typing import Dict, List, Optional, Tuple, Type
from backend.app.schemas.events import ApiEvent, LogSource
from backend.app.services.ingestion.base import BaseLogParser
from backend.app.services.ingestion.nginx_parser import NginxParser
from backend.app.services.ingestion.envoy_parser import EnvoyParser
from backend.app.services.ingestion.kong_parser import KongParser
from backend.app.services.ingestion.aws_gw_parser import AwsApiGwParser
from backend.app.services.ingestion.azure_apim_parser import AzureApimParser
from backend.app.services.ingestion.gcp_endpoints_parser import GcpEndpointsParser
from backend.app.services.ingestion.otel_parser import OtelTraceParser


class ParserRegistry:
    def __init__(self):
        self._parsers: Dict[LogSource, BaseLogParser] = {}
        self._priority_list: List[BaseLogParser] = []
        self._register_default_parsers()

    def register(self, parser: BaseLogParser):
        self._parsers[parser.source_type] = parser
        if parser not in self._priority_list:
            self._priority_list.append(parser)

    def _register_default_parsers(self):
        # Register in heuristic priority order
        self.register(KongParser())
        self.register(AwsApiGwParser())
        self.register(AzureApimParser())
        self.register(GcpEndpointsParser())
        self.register(OtelTraceParser())
        self.register(EnvoyParser())
        self.register(NginxParser())

    def get_parser(self, source_type: LogSource) -> Optional[BaseLogParser]:
        return self._parsers.get(source_type)

    def detect_parser(self, sample_line: str) -> Optional[BaseLogParser]:
        """Tries each registered parser's can_parse heuristic."""
        for parser in self._priority_list:
            try:
                if parser.can_parse(sample_line):
                    return parser
            except Exception:
                continue
        # Default fallback to NGINX parser if text line resembles standard access log
        return self._parsers.get(LogSource.NGINX)

    def parse_with_detection(
        self, lines: List[str], gateway_id: str = "default-gw", forced_source: Optional[LogSource] = None
    ) -> Tuple[List[ApiEvent], List[Tuple[int, str, str]], str]:
        """Parses lines either with a forced parser or by auto-detecting from the first valid line."""
        if not lines:
            return [], [], "none"

        parser: Optional[BaseLogParser] = None
        if forced_source and forced_source != LogSource.AUTO:
            parser = self.get_parser(forced_source)

        if not parser:
            # Detect using first non-empty line
            for line in lines:
                if line.strip():
                    parser = self.detect_parser(line.strip())
                    if parser:
                        break

        if not parser:
            parser = self.get_parser(LogSource.NGINX)

        events, errors = parser.parse_batch(lines, gateway_id=gateway_id)
        return events, errors, parser.source_type.value


# Global registry instance
parser_registry = ParserRegistry()
