"""Feature registry for managing optional dependencies in QuickHooks."""

import importlib


class FeatureRegistry:
    """Manages optional feature loading and provides helpful error messages."""

    def __init__(self):
        """Initialize the feature registry."""
        self.features: dict[str, bool] = {}
        self.feature_dependencies: dict[str, list[str]] = {
            "ai": ["lancedb", "fastembed"],
            "search": ["tantivy"],
            "analytics": ["pyarrow", "polars", "duckdb", "pandas", "plotly"],
            "agents": ["openai", "anthropic", "tiktoken"],
            "scaffold": ["cookiecutter", "black", "isort"],
            "web": ["fastapi", "uvicorn", "streamlit", "websockets"],
            "cloud": ["boto3", "redis", "celery"],
            "enterprise": ["cryptography", "ldap3", "prometheus_client"],
            "performance": ["redis", "aiocache", "psutil"],
        }
        self.combined_features: dict[str, list[str]] = {
            "essential": ["ai", "search", "dev"],
            "pro": ["essential", "analytics", "scaffold", "agents"],
            "enterprise-full": ["pro", "web", "cloud", "enterprise", "performance"],
            "all": [
                "ai",
                "search",
                "analytics",
                "agents",
                "scaffold",
                "web",
                "cloud",
                "enterprise",
                "performance",
            ],
        }
        self._scan_features()

    def _scan_features(self) -> None:
        """Scan for available features based on installed packages."""
        for feature, dependencies in self.feature_dependencies.items():
            self.features[feature] = self._check_dependencies(dependencies)

        # Check combined features
        for feature, sub_features in self.combined_features.items():
            self.features[feature] = all(
                self.features.get(sub_feature, False)
                for sub_feature in sub_features
                if sub_feature in self.features
            )

    def _check_dependencies(self, dependencies: list[str]) -> bool:
        """Check if all dependencies for a feature are available."""
        for dep in dependencies:
            try:
                importlib.import_module(dep)
            except ImportError:
                return False
        return True

    def require(self, feature: str) -> None:
        """Require a feature or raise helpful error.

        Args:
            feature: Feature name to require

        Raises:
            ImportError: If feature is not available
        """
        if not self.has(feature):
            missing_deps = self._get_missing_dependencies(feature)
            msg = (
                f"Feature '{feature}' is not available.\n"
                f"Missing dependencies: {', '.join(missing_deps)}\n"
                f"Install with: pip install quickhooks[{feature}]"
            )
            raise ImportError(msg)

    def has(self, feature: str) -> bool:
        """Check if feature is available.

        Args:
            feature: Feature name to check

        Returns:
            True if feature is available, False otherwise
        """
        return self.features.get(feature, False)

    def _get_missing_dependencies(self, feature: str) -> list[str]:
        """Get list of missing dependencies for a feature."""
        if feature not in self.feature_dependencies:
            return []

        missing = []
        for dep in self.feature_dependencies[feature]:
            try:
                importlib.import_module(dep)
            except ImportError:
                missing.append(dep)
        return missing

    def list_available(self) -> dict[str, bool]:
        """List all features and their availability status.

        Returns:
            Dictionary mapping feature names to availability status
        """
        return self.features.copy()

    def list_missing(self) -> list[str]:
        """List all missing features.

        Returns:
            List of feature names that are not available
        """
        return [
            feature for feature, available in self.features.items() if not available
        ]

    def get_installation_command(self, features: list[str]) -> str:
        """Get pip installation command for multiple features.

        Args:
            features: List of feature names

        Returns:
            Pip install command string
        """
        if len(features) == 1:
            return f"pip install quickhooks[{features[0]}]"
        feature_string = ",".join(features)
        return f"pip install quickhooks[{feature_string}]"

    def suggest_install_group(self, required_features: list[str]) -> str | None:
        """Suggest the most appropriate install group for required features.

        Args:
            required_features: List of features that are needed

        Returns:
            Suggested install group name, or None if no good match
        """
        required_set = set(required_features)

        # Check if any combined feature includes all required features
        for group, sub_features in self.combined_features.items():
            if required_set.issubset(set(sub_features)):
                return group

        return None


# Global registry instance
features = FeatureRegistry()


def require_feature(feature: str) -> None:
    """Convenience function to require a feature.

    Args:
        feature: Feature name to require

    Raises:
        ImportError: If feature is not available
    """
    features.require(feature)


def has_feature(feature: str) -> bool:
    """Convenience function to check if feature is available.

    Args:
        feature: Feature name to check

    Returns:
        True if feature is available, False otherwise
    """
    return features.has(feature)


def list_features() -> dict[str, bool]:
    """Convenience function to list all features.

    Returns:
        Dictionary mapping feature names to availability status
    """
    return features.list_available()


class LazyImport:
    """Lazy import that provides helpful error messages for missing features."""

    def __init__(self, module_name: str, feature: str, install_extra: str):
        """Initialize lazy import.

        Args:
            module_name: Name of the module to import
            feature: Feature name for error messages
            install_extra: Extra name for installation instructions
        """
        self.module_name = module_name
        self.feature = feature
        self.install_extra = install_extra
        self._module = None

    def __getattr__(self, name: str):
        """Get attribute from the lazily imported module."""
        if self._module is None:
            if not features.has(self.feature):
                msg = (
                    f"Feature '{self.feature}' is not available. "
                    f"Install with: pip install quickhooks[{self.install_extra}]"
                )
                raise ImportError(msg)
            self._module = importlib.import_module(self.module_name)

        return getattr(self._module, name)


# Common lazy imports for optional dependencies
try:
    import lancedb

    LANCEDB_AVAILABLE = True
except ImportError:
    lancedb = LazyImport("lancedb", "ai", "ai")  # type: ignore
    LANCEDB_AVAILABLE = False

try:
    import polars as pl

    POLARS_AVAILABLE = True
except ImportError:
    pl = LazyImport("polars", "analytics", "analytics")  # type: ignore
    POLARS_AVAILABLE = False

try:
    import duckdb

    DUCKDB_AVAILABLE = True
except ImportError:
    duckdb = LazyImport("duckdb", "analytics", "analytics")  # type: ignore
    DUCKDB_AVAILABLE = False

try:
    import fastapi

    FASTAPI_AVAILABLE = True
except ImportError:
    fastapi = LazyImport("fastapi", "web", "web")  # type: ignore
    FASTAPI_AVAILABLE = False

try:
    import streamlit as st

    STREAMLIT_AVAILABLE = True
except ImportError:
    st = LazyImport("streamlit", "web", "web")  # type: ignore
    STREAMLIT_AVAILABLE = False
