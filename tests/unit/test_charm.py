# Copyright 2022 Guillaume Belanger
# See LICENSE file for licensing details.

import unittest
from unittest.mock import Mock, patch

from ops import testing
from ops.model import ActiveStatus

from charm import GNBSIMOperatorCharm


class TestCharm(unittest.TestCase):
    @patch("lightkube.core.client.GenericSyncClient")
    @patch(
        "charm.KubernetesServicePatch",
        lambda charm, ports: None,
    )
    def setUp(self, patch_k8s_client):
        self.namespace = "whatever"
        self.harness = testing.Harness(GNBSIMOperatorCharm)
        self.harness.set_model_name(name=self.namespace)
        self.addCleanup(self.harness.cleanup)
        self.harness.begin()

    @patch("kubernetes.Kubernetes.create_network_attachment_definition")
    def test_given_when_on_install_then_network_attachment_definition_is_created(
        self, patch_create_network_attachment_definition
    ):
        self.harness.charm._on_install(event=Mock())

        patch_create_network_attachment_definition.assert_called_once()

    @patch("kubernetes.Kubernetes.delete_network_attachment_definition")
    def test_given_when_on_remove_then_network_attachment_definition_is_deleted(
        self, patch_delete_network_attachment_definition
    ):
        self.harness.charm._on_remove(event=Mock())

        patch_delete_network_attachment_definition.assert_called_once()

    @patch("ops.model.Container.push")
    def test_given_use_default_config_when_config_changed_then_config_file_is_written(
        self,
        patch_push,
    ):
        self.harness.set_can_connect(container="gnbsim", val=True)

        self.harness.update_config({"use-default-config": True})

        patch_push.assert_called_with(
            path="/etc/gnbsim/gnb.conf",
            source='configuration:\n  customProfiles:\n    customProfiles1:\n      defaultAs: 192.168.250.1\n      enable: false\n      execInParallel: false\n      gnbName: gnb1\n      iterations:\n      - "1": REGISTRATION-PROCEDURE 5\n        "2": PDU-SESSION-ESTABLISHMENT-PROCEDURE 5\n        "3": USER-DATA-PACKET-GENERATION-PROCEDURE 10\n        name: iteration1\n        next: iteration2\n      - "1": AN-RELEASE-PROCEDURE 10\n        "2": UE-TRIGGERED-SERVICE-REQUEST-PROCEDURE 5\n        name: iteration2\n        next: iteration3\n        repeat: 0\n      - "1": UE-INITIATED-DEREGISTRATION-PROCEDURE 10\n        name: iteration3\n        next: quit\n        repeat: 0\n      key: 5122250214c33e723a5dd523fc145fc0\n      opc: 981d464c7c52eb6e5036234984ad0bcf\n      plmnId:\n        mcc: 208\n        mnc: 93\n      profileName: custom1\n      profileType: custom\n      sequenceNumber: 16f3b3f70fc2\n      startImsi: 208930100007487\n      startiteration: iteration1\n      stepTrigger: false\n      ueCount: 30\n  execInParallel: false\n  gnbs:\n    gnb1:\n      defaultAmf:\n        hostName: amf\n        port: 38412\n      globalRanId:\n        gNbId:\n          bitLength: 24\n          gNBValue: "000102"\n        plmnId:\n          mcc: 208\n          mnc: 93\n      n2Port: 9487\n      n3IpAddr: 192.168.251.5\n      n3Port: 2152\n      name: gnb1\n      supportedTaList:\n      - broadcastPlmnList:\n        - plmnId:\n            mcc: 208\n            mnc: 93\n          taiSliceSupportList:\n          - sd: "010203"\n            sst: 1\n        tac: "000001"\n    gnb2:\n      defaultAmf:\n        hostName: amf\n        port: 38412\n      globalRanId:\n        gNbId:\n          bitLength: 24\n          gNBValue: "000112"\n        plmnId:\n          mcc: 208\n          mnc: 93\n      n2Port: 9488\n      n3IpAddr: 192.168.251.6\n      n3Port: 2152\n      name: gnb2\n      supportedTaList:\n      - broadcastPlmnList:\n        - plmnId:\n            mcc: 208\n            mnc: 93\n          taiSliceSupportList:\n          - sd: "010203"\n            sst: 1\n        tac: "000001"\n  goProfile:\n    enable: false\n    port: 5000\n  httpServer:\n    enable: false\n    ipAddr: POD_IP\n    port: 6000\n  networkTopo:\n  - upfAddr: 192.168.252.3/32\n    upfGw: 192.168.251.1\n  profiles:\n  - defaultAs: 192.168.250.1\n    enable: false\n    execInParallel: false\n    gnbName: gnb1\n    key: 5122250214c33e723a5dd523fc145fc0\n    opc: 981d464c7c52eb6e5036234984ad0bcf\n    perUserTimeout: 100\n    plmnId:\n      mcc: 208\n      mnc: 93\n    profileName: profile1\n    profileType: register\n    sequenceNumber: 16f3b3f70fc2\n    startImsi: 208930100007487\n    ueCount: 5\n  - dataPktCount: 5\n    defaultAs: 192.168.250.1\n    enable: true\n    execInParallel: false\n    gnbName: gnb1\n    key: 5122250214c33e723a5dd523fc145fc0\n    opc: 981d464c7c52eb6e5036234984ad0bcf\n    perUserTimeout: 100\n    plmnId:\n      mcc: 208\n      mnc: 93\n    profileName: profile2\n    profileType: pdusessest\n    sequenceNumber: 16f3b3f70fc2\n    startImsi: 208930100007487\n    ueCount: 5\n  - defaultAs: 192.168.250.1\n    enable: false\n    execInParallel: false\n    gnbName: gnb1\n    key: 5122250214c33e723a5dd523fc145fc0\n    opc: 981d464c7c52eb6e5036234984ad0bcf\n    perUserTimeout: 100\n    plmnId:\n      mcc: 208\n      mnc: 93\n    profileName: profile3\n    profileType: anrelease\n    sequenceNumber: 16f3b3f70fc2\n    startImsi: 208930100007497\n    ueCount: 5\n  - defaultAs: 192.168.250.1\n    enable: false\n    execInParallel: false\n    gnbName: gnb1\n    key: 5122250214c33e723a5dd523fc145fc0\n    opc: 981d464c7c52eb6e5036234984ad0bcf\n    perUserTimeout: 100\n    plmnId:\n      mcc: 208\n      mnc: 93\n    profileName: profile4\n    profileType: uetriggservicereq\n    sequenceNumber: 16f3b3f70fc2\n    startImsi: 208930100007497\n    ueCount: 5\n  - defaultAs: 192.168.250.1\n    enable: false\n    execInParallel: false\n    gnbName: gnb1\n    key: 5122250214c33e723a5dd523fc145fc0\n    opc: 981d464c7c52eb6e5036234984ad0bcf\n    perUserTimeout: 100\n    plmnId:\n      mcc: 208\n      mnc: 93\n    profileName: profile5\n    profileType: deregister\n    sequenceNumber: 16f3b3f70fc2\n    startImsi: 208930100007497\n    ueCount: 5\n  - defaultAs: 192.168.250.1\n    enable: false\n    execInParallel: false\n    gnbName: gnb1\n    key: 5122250214c33e723a5dd523fc145fc0\n    opc: 981d464c7c52eb6e5036234984ad0bcf\n    perUserTimeout: 100\n    plmnId:\n      mcc: 208\n      mnc: 93\n    profileName: profile6\n    profileType: nwtriggeruedereg\n    sequenceNumber: 16f3b3f70fc2\n    startImsi: 208930100007497\n    ueCount: 5\n  - defaultAs: 192.168.250.1\n    enable: false\n    execInParallel: false\n    gnbName: gnb1\n    key: 5122250214c33e723a5dd523fc145fc0\n    opc: 981d464c7c52eb6e5036234984ad0bcf\n    perUserTimeout: 100\n    plmnId:\n      mcc: 208\n      mnc: 93\n    profileName: profile7\n    profileType: uereqpdusessrelease\n    sequenceNumber: 16f3b3f70fc2\n    startImsi: 208930100007497\n    ueCount: 5\n  runConfigProfilesAtStart: true\ninfo:\n  description: gNodeB sim initial configuration\n  version: 1.0.0\nlogger:\n  logLevel: trace\n',  # noqa: E501
        )

    @patch("charm.check_output")
    @patch("ops.model.Container.exec")
    @patch("ops.model.Container.exists")
    def test_given_config_file_is_written_when_pebble_ready_then_ip_route_is_replaced(
        self,
        patch_exists,
        patch_exec,
        patch_check_output,
    ):
        pod_ip = "1.2.3.4"
        patch_exists.return_value = True
        patch_check_output.return_value = pod_ip.encode()

        self.harness.container_pebble_ready(container_name="gnbsim")

        patch_exec.assert_called_with(
            command=["ip", "route", "replace", "192.168.252.3/32", "via", "192.168.251.1"],
            timeout=30,
            environment={"MEM_LIMIT": "1Gi", "POD_IP": pod_ip},
        )

    @patch("charm.check_output")
    @patch("ops.model.Container.exec", new=Mock())
    @patch("ops.model.Container.exists")
    def test_given_config_file_is_written_when_pebble_ready_then_status_is_active(
        self, patch_exists, patch_check_output
    ):
        patch_exists.return_value = True
        patch_check_output.return_value = b"1.2.3.4"

        self.harness.container_pebble_ready("gnbsim")

        self.assertEqual(self.harness.model.unit.status, ActiveStatus())
