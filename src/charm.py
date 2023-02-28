#!/usr/bin/env python3
# Copyright 2022 Guillaume Belanger
# See LICENSE file for licensing details.

"""Charmed operator for the 5G OMEC GNBSIM service."""

import logging
from ipaddress import IPv4Address
from subprocess import check_output
from typing import Optional, Union

from charms.observability_libs.v1.kubernetes_service_patch import KubernetesServicePatch
from lightkube.models.core_v1 import ServicePort
from ops.charm import (
    ActionEvent,
    CharmBase,
    ConfigChangedEvent,
    InstallEvent,
    PebbleReadyEvent,
    RemoveEvent,
)
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, MaintenanceStatus, WaitingStatus
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
        self._kubernetes = Kubernetes(namespace=self.model.name)
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.gnbsim_pebble_ready, self._on_gnbsim_pebble_ready)
        self.framework.observe(self.on.start_simulation_action, self._on_start_simulation_action)
        self.framework.observe(self.on.remove, self._on_remove)
        self._service_patcher = KubernetesServicePatch(
            charm=self,
            ports=[
                ServicePort(name="ngapp", port=38412, protocol="SCTP"),
                ServicePort(name="http-api", port=6000),
            ],
        )

    def _on_config_changed(self, event: ConfigChangedEvent) -> None:
        if not self._container.can_connect():
            self.unit.status = WaitingStatus("Waiting for container to be ready")
            event.defer()
            return
        if self._use_default_config:
            self._write_default_config()
            self._on_gnbsim_pebble_ready(event)

    def _on_install(self, event: InstallEvent) -> None:
        """Handle the install event."""
        self._kubernetes.create_network_attachment_definition()
        self._kubernetes.patch_statefulset(statefulset_name=self.app.name)

    def _write_default_config(self) -> None:
        with open("src/files/default_config.yaml", "r") as f:
            content = f.read()
        self._container.push(source=content, path=f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}")
        logger.info("Default config file written")

    def _on_remove(self, event: RemoveEvent) -> None:
        """Handle the remove event."""
        self._kubernetes.delete_network_attachment_definition()

    @property
    def _use_default_config(self) -> bool:
        return bool(self.model.config["use-default-config"])

    @property
    def _config_file_is_written(self) -> bool:
        if not self._container.exists(f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}"):
            logger.info(f"Config file is not written: {CONFIG_FILE_NAME}")
            return False
        logger.info("Config file is written")
        return True

    def _on_gnbsim_pebble_ready(self, event: Union[PebbleReadyEvent, ConfigChangedEvent]) -> None:
        """Handle the pebble ready event."""
        if not self._container.can_connect():
            self.unit.status = WaitingStatus("Waiting for container to be ready")
            event.defer()
            return
        if not self._kubernetes.statefulset_is_patched(statefulset_name=self.app.name):
            self.unit.status = WaitingStatus("Waiting for statefulset to be patched")
            event.defer()
            return
        if not self._config_file_is_written:
            if self._use_default_config:
                self.unit.status = WaitingStatus("Waiting for config file to be written")
                event.defer()
                return
            else:
                self.unit.status = BlockedStatus(
                    "Use `juju scp` to copy the config file to the unit and run the `configure-network` action"  # noqa: E501, W505
                )
                return
        self._execute_replace_ip_route()
        self.unit.status = ActiveStatus()

    def _execute_replace_ip_route(self) -> None:
        process = self._container.exec(
            command=["ip", "route", "replace", "192.168.252.3/32", "via", "192.168.251.1"],
            timeout=30,
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
        if not self._container.can_connect():
            event.fail("Container is not ready")
            return
        if not self._config_file_is_written:
            event.fail("Config file is not written")
            return
        self.unit.status = MaintenanceStatus("Starting simulation")
        process = self._container.exec(
            command=["/gnbsim/bin/gnbsim", "--cfg", f"{BASE_CONFIG_PATH}/{CONFIG_FILE_NAME}"],
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
        event.set_results({"success": "true"})
        self.unit.status = ActiveStatus("Successfully ran simulation")

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
