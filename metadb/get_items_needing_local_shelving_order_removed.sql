-- metadb:function get_items_needing_local_shelving_order_removed
-- Get a list of items that have an old 'Shelving order' note to delete

DROP FUNCTION IF EXISTS get_items_needing_local_shelving_order_removed;

CREATE FUNCTION get_items_needing_local_shelving_order_removed(
    query_offset BIGINT,
    query_limit BIGINT
)
RETURNS TABLE (
	item_id TEXT,
    note TEXT
)
AS
$$
SELECT
    item__t.id,
    item_notes.note
FROM
    folio_derived.item_notes item_notes
JOIN 
    folio_inventory.item__t item__t 
    ON item_notes.item_id = item__t.id
WHERE
    item_notes.note_type_name = 'Shelving order'
    AND 
    item_notes.note ~ '[0-9]{3}(.[0-9]+)? [A-Z]{1,2}[0-9]+[a-z]+.*'
ORDER BY 
    item__t.barcode
OFFSET
    query_offset
LIMIT
    query_limit
$$
LANGUAGE SQL;
