from lxml import etree

from ncclient.xml_ import *
from ncclient.operations.rpc import RPC
from ncclient.operations import util
from ncclient.operations.errors import OperationError


"""
Typical sequence for communicating with NSO

* hello (capability exchange)
* (optional) lock
* start-transaction
* edit-config (RFC RPC + custom parameters)
* prepare-transaction
* commit-transaction OR abort-transaction
* (optional) unlock

NOTE:

The following RFC RPCs are modified:
* commit
* edit-config
* copy-config
* get
* get-config

TODO - need to override those (done for edit.rpc not for retrieve.rpc)
"""


def add_service_commit_params(node, no_deploy=False, reconcile=None):
    """
    Convenience method to add service-commit-params to various RPCs,

    The method should be used this way:
        the RPC implementing the grouping takes as input the no_deploy
        and reconcile parameters

        Then it calls this method with the Node node on which to add
        the service-commit-params if they are configured.
    """
    if no_deploy:
        sub_ele_ns(node, "no-deploy", ns=TAILF_NS_NCS)

    if reconcile is not None:
        if reconcile not in ["keep-non-service-config", "discard-non-service-config"]:
            raise OperationError("Wrong reconcile argument: " + reconcile)
        rec_node = sub_ele_ns(node, "reconcile", ns=TAILF_NS_NCS)
        sub_ele_ns(rec_node, reconcile, ns=TAILF_NS_NCS)


def add_rollback_meta_data(node, rollback_label=None, rollback_comment=None):
    """
    Convenience method to add rollback-meta-data to various RPCs

    TODO: check if any character in comment/label would make this fail


    to be added to:
         * prepare-transaction
         * edit-config (if candidate support)
         * commit (if candidate support)
    """
    if rollback_label:
        sub_ele_ns(node, "label", ns=TAILF_NS_ROLLBACK).text = rollback_label
    if rollback_comment:
        sub_ele_ns(node, "comment", ns=TAILF_NS_ROLLBACK).text = rollback_comment


def add_with_transaction_id(node, with_transaction_id=False):
    """
    Convenience method to add with-transaction-id to a variety of RPCs

    to be added to:
        * edit-config
        * copy-config
        * commit
        * commit-transaction
    """
    if with_transaction_id:
        sub_ele_ns(node, "with-transaction-id", ns=TAILF_NS_WTI)


def add_with_inactive(node, with_inactive=True):
    """
    Setting default True because it seems that is was NSO does

    to be added to:
        * get
        * get-config
        * edit-config
        * copy-config
        * start-transaction
    """
    if with_inactive:
        sub_ele_ns(node, "with-inactive", ns=TAILF_NS_INACTIVE)


###############################################################################################
#                    NSO Specific RPCs
###############################################################################################
class StartTransaction(RPC):
    def request(self, target='candidate', with_inactive=True):
        """
        start-transaction

        Note: in NSO 5.3 according to model, target can be in
              [startup, running, candidate]
        """
        node = new_ele_ns("start-transaction", ns=TAILF_NS)
        target_node = sub_ele_ns(node, "target", ns=TAILF_NS)
        sub_ele_ns(target_node, target, ns=TAILF_NS)
        # TODO check this node.append(util.datastore_or_url("target", target, self._assert))
        add_with_inactive(node, with_inactive)
        return self._request(node)


class PrepareTransaction(RPC):
    def request(self, dry_run=None, dry_run_reverse=False, no_deploy=False, reconcile=None,
                rollback_label=None, rollback_comment=None):
        """
        prepare-transaction
        dry-run: can be None / native / cli / xml
        no_deploy: can be False / True
        reconcile: can be None / keep-non-service-config / discard-non-service-config
        """
        node = new_ele_ns("prepare-transaction", ns=TAILF_NS)
        if dry_run is not None:
            if dry_run not in ["native", "cli", "xml"]:
                raise OperationError("Wrong dry-run argument: " + dry_run)
            dr_node = sub_ele_ns(node, "dry-run", ns=TAILF_NS_NCS)
            sub_ele_ns(dr_node, "outformat", ns=TAILF_NS_NCS).text = dry_run

            if dry_run_reverse:
                sub_ele_ns(dr_node, "reverse", ns=TAILF_NS_NCS)

        add_service_commit_params(node, no_deploy=no_deploy, reconcile=reconcile)
        add_rollback_meta_data(node, rollback_label, rollback_comment)

        return self._request(node)


class CommitTransaction(RPC):
    def request(self, with_transaction_id=None):
        """
        commit-transaction
        """
        node = new_ele_ns("commit-transaction", ns=TAILF_NS)
        add_with_transaction_id(node, with_transaction_id)
        return self._request(node)


class AbortTransaction(RPC):
    def request(self):
        """
        abort-transaction
        """
        node = new_ele_ns("abort-transaction", ns=TAILF_NS)
        return self._request(node)


