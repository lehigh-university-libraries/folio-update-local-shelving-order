-- metadb:function count_items_needing_local_shelving_order
-- Count the items that would be returned from get_items_needing_local_shelving_order.

DROP FUNCTION IF EXISTS count_items_needing_local_shelving_order;

CREATE FUNCTION count_items_needing_local_shelving_order(
)
RETURNS TABLE (
	total BIGINT
)
AS
$$
SELECT
	COUNT(*)
FROM
    folio_inventory.item__t item__t
JOIN folio_inventory.holdings_record__t holdings_record__t 
    ON holdings_record__t.id = item__t.holdings_record_id
JOIN folio_inventory.call_number_type__t call_number_type__t
	ON call_number_type__t.id = holdings_record__t.call_number_type_id
WHERE
	call_number_type__t.name = 'Dewey Decimal classification'
    AND (
        -- long cutter numbers
        item__t.item_level_call_number ~ '[0-9]{3}(.[0-9]+)? [A-Z]{1,2}[0-9]{4,}.*'
        OR
        holdings_record__t.call_number ~ '[0-9]{3}(.[0-9]+)? [A-Z]{1,2}[0-9]{4,}.*'
        OR
        -- capital letters after the cutter numbers
        item__t.item_level_call_number ~ '[0-9]{3}(.[0-9]+)? [A-Z]{1,2}[0-9]+[A-Z]+.*'
        OR
        holdings_record__t.call_number ~ '[0-9]{3}(.[0-9]+)? [A-Z]{1,2}[0-9]+[A-Z]+.*'
        OR
        -- colon after the cutter numbers
        item__t.item_level_call_number ~ '[0-9]{3}(.[0-9]+)? [A-Z]{1,2}[0-9]+:+.*'
        OR
        holdings_record__t.call_number ~ '[0-9]{3}(.[0-9]+)? [A-Z]{1,2}[0-9]+:+.*'
        OR
        -- more numbers after the second set of cutter letters
        item__t.item_level_call_number ~ '[0-9]{3}(.[0-9]+)? [A-Z]{1,2}[0-9]+[A-Za-z]+[0-9]+.*'
        OR
        holdings_record__t.call_number ~ '[0-9]{3}(.[0-9]+)? [A-Z]{1,2}[0-9]+[A-Za-z]+[0-9]+.*'
    ) 
    -- AND NOT EXISTS (
    --     SELECT
    --         1
    --     FROM
    --         folio_derived.item_notes item_notes
    --     WHERE
    --         item_notes.item_id = item__t.id
    --         AND item_notes.note_type_name = 'Shelving order'
    -- )
$$
LANGUAGE SQL;
