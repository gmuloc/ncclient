#!/usr/bin/env python
import logging
import sys

from lxml import etree


from ncclient import manager
from ncclient.xml_ import *

EDIT_CONFIG = """
<config>
    <devices xmlns="http://tail-f.com/ns/ncs">
      <authgroups>
        <group>
          <name>example</name>
          <default-map>
            <remote-name>example</remote-name>
            <remote-password>example</remote-password>
          </default-map>
        </group>
      </authgroups>
    </devices>
</config>
"""


def connect(host, port, user, password):
    conn = manager.connect(host=host,
                           port=port,
                           username=user,
                           password=password,
                           timeout=60,
                           device_params={'name': 'nso'},
                           hostkey_verify=False,
                           allow_agent=False,
                           look_for_keys=False)

    logging.info("Locking configuration")
    lock_result = conn.lock(target="running")
    logging.debug(lock_result)

    # start-transaction rpc
    logging.info("Prepare Transaction")
    start_result = conn.start_transaction(target="running")
    logging.debug(start_result)

    # edit-config
    payload = EDIT_CONFIG
    # logging.debug(to_xml(config))
    logging.info("Edit Config")
    edit_result = conn.edit_config(config=payload, target="running",
                                   test_option="test-then-set",
                                   error_option="rollback-on-error",
                                   with_inactive=True)
    logging.debug(edit_result)

    # prepare-transaction rpc
    logging.info("Prepare Transaction")
    prepare_result = conn.prepare_transaction(dry_run="xml")
    logging.debug(prepare_result)

    # abort rpc
    logging.info("Abort Transaction")
    abort_result = conn.abort_transaction()
    logging.debug(abort_result)

    # unlock
    logging.info("Unlocking configuration")
    unlock_result = conn.unlock(target="running")
    logging.debug(unlock_result)

    logging.info(to_xml(to_ele(prepare_result.xml), pretty_print=True))
    return prepare_result


if __name__ == '__main__':
    LOG_FORMAT = '%(asctime)s %(levelname)s %(filename)s:%(lineno)d %(message)s'
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=LOG_FORMAT)

    connect('127.0.0.1', 2022, 'admin', 'admin')
