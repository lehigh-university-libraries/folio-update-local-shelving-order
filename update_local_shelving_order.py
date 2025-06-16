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
            # call_number = (
            #     report_item["item_call_number"]
            #     if report_item["item_call_number"]
            #     else report_item["hr_call_number"]
            # )
            # local_shelving_order = generate_local_shelving_order(call_number)
            local_shelving_order = None
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
            "017d1b3d-6bac-4962-a449-82efc3d1ea4a",
            "02f4e230-fdee-42da-b3e5-2b8bac23aeb0",
            "031d7909-82fb-4e36-85b6-4aa4caecefc7",
            "0715af48-cd92-46b9-8c4d-38bd1729e98d",
            "0a7fcf91-3fb2-4c88-ad0f-d67f38c6c0a5",
            "0deca2c5-bb76-4ee6-b95c-ceedb8dd9dda",
            "0f76c0d7-3713-441a-ae6f-c0114a7574b8",
            "0fbbba8d-c72b-4d80-b46e-cbbe9346d928",
            "13b2745f-da06-4023-9659-be0f54c4f788",
            "18fafc70-3a85-45c3-9e29-8855cf793ea9",
            "19595d0f-d24b-4513-9f55-ccdf135d1c96",
            "19ad16b0-0b68-46b1-b358-d81bca64cdf6",
            "1b4367eb-2b71-470b-9070-56889929d293",
            "1f9b3f5f-7e7f-43c9-aaeb-e14b02f9f6a9",
            "20907d00-1b94-4f71-9efe-a1670cde7c7d",
            "217d7f24-09a4-43d2-a840-37735c1e89f4",
            "2263dbc0-d4ba-405d-b275-7a562f8de70e",
            "226763e6-4eab-4414-82fa-3147faf4ff80",
            "28984743-b998-4ef6-8dbc-c065a80b74af",
            "29572d1e-78ec-4077-afa6-f7d5e2d3b610",
            "2c92d4bf-b34c-4b46-9721-866f591be519",
            "2da4b1e6-29c0-41ae-9d92-84a5a5bcb75e",
            "2e9239a2-8ace-4f0a-8f60-c09791b9099f",
            "2fb57cd5-b6df-4f6c-8290-a56e64653643",
            "31c0aaa1-bf34-45d4-92dd-2992621f68ef",
            "32e87780-fe43-4cb8-b637-910ad765a927",
            "34a32d6a-889c-414e-8e42-20efa44fafbf",
            "35d8d7df-39af-4b8e-a68c-38a11616a608",
            "3916968c-10cf-448c-81b9-4e641085103a",
            "3a367d36-a716-4f18-9e1a-125785f2ccdd",
            "3aee9573-e819-427f-b7c4-003cc07b1127",
            "3b89be3f-7d5a-45b5-8c65-8139f3b737f8",
            "3ff4b3e8-22d2-440b-a431-c47da29faef1",
            "4422c649-2a3b-44b6-817d-b5703219c51f",
            "44a8a172-276f-4222-8c5d-26beda773261",
            "48837d25-739b-4411-8f8a-d7f36b7afa92",
            "4884fdcc-be60-4bd7-b246-56e7acdc5573",
            "4e4fab1a-4f10-466f-9173-404a35679df9",
            "50a191e9-0709-43ef-a771-fc09d1540654",
            "51c11aa9-473a-4ae8-8bc9-c68662e6bf22",
            "52e56bb0-d1cb-4bd0-9418-c75f10c1225d",
            "56c4dbf8-98b6-4fb3-bd40-bf094448040c",
            "57c534a3-22e6-42a6-8251-c1a27d9d9062",
            "61f415bb-a07f-4fbe-8ea2-8882bd7af7c5",
            "621f85fa-cfbf-403d-8c08-50ed9203395f",
            "64124138-a8dc-4b93-bef5-28391b1c9840",
            "64645a20-3e22-4e30-a2a1-0c4015400c64",
            "6470690e-8582-44a8-8a6d-99f9aef328e9",
            "68ec6d8c-74dc-41fe-ba4e-6eec31dafa18",
            "6f96c6a0-48c2-475d-ac71-738ffcc12619",
            "7283aa2e-94c9-4496-88fb-25d7dec9d8df",
            "74b76e25-dd6a-4133-bc11-07b898e6a75a",
            "7b6096df-4cc1-46c0-be3f-51b7ec727d2a",
            "7eef63e8-5ab9-4d38-8a82-9e6bd38e1cee",
            "80029d7c-efbb-4e27-ab71-a5173dafad99",
            "816d63a3-6d61-4f87-9963-cda9346c78c2",
            "8318048d-0a51-45f9-826c-ecf1f4aa137b",
            "833c6e92-9701-4520-8d06-dc134834b4d5",
            "85bcb271-5db6-471a-8920-f895938834c6",
            "88192ad0-960d-4396-88c9-c3238144c580",
            "89cfd01e-3ba6-4650-9e9d-0dd9f2d06a11",
            "8b6b3c61-b259-4445-adca-4a6842a037eb",
            "902744f3-d6cb-46b6-a5b8-be3386f3d5ba",
            "91ae7fa1-bab3-4110-84f1-b01fda57e645",
            "959c2bd7-907e-4160-9833-fa7bcd3859ca",
            "98fb0fdf-5158-49c7-a443-a3acbf284919",
            "99a6dabe-c25c-410f-bfa8-e7df8eb364b0",
            "9a76821f-0ab0-4919-9605-d3f56f5a88b1",
            "9d514992-f172-4dd3-bdc5-38e111ee2659",
            "9d97612f-52fa-4d69-bc9e-2b096e6e9a22",
            "a02d9d6a-f54a-48b6-aea3-7690ea15e077",
            "a9a5bb7b-0b0d-40a9-815a-7c13215c71f8",
            "aa097d30-c451-4e37-aad9-b97dfd88fc46",
            "ac253b95-a949-4b07-85ee-28e71cd5ce84",
            "ad0de168-6496-4075-b8e5-cb8fe44c297a",
            "ad9bc372-4d79-4413-962b-b2e66cf7fc3d",
            "b21eea46-838f-41d8-a867-8a6856a0a501",
            "b2a15190-800c-4590-8201-0eb6ad68faf3",
            "b7848500-e3f6-4f37-8ceb-34bec0e80979",
            "b9234192-7aa9-40f8-9f6a-aecefb34cf5d",
            "ba967b2c-5dda-4502-8abe-89a6c9be3ac9",
            "bb5200f9-c71f-48e5-9169-9a8d1f2ca8f8",
            "bcadc496-547c-4235-94ec-988fe8592d04",
            "bf17783e-4fcf-4d00-a3f7-c43ef438c3f9",
            "bf3b00de-6a10-4dde-816f-1a32bd945390",
            "c32e8f34-d5a6-4c26-a6a4-5c789569f021",
            "c3f31179-5aa0-43c6-b415-e4dec8cddf0e",
            "c525bb81-f8f5-44a3-a8dc-6bacf4b66edc",
            "c556ffd8-8918-4bc2-8ccb-12cfcc9cc7a0",
            "c995524f-c466-4de3-a769-ca1b2d664f10",
            "cdaff7aa-99c6-40cc-aba5-9cda5809ac9a",
            "d1d31cff-3fa1-4e89-b120-26a76174f2d1",
            "d327b009-16e2-4ffb-b3a1-eca4df0b4755",
            "d71e9d2b-67c8-415c-a222-48c9f38a63e6",
            "de3ff0bd-e4af-4b1a-8eca-d0f81f936a72",
            "e0ef8518-1c71-4762-acde-947d9b5866bf",
            "e1c9e79f-cb79-4631-9aee-2c7640639121",
            "e37dc277-1a8d-4c36-a141-79e7d1113a0b",
            "e4dd32ab-27de-44af-bcdc-5f21b3ceeeb2",
            "e4e7502d-d76b-48bf-b094-b3c3d9b03fd7",
            "eb30bfb1-c48c-438b-9d37-c5bd8c542d81",
            "ecd4db4b-bea8-428b-ae01-26ecbc63901f",
            "ee77751c-65f0-4466-9844-b8fb29cf0bfb",
            "f237813a-cb03-487d-97d9-7a24f7d9815c",
            "f787d9e0-37f0-4c6e-b02b-5883660f49a8",
            "f7ee25a0-53f5-47ea-b3ee-959895707b29",
            "ffaa9b35-bfbb-4409-98d2-39716bccebe5",
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
        # item["notes"].append(
        #     {
        #         "itemNoteTypeId": shelving_order_item_note_type_id,
        #         "note": local_shelving_order,
        #         "staffOnly": True,
        #     }
        # )
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
