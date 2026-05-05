import argparse
from configparser import ConfigParser
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from folioclient import FolioClient  # pip install folioclient
import logging
import smtplib
import time
import traceback

# import os
import requests

SPEED_FILE = "seconds_per_record.txt"

logger = None
config = None
shelving_order_item_note_type_id = None
call_number_prefix = None
start_offset = 0
overwrite = False
args = None


def main():
    init()
    try:
        run()
        send_email(
            f"Local shelving order updated for {email_subject_context()}",
            "Run completed successfully.",
        )
    except Exception:
        send_email(
            f"Error updating local shelving order for {email_subject_context()}",
            traceback.format_exc(),
        )
        raise


def init():
    init_args()
    init_config()
    init_logging()
    init_folio()
    logger.info("Running with parameters: %s", vars(args))


def init_args():
    global call_number_prefix, start_offset, overwrite, args
    parser = argparse.ArgumentParser()
    parser.add_argument("--call-number-prefix", default=None)
    parser.add_argument("--start-offset", type=int, default=0)
    parser.add_argument("--overwrite", action="store_true", default=False)
    args = parser.parse_args()
    call_number_prefix = args.call_number_prefix
    start_offset = args.start_offset
    overwrite = args.overwrite


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
    speed = load_speed()
    items_to_process = total - start_offset
    if speed and items_to_process > 0:
        logger.info(
            "%i items need local shelving order. Estimated finish: %s",
            total,
            estimate_finish_time(items_to_process * speed),
        )
    else:
        logger.info("%i items need local shelving order.", total)

    offset = start_offset
    while True:
        items_remaining = total - offset
        if speed and items_remaining > 0:
            logger.info(
                "Loading items from offset %i, estimated finish: %s",
                offset,
                estimate_finish_time(items_remaining * speed),
            )
        else:
            logger.info("Loading items from offset %i", offset)

        batch_start = time.time()
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

        speed = round(time.time() - batch_start, 2) / len(report_items)
        if len(report_items) >= 100:
            save_speed(speed)
        offset += int(config["MetaDB"]["batch_size"])


def load_count_report():
    def load_count_internal(folio):
        payload = {"url": config["MetaDB"]["items_count_url"]}
        if call_number_prefix:
            payload["params"] = {"call_number_prefix": call_number_prefix}
        result = folio.folio_post(path="/ldp/db/reports", payload=payload)
        return result["records"][0]["total"]

    return run_with_folio_client(load_count_internal)


def load_items_report_batch(offset):
    def load_items_internal(folio):
        params = {
            "query_offset": str(offset),
            "query_limit": config["MetaDB"]["batch_size"],
        }
        if call_number_prefix:
            params["call_number_prefix"] = call_number_prefix
        result = folio.folio_post(
            path="/ldp/db/reports",
            payload={"url": config["MetaDB"]["items_query_url"], "params": params},
        )
        return result["records"]

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
                if overwrite:
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


def load_speed():
    try:
        with open(SPEED_FILE) as f:
            return float(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def save_speed(speed):
    with open(SPEED_FILE, "w") as f:
        f.write(str(speed))


def estimate_finish_time(seconds):
    return (datetime.now() + timedelta(seconds=int(seconds))).strftime("%Y-%m-%d %H:%M:%S")


def email_subject_context():
    prefix_part = call_number_prefix if call_number_prefix else "all"
    offset = start_offset
    return f"prefix={prefix_part}, offset={offset}"


def send_email(subject, body):
    if "Email" not in config:
        return
    email_config = config["Email"]
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = email_config["from_address"]
    msg["To"] = email_config["to_address"]
    with smtplib.SMTP(
        email_config["smtp_host"], int(email_config["smtp_port"])
    ) as smtp:
        smtp.sendmail(
            email_config["from_address"], [email_config["to_address"]], msg.as_string()
        )


if __name__ == "__main__":
    main()
