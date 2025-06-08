from enum import StrEnum
from typing import Final

RolePrefix: Final[str] = "HKBot_"


class HeBotRole(StrEnum):
    Unverified = RolePrefix + "unverified"
    VerificationPending = RolePrefix + "verification_pending"
    Verified = RolePrefix + "verified"
