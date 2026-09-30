"""Test data from the model's browser checks never outlives its run.

The database and its migration record are copied before the first agent-browser command, and put
back before the host's final checks and when the run ends. The record travels with the data: a
migration applied after the copy counts as new again, and the host's gate reapplies it to the clean
data instead of leaving a schema the record no longer describes.
"""

from typing import Any

from e2b import SandboxException

from ..tools.tools import ROOT
from . import migrations

SNAPSHOT = "/tmp/accretion-before-checks.dump"


class CheckData:
    def __init__(self, sandbox, stack: dict[str, Any]):
        self.sandbox = sandbox
        self.stack = stack
        self.saved = False
        # migrated.json as it was at the copy; None when the project had none yet.
        self.record: str | None = None

    async def keep(self) -> None:
        """Copy the database before the first check of the run; later checks share that copy."""
        if self.saved:
            return
        try:
            self.record = await self.sandbox.files.read(f"{ROOT}/{migrations.APPLIED}")
        except SandboxException:
            self.record = None
        if not await migrations.snapshot(self.sandbox, self.stack, SNAPSHOT):
            # No copy, no check: test data written without one could never be removed.
            raise ValueError("Could not copy the database before the browser check. Try again, or finish.")
        self.saved = True

    async def discard(self) -> bool:
        """Put the copy back. True when test data was removed."""
        if not self.saved:
            return False
        self.saved = False
        restored = await migrations.restore_snapshot(self.sandbox, self.stack, SNAPSHOT)
        try:
            if self.record is None:
                await self.sandbox.files.remove(f"{ROOT}/{migrations.APPLIED}")
            else:
                await self.sandbox.files.write(f"{ROOT}/{migrations.APPLIED}", self.record)
        except SandboxException:
            return False
        return restored