###############################################################################################
#                    Overriden Standard RPCs with NSO options
###############################################################################################
class EditConfig(RPC):
    "`edit-config` RPC"

    def request(self, config, format='xml', target='candidate', default_operation=None,
                test_option=None, error_option=None, no_deploy=False, reconcile=None,
                rollback_label=None, rollback_comment=None, with_transaction_id=False,
                with_inactive=False):
        """Loads all or part of the specified *config* to the *target* configuration datastore.

        *target* is the name of the configuration datastore being edited

        *config* is the configuration, which must be rooted in the `config` element. It can be specified either as a string or an :class:`~xml.etree.ElementTree.Element`.

        *default_operation* if specified must be one of { `"merge"`, `"replace"`, or `"none"` }

        *test_option* if specified must be one of { `"test_then_set"`, `"set"` }

        *error_option* if specified must be one of { `"stop-on-error"`, `"continue-on-error"`, `"rollback-on-error"` }

        The `"rollback-on-error"` *error_option* depends on the `:rollback-on-error` capability.
        """
        node = new_ele("edit-config")
        node.append(util.datastore_or_url("target", target, self._assert))
        if default_operation is not None:
        # TODO: check if it is a valid default-operation
            sub_ele(node, "default-operation").text = default_operation
        if test_option is not None:
            self._assert(':validate')
            sub_ele(node, "test-option").text = test_option
        if error_option is not None:
            if error_option == "rollback-on-error":
                self._assert(":rollback-on-error")
            sub_ele(node, "error-option").text = error_option

        # NSO
        # TODO add commit params
        add_service_commit_params(node, no_deploy, reconcile)
        # TODO Should check for candidate for rollback
        add_rollback_meta_data(node, rollback_label, rollback_comment)
        add_with_transaction_id(node, with_transaction_id)
        add_with_inactive(node, with_inactive)

        if format == 'xml':
            # TODO - understand why namespace is not propagated
            config_node = validated_element(config, ("config", qualify("config")))
            ns = "{urn:ietf:params:xml:ns:netconf:base:1.0}"
            config_node.tag = ns + "config"
            node.append(config_node)
        if format == 'text':
            config_text = sub_ele(node, "config-text")
            sub_ele(config_text, "configuration-text").text = config


        return self._request(node)


class CopyConfig(RPC):
    "`copy-config` RPC"

    def request(self, source, target, no_deploy=False, reconcile=None,
                with_transaction_id=False, with_inactive=False):
        """Create or replace an entire configuration datastore with the contents of another complete
        configuration datastore.

        *source* is the name of the configuration datastore to use as the source of the copy operation or `config` element containing the configuration subtree to copy

        *target* is the name of the configuration datastore to use as the destination of the copy operation

        :seealso: :ref:`srctarget_params`"""
        node = new_ele("copy-config")
        node.append(util.datastore_or_url("target", target, self._assert))

        try:
            # datastore name or URL
            node.append(util.datastore_or_url("source", source, self._assert))
        except Exception:
            # `source` with `config` element containing the configuration subtree to copy
            node.append(validated_element(source, ("source", qualify("source"))))

        # NSO
        # TODO add commit params
        add_service_commit_params(node, no_deploy, reconcile)
        add_with_transaction_id(node, with_transaction_id)
        add_with_inactive(node, with_inactive)

        return self._request(node)

'''
# Not augmenting it now but should add datastore to support nmda
class Validate(RPC):
    "`validate` RPC. Depends on the `:validate` capability."

    DEPENDS = [':validate']

    def request(self, source="candidate"):
        """Validate the contents of the specified configuration.

        *source* is the name of the configuration datastore being validated or `config` element containing the configuration subtree to be validated

        :seealso: :ref:`srctarget_params`"""
        node = new_ele("validate")
        if type(source) is str:
            src = util.datastore_or_url("source", source, self._assert)
        else:
            validated_element(source, ("config", qualify("config")))
            src = new_ele("source")
            src.append(source)
        node.append(src)
        return self._request(node)
'''


class Commit(RPC):
    "`commit` RPC. Depends on the `:candidate` capability, and the `:confirmed-commit`."

    DEPENDS = [':candidate']

    def request(self, confirmed=False, timeout=None, persist=None, persist_id=None,
                no_deploy=False, reconcile=None, rollback_label=None, rollback_comment=None,
                with_transaction_id=False):
        """Commit the candidate configuration as the device's new current configuration. Depends on the `:candidate` capability.

        A confirmed commit (i.e. if *confirmed* is `True`) is reverted if there is no followup commit within the *timeout* interval. If no timeout is specified the confirm timeout defaults to 600 seconds (10 minutes). A confirming commit may have the *confirmed* parameter but this is not required. Depends on the `:confirmed-commit` capability.

        *confirmed* whether this is a confirmed commit

        *timeout* specifies the confirm timeout in seconds

        *persist* make the confirmed commit survive a session termination, and set a token on the ongoing confirmed commit

        *persist_id* value must be equal to the value given in the <persist> parameter to the original <commit> operation.
        """
        node = new_ele("commit")
        if (confirmed or persist) and persist_id:
            raise OperationError("Invalid operation as confirmed or persist cannot be present with persist-id")
        if confirmed:
            self._assert(":confirmed-commit")
            sub_ele(node, "confirmed")
            if timeout is not None:
                sub_ele(node, "confirm-timeout").text = timeout
            if persist is not None:
                sub_ele(node, "persist").text = persist
        if persist_id:
            sub_ele(node, "persist-id").text = persist_id

        # NSO
        # TODO add commit params
        add_service_commit_params(node, no_deploy, reconcile)
        # TODO Should check for candidate for rollback
        add_rollback_meta_data(node, rollback_label, rollback_comment)
        add_with_transaction_id(node, with_transaction_id)

        return self._request(node)
