"""Substrate tooling: repo-walker and drift detection driven by the
canonical substrate manifest (UIAO_200) and workspace contract (UIAO_201).
"""

from uiao.substrate.walker import SubstrateReport, walk_substrate

__all__ = ["SubstrateReport", "walk_substrate"]
