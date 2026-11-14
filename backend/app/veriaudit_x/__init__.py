"""VeriAudit-X: versioned dataset infrastructure for VeriAudit v2.

See dataset/veriaudit-x/README.md for the data model.
"""

from app.veriaudit_x.schema import SCHEMA_VERSION, DatasetManifest, VeriAuditXRecord, json_schema
from app.veriaudit_x.splits import SplitLeakageError, assign_splits, check_leakage, write_splits
from app.veriaudit_x.validation import ValidationConfig, ValidationReport, validate_file, validate_objects

__all__ = [
    "SCHEMA_VERSION",
    "DatasetManifest",
    "SplitLeakageError",
    "ValidationConfig",
    "ValidationReport",
    "VeriAuditXRecord",
    "assign_splits",
    "check_leakage",
    "json_schema",
    "validate_file",
    "validate_objects",
    "write_splits",
]
