-- metadb:function get_items_needing_local_shelving_order
-- Get a list of items that do not have a 'Shelving order' note, but need it because the call number (either item or holdings level) has a cutter with more than three digits.

DROP FUNCTION IF EXISTS get_items_needing_local_shelving_order;

CREATE FUNCTION get_items_needing_local_shelving_order(
    query_offset BIGINT,
    query_limit BIGINT
)
RETURNS TABLE (
	id TEXT,
    hrid TEXT,
    barcode TEXT,
    item_call_number TEXT,
    hr_call_number TEXT
)
AS
$$
SELECT
	item__t.id,
    item__t.hrid,
    item__t.barcode,
    item__t.item_level_call_number,
    holdings_record__t.call_number AS hr_call_number
FROM
    folio_inventory.item__t item__t
JOIN folio_inventory.holdings_record__t holdings_record__t 
    ON holdings_record__t.id = item__t.holdings_record_id
JOIN folio_inventory.call_number_type__t call_number_type__t
	ON call_number_type__t.id = holdings_record__t.call_number_type_id
WHERE
	call_number_type__t.name = 'Dewey Decimal classification'
    AND (
        item__t.item_level_call_number ~ '[0-9]{3}(.[0-9]+)? [A-Z]{1,2}[0-9]{4,}.*'
        OR
        holdings_record__t.call_number ~ '[0-9]{3}(.[0-9]+)? [A-Z]{1,2}[0-9]{4,}.*'
    ) 
    AND NOT EXISTS (
        SELECT
            1
        FROM
            folio_derived.item_notes item_notes
        WHERE
            item_notes.item_id = item__t.id
            AND item_notes.note_type_name = 'Shelving order'
    )
OFFSET
    query_offset
LIMIT
    query_limit
$$
LANGUAGE SQL;
