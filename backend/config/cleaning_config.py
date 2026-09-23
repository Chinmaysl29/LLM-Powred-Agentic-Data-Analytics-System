CLEANING_THRESHOLDS = {
    "missing_values": {
        "critical": 0.50,      # >50% missing -> Critical
        "high": 0.30,          # 30-50% -> High
        "medium": 0.10,        # 10-30% -> Medium
        "low": 0.01            # 1-10% -> Low
    },
    "duplicates": {
        "critical": 0.50,
        "high": 0.20,
        "medium": 0.05
    },
    "outliers": {
        "iqr_multiplier": 1.5,
        "zscore_threshold": 3.0,
        "critical_percentage": 0.40,    # >40% = Critical
        "high_percentage": 0.20
    },
    "type_conversion": {
        "numeric_parse_threshold": 0.95,  # 95% must parse
        "datetime_parse_threshold": 0.90
    },
    "consistency": {
        "format_parse_threshold": 0.80,   # 80% must parse
        "case_variant_threshold": 0.90    # 90% same case = OK
    },
    "quality_improvement": {
        "critical_current_score": 60,     # Score <60 = Critical
        "potential_gain_threshold": 15    # +15 points possible = Notable
    }
}

PRIORITY_WEIGHTS = {
    "missing_values": 0.30,
    "duplicates": 0.15,
    "type_conversion": 0.20,
    "outliers": 0.15,
    "consistency": 0.10,
    "quality_improvement": 0.10
}

TYPE_STRATEGIES = {
    "numeric": {
        "missing_strategies": ["mean", "median", "mode", "drop_rows", "drop_column"],
        "outlier_detection": ["iqr", "zscore"]
    },
    "categorical": {
        "missing_strategies": ["mode", "drop_rows", "drop_column"],
        "outlier_detection": []  # Not applicable
    },
    "datetime": {
        "missing_strategies": ["forward_fill", "backward_fill", "drop_rows", "drop_column"],
        "outlier_detection": ["zscore_by_epoch"]  # Treat as numeric epoch
    },
    "boolean": {
        "missing_strategies": ["mode", "drop_rows"],
        "outlier_detection": []
    }
}
