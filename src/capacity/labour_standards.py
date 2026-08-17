"""Labour standards configuration and lookup."""

from __future__ import annotations

from typing import Dict

from .models import LabourStandardsConfig


class LabourStandards:
    """Provides labour productivity standards by role family.

    Standards are in "demand index units per labour hour" — i.e., how much
    demand (transactions or index points) one hour of labour can handle
    for a given role.
    """

    # Default standards by role family (configurable via config)
    DEFAULT_STANDARDS: Dict[str, float] = {
        "checkout": 28.0,
        "fresh": 18.0,
        "grocery": 22.0,
        "online": 15.0,
        "supervisor": 25.0,
        "management": 20.0,
        "support": 20.0,
        "default": 20.0,
    }

    # Map employee role names to role families
    ROLE_TO_FAMILY: Dict[str, str] = {
        "Checkout / Front End": "checkout",
        "Grocery / Nightfill": "grocery",
        "Fresh Foods": "fresh",
        "Online / Click & Collect": "online",
        "Department Supervisor": "supervisor",
        "Store Management": "management",
        "Other / Support": "support",
    }

    def __init__(self, standards: Dict[str, float] | None = None):
        """Initialise labour standards.

        Parameters
        ----------
        standards : Dict[str, float] | None
            Custom standards. If ``None``, defaults are used.
        """
        merged = dict(self.DEFAULT_STANDARDS)
        if standards:
            merged.update(standards)
        self.config = LabourStandardsConfig(standards=merged)

    def productivity_for_role(self, role: str) -> float:
        """Return the productivity standard for an employee role.

        Parameters
        ----------
        role : str
            Employee role name (e.g. "Checkout / Front End").

        Returns
        -------
        float
            Units of demand per labour hour.
        """
        family = self.ROLE_TO_FAMILY.get(role, "default")
        return self.config.productivity_for(family)

    def required_hours(self, demand_index: float, role: str) -> float:
        """Compute required labour hours for a given demand level.

        Parameters
        ----------
        demand_index : float
            The demand index (transactions or activity units).
        role : str
            Employee role name.

        Returns
        -------
        float
            Required labour hours.
        """
        productivity = self.productivity_for_role(role)
        if productivity <= 0:
            return 0.0
        return demand_index / productivity