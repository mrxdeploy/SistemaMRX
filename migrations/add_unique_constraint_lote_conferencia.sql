-- Migration: Add unique constraint to lote.conferencia_id
-- Date: 2025-11-15
-- Purpose: Prevent duplicate lot creation for the same conference

-- Step 1: Check for existing duplicates (run this first to identify issues)
SELECT conferencia_id, COUNT(*) as count
FROM lotes
WHERE conferencia_id IS NOT NULL
GROUP BY conferencia_id
HAVING COUNT(*) > 1;

-- Step 2: If duplicates exist, resolve them manually before proceeding
-- Example: Keep the first created lot and delete others
-- DELETE FROM lotes WHERE id IN (
--     SELECT id FROM (
--         SELECT id, ROW_NUMBER() OVER (PARTITION BY conferencia_id ORDER BY data_criacao ASC) as rn
--         FROM lotes
--         WHERE conferencia_id IS NOT NULL
--     ) t
--     WHERE t.rn > 1
-- );

-- Step 3: Add unique constraint (only run after resolving duplicates)
ALTER TABLE lotes
ADD CONSTRAINT uq_lote_conferencia_id UNIQUE (conferencia_id);

-- Step 4: Verify constraint was added
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'lotes'::regclass
AND conname = 'uq_lote_conferencia_id';
