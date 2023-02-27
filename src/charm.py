#!/usr/bin/env python3
# Copyright 2022 Guillaume Belanger
# See LICENSE file for licensing details.

"""Charmed operator for the 5G OMEC GNBSIM service."""

import logging
from ipaddress import IPv4Address
from subprocess import check_output
from typing import Optional, Union

from charms.amf_operator.v0.n2 import AMFAvailableEvent, N2Requires
from charms.observability_libs.v1.kubernetes_service_patch import KubernetesServicePatch
from jinja2 import Environment, FileSystemLoader
from lightkube.models.core_v1 import ServicePort
from ops.charm import (
    ActionEvent,
    CharmBase,
    InstallEvent,
    PebbleReadyEvent,
    RelationJoinedEvent,
    RemoveEvent,
)
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, ModelError, WaitingStatus
from ops.pebble import ExecError

from kubernetes import Kubernetes

logger = logging.getLogger(__name__)

BASE_CONFIG_PATH = "/etc/gnbsim"
CONFIG_FILE_NAME = "gnb.conf"


class GNBSIMOperatorCharm(CharmBase):
    """Main class to describe juju event handling for the 5G GNBSIM operator."""

    def __init__(self, *args):
        super().__init__(*args)
        self._container_name = self._service_name = "gnbsim"
        self._container = self.unit.get_container(self._container_name)
        self._n2_requires = N2Requires(charm=self, relationship_name="n2")
        self._kubernetes = Kubernetes(namespace=self.model.name)
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.gnbsim_pebble_ready, self._on_gnbsim_pebble_ready)
        self.framework.observe(self._n2_requires.on.amf_available, self._on_amf_available)
        self.framework.observe(self.on.n2_relation_joined, self._on_gnbsim_pebble_ready)
        self.framework.observe(self.on.start_simulation_action, self._on_start_simulation_action)
        self.framework.observe(self.on.remove, self._on_remove)
        self._service_patcher = KubernetesServicePatch(
            charm=self,
            ports=[
                ServicePort(name="ngapp", port=38412, protocol="SCTP"),
                ServicePort(name="http-api", port=6000),
            ],
        )

    def _on_install(self, event: InstallEvent) -> None:
        """Handle the install event."""
        self._kubernetes.create_network_attachment_definition()
        self._kubernetes.patch_statefulset(statefulset_name=self.app.name)

    def _on_amf_available(self, event: AMFAvailableEvent) -> None:
        if not self._container.can_connect():
            self.unit.status = WaitingStatus("Waiting for container to be ready")
            event.defer()
            return
        self._write_config_file(amf_hostname=event.hostname, amf_port=event.port)
        self._on_gnbsim_pebble_ready(event)

    def _write_config_file(self, amf_hostname: str, amf_port: str) -> None:
        jinja2_environment = Environment(loader=FileSystemLoader("src/templates/"))
        template = jinja2_environment.get_template("gnb.conf.j2")
        content = template.render(
            amf_hostname=amf_hostname,
            amf_port=amf_port,
            gnb1_n3_ip_address="192.168.251.5",
            gnb2_n3_ip_address="192.168.251.6",
            upf_access_ip_address="192.168.252.3/32",  # TODO: Replace with relation data
            upf_gateway="192.168.251.1",  # TODO: Replace with relation data
            default_icmp_packet_destionation="192.168.250.1",  # TODO: Replace with relation data
        )
        self._container.push(path=f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}", source=content)
        logger.info(f"Pushed {CONFIG_FILE_NAME} config file")

    def _on_remove(self, event: RemoveEvent) -> None:
        """Handle the remove event."""
        self._kubernetes.delete_network_attachment_definition()

    @property
    def _config_file_is_written(self) -> bool:
        if not self._container.exists(f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}"):
            logger.info(f"Config file is not written: {CONFIG_FILE_NAME}")
            return False
        logger.info("Config file is written")
        return True

    def _on_gnbsim_pebble_ready(
        self, event: Union[PebbleReadyEvent, AMFAvailableEvent, RelationJoinedEvent]
    ) -> None:
        """Handle the pebble ready event."""
        if not self._container.can_connect():
            self.unit.status = WaitingStatus("Waiting for container to be ready")
            event.defer()
            return
        if not self._n2_relation_is_created:
            self.unit.status = BlockedStatus("Waiting for n2 relation to be created")
            return
        if not self._config_file_is_written:
            self.unit.status = WaitingStatus("Waiting for config file to be written")
            return
        self._execute_replace_ip_route()
        self.unit.status = ActiveStatus()

    @property
    def _n2_relation_is_created(self) -> bool:
        return self._relation_created("n2")

    def _relation_created(self, relation_name: str) -> bool:
        """Returns whether a given Juju relation was crated.

        Args:
            relation_name (str): Relation name

        Returns:
            str: Whether the relation was created.
        """
        if not self.model.get_relation(relation_name):
            return False
        return True

    def _execute_replace_ip_route(self) -> None:
        process = self._container.exec(
            command=["ip", "route", "replace", "192.168.252.3/32", "via", "192.168.251.1"],
            timeout=300,
            environment=self._environment_variables,
        )
        try:
            process.wait_output()
        except ExecError as e:
            logger.error("Exited with code %d. Stderr:", e.exit_code)
            for line in e.stderr.splitlines():
                logger.error("    %s", line)
            raise e
        logger.info("Replaced ip route")

    def _on_start_simulation_action(self, event: ActionEvent) -> None:
        if not self._gnbsim_service_is_running:
            event.fail(message="Service should be running for the user to be created")
            return
        logger.info("Starting simulation")
        process = self._container.exec(
            command=["./gnbsim", "--cfg", f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}"],
            timeout=300,
            environment=self._environment_variables,
        )
        try:
            process.wait_output()
        except ExecError as e:
            logger.error("Exited with code %d. Stderr:", e.exit_code)
            for line in e.stderr.splitlines():
                logger.error("    %s", line)
            raise e
        logger.info("Successfully ran simulation")

    @property
    def _gnbsim_service_is_running(self) -> bool:
        try:
            gnbsim_service = self._container.get_service(service_name=self._service_name)
        except ModelError:
            logger.info("gnbsim service not found")
            return False
        if not gnbsim_service.is_running():
            logger.info("gnbsim service is not running")
            return False
        return True

    @property
    def _environment_variables(self) -> dict:
        """Returns the environment variables for the workload service."""
        return {
            "MEM_LIMIT": "1Gi",
            "POD_IP": str(self._pod_ip),
        }

    @property
    def _pod_ip(self) -> Optional[IPv4Address]:
        """Get the IP address of the Kubernetes pod."""
        return IPv4Address(check_output(["unit-get", "private-address"]).decode().strip())


if __name__ == "__main__":
    main(GNBSIMOperatorCharm)
