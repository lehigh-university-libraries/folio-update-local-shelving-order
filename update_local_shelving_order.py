from configparser import ConfigParser
from folioclient import FolioClient  # pip install folioclient
import logging

# import os
import requests

logger = None
config = None
shelving_order_item_note_type_id = None


def main():
    init()
    run()


def init():
    init_config()
    init_logging()
    init_folio()


def init_config():
    global config
    config = ConfigParser()
    config.read_file(open("config/config.properties"))
    # dir = os.path.dirname(__file__)
    # dir = os.path.dirname(dir)
    # config_path = os.path.join(dir, "config", "config.properties")
    # with open(config_path, "r", encoding="utf-8") as f:
    #     config.read_file(f)


def init_logging():
    logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s")
    global logger
    logger = logging.getLogger(__name__)
    logger.setLevel(config["Logging"]["level"].upper())


def init_folio():
    def init_folio_internal(folio):
        init_item_note_type(folio)

    run_with_folio_client(init_folio_internal)


def init_item_note_type(folio):
    result = folio.folio_get(
        path="/item-note-types",
        key="itemNoteTypes",
        query_params={
            "limit": 1000,
        },
    )
    item_note_types = {
        item_note_type["name"]: item_note_type for item_note_type in result
    }

    global shelving_order_item_note_type_id
    note_type = config["FOLIO"]["shelving_order_item_note_type"]
    shelving_order_item_note_type_id = item_note_types[note_type]["id"]


def run():
    total = load_count_report()
    logger.info("%i items need local shelving order.", total)

    offset = int(config["ShelvingOrderService"]["start_offset"])
    while True:
        logger.info("Loading items from offset %i", offset)
        report_items = load_items_report_batch(offset)
        if not report_items:
            logger.info("No more items need local shelving order")
            break
        for report_item in report_items:
            call_number = (
                report_item["item_call_number"]
                if report_item["item_call_number"]
                else report_item["hr_call_number"]
            )
            local_shelving_order = generate_local_shelving_order(call_number)
            update_item(report_item, local_shelving_order)
        offset += int(config["MetaDB"]["batch_size"])


def load_count_report():
    def load_count_internal(folio):
        result = folio.folio_post(
            path="/ldp/db/reports",
            payload={
                "url": config["MetaDB"]["items_count_url"],
            },
        )
        total = result["records"][0]["total"]
        return total

    return run_with_folio_client(load_count_internal)


def load_items_report_batch(offset):
    def load_items_internal(folio):
        result = folio.folio_post(
            path="/ldp/db/reports",
            payload={
                "url": config["MetaDB"]["items_query_url"],
                "params": {
                    "query_offset": str(offset),
                    "query_limit": config["MetaDB"]["batch_size"],
                },
            },
        )
        records = result["records"]
        return records

    return run_with_folio_client(load_items_internal)


def generate_local_shelving_order(call_number):
    base_url = config["ShelvingOrderService"]["base_url"]
    timeout = int(config["ShelvingOrderService"]["timeout"])
    url = base_url + call_number  # no encoding needed?
    response = requests.get(url, timeout=timeout)

    if response.status_code == 200:
        return response.text
    else:
        raise Exception("Exception calling shelving order service " + response.text)


def update_item(report_item, local_shelving_order):
    def update_item_internal(folio):
        if report_item["id"] in [
            "7b4c277c-d474-4b06-a470-5c5c92be84f4",
            "7b56cc69-8e7c-497c-8486-f23a1da0f4e5",
            "ff264b56-7e66-4093-93d0-c7809b93eb12",
            "87501c96-327b-4e66-b0fb-6adb8e332f68",
            "e7dc49c3-015b-4e09-9f35-6b51fd35d141",
        ]:
            logger.warn("skipping id of item known bad: %s", report_item["id"])
            return

        item = load_item(folio, report_item["id"])

        # Most items have barcodes, but not all. This is used purely for output so HRID is also ok.
        barcode = item["barcode"] if "barcode" in item else "HRID:" + item["hrid"]

        for note in list(item["notes"]):
            # The MetaDB query uses a folio_derived schema table for the item note, which is only
            # updated daily. Therefore if the app is run a second time in the same day, it will
            # load items that already have these notes, which the MetaDB query didn't yet know.
            # Thus, skip those items.
            # In the future it may be necessary to handle changed call numbers, where instead of
            # skipping these items we'd have to replace the existing note.
            if note["itemNoteTypeId"] == shelving_order_item_note_type_id:
                if config.getboolean("ShelvingOrderService", "overwrite"):
                    # Delete old note before adding new one below
                    item["notes"].remove(note)
                else:
                    # Skip items that already have this note
                    logger.debug(
                        "Skipping item with barcode %s as it already has a local shelving order",
                        barcode,
                    )
                    return
        item["notes"].append(
            {
                "itemNoteTypeId": shelving_order_item_note_type_id,
                "note": local_shelving_order,
                "staffOnly": True,
            }
        )
        save_item(folio, item)
        logger.debug(
            "Updated item with barcode %s with local shelving order %s",
            barcode,
            local_shelving_order,
        )

    return run_with_folio_client(update_item_internal)


def load_item(folio, item_id):
    item = folio.folio_get(path=f"/inventory/items/{item_id}")
    return item


def save_item(folio, item):
    folio.folio_put(
        path=f"/inventory/items/{item['id']}",
        payload=item,
    )


def run_with_folio_client(fn):
    folio_config = config["FOLIO"]

    with FolioClient(
        folio_config["base_url"],
        folio_config["tenant"],
        folio_config["username"],
        folio_config["password"],
    ) as folio:
        return fn(folio)


if __name__ == "__main__":
    main()
