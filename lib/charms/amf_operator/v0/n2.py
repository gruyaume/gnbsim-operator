"""N2 Interface."""

from ops.framework import EventBase, EventSource, Object
from ops.charm import CharmBase, CharmEvents, RelationChangedEvent
from typing import Optional, Tuple


# The unique Charmhub library identifier, never change it
LIBID = "8436ec6d894947c1bd384234ccc64e81"

# Increment this major API version when introducing breaking changes
LIBAPI = 0

# Increment this PATCH version before using `charmcraft publish-lib` or reset
# to 0 if you are raising the major API version
LIBPATCH = 1


class AMFAvailableEvent(EventBase):
    """Dataclass for N2 available events."""

    def __init__(self, handle, hostname: str, port: str):
        """Sets hostname."""
        super().__init__(handle)
        self.hostname = hostname
        self.port = port

    def snapshot(self) -> dict:
        """Returns event data."""
        return {
            "hostname": self.hostname,
            "port": self.port,
        }

    def restore(self, snapshot) -> None:
        """Restores event data."""
        self.hostname = snapshot["hostname"]
        self.port = snapshot["port"]


class N2RequirerCharmEvents(CharmEvents):
    """All custom events for the N2Requirer."""

    amf_available = EventSource(AMFAvailableEvent)


class N2Provides(Object):

    def __init__(self, charm: CharmBase, relationship_name: str):
        self.relationship_name = relationship_name
        super().__init__(charm, relationship_name)

    def set_info(self, hostname: str, port: str) -> None:
        relations = self.model.relations[self.relationship_name]
        for relation in relations:
            relation.data[self.model.app]["hostname"] = hostname
            relation.data[self.model.app]["port"] = port


class N2Requires(Object):

    on = N2RequirerCharmEvents()

    def __init__(self, charm: CharmBase, relationship_name: str):
        self.relationship_name = relationship_name
        self.charm = charm
        super().__init__(charm, relationship_name)
        self.framework.observe(
            charm.on[relationship_name].relation_changed, self._on_relation_changed
        )

    def _on_relation_changed(self, event: RelationChangedEvent) -> None:
        """Triggered everytime there's a change in relation data.

        Args:
            event (RelationChangedEvent): Juju event

        Returns:
            None
        """
        hostname = event.relation.data[event.app].get("hostname")
        port = event.relation.data[event.app].get("port")
        if hostname:
            self.on.amf_available.emit(hostname=hostname, port=port)

    def get_amf_info(self) -> Optional[Tuple[str, str]]:
        """Returns N2 info."""
        for relation in self.model.relations[self.relationship_name]:
            if not relation.data:
                continue
            if not relation.data[relation.app]:
                continue
            return relation.data[relation.app].get("hostname", None),\
                relation.data[relation.app].get("port", None)
        return None
