from incydr.enums import _Enum


class WatchlistType(_Enum):
    WATCHLIST_TYPE_UNSPECIFIED = "WATCHLIST_TYPE_UNSPECIFIED"
    CONTRACT_EMPLOYEE = "CONTRACT_EMPLOYEE"
    DEPARTING_EMPLOYEE = "DEPARTING_EMPLOYEE"
    ELEVATED_ACCESS_PRIVILEGES = "ELEVATED_ACCESS_PRIVILEGES"
    FLIGHT_RISK = "FLIGHT_RISK"
    HIGH_IMPACT_EMPLOYEE = "HIGH_IMPACT_EMPLOYEE"
    NEW_EMPLOYEE = "NEW_EMPLOYEE"
    PERFORMANCE_CONCERNS = "PERFORMANCE_CONCERNS"
    POOR_SECURITY_PRACTICES = "POOR_SECURITY_PRACTICES"
    SUSPICIOUS_SYSTEM_ACTIVITY = "SUSPICIOUS_SYSTEM_ACTIVITY"
    CUSTOM = "CUSTOM"
