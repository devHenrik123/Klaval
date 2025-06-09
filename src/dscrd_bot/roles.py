from enum import StrEnum
from typing import Final

RolePrefix: Final[str] = "HK "


class HeBotRole(StrEnum):
    Unverified = RolePrefix + "Unverified"
    VerificationPending = RolePrefix + "Verification Pending"
    Verified = RolePrefix + "Verified"
