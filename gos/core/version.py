from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class VersionInfo:
    major: int
        minor: int
            patch: int
                build: str

                    def string(self) -> str:
                            return f"{self.major}.{self.minor}.{self.patch}"

                                def full(self) -> str:
                                        return f"{self.string()}+{self.build}"


                                        # Canonical UIAO-GOS version
                                        VERSION = VersionInfo(
                                            major=0,
                                                minor=1,
                                                    patch=0,
                                                        build=datetime.utcnow().strftime("%Y%m%d%H%M%S"),
                                                        )
                                                        