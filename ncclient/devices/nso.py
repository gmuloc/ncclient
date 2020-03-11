"""
Handler for Cisco NSO (TAIL-F NCS) device specific information.

Note that for proper import, the classname has to be:

    "<Devicename>DeviceHandler"

...where <Devicename> is something like "Default", "Nexus", etc.

All device-specific handlers derive from the DefaultDeviceHandler, which implements the
generic information needed for interaction with a Netconf server.

"""


from .default import DefaultDeviceHandler

from ncclient.operations.third_party.tailf.rpc import StartTransaction, PrepareTransaction
from ncclient.operations.third_party.tailf.rpc import AbortTransaction, CommitTransaction
from ncclient.operations.third_party.tailf.rpc import Commit, EditConfig, CopyConfig

from ncclient.xml_ import BASE_NS_1_0


class NsoDeviceHandler(DefaultDeviceHandler):
    """
    Cisco NSO handler for device specific information.

    """
    def __init__(self, device_params):
        super(NsoDeviceHandler, self).__init__(device_params)

    def add_additional_operations(self):
        """
        Add vendor operations to NSO device
        """
        dict = {}
        dict["start_transaction"] = StartTransaction
        dict["prepare_transaction"] = PrepareTransaction
        dict["abort_transaction"] = AbortTransaction
        dict["commit_transaction"] = CommitTransaction
        dict["commit"] = Commit
        dict["edit_config"] = EditConfig
        dict["copy_config"] = CopyConfig
        return dict

    def get_xml_base_namespace_dict(self):
        """
        TODO confirm if needed

        Some problems with empty namespace
        """
        # default namespace
        return {None: BASE_NS_1_0}
