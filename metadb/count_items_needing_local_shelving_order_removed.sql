-- metadb:function count_items_needing_local_shelving_order_removed
-- Count the items that have an old 'Shelving order' note to delete

DROP FUNCTION IF EXISTS count_items_needing_local_shelving_order_removed;

CREATE FUNCTION count_items_needing_local_shelving_order_removed(
)
RETURNS TABLE (
	total BIGINT
)
AS
$$
SELECT
	COUNT(*)
FROM
    folio_derived.item_notes item_notes
JOIN 
    folio_inventory.item__t item__t 
    ON item_notes.item_id = item__t.id
WHERE
    item_notes.note_type_name = 'Shelving order'
    AND 
    item_notes.note ~ '[0-9]{3}(.[0-9]+)? [A-Z]{1,2}[0-9]+[a-z]+.*'
$$
LANGUAGE SQL;
