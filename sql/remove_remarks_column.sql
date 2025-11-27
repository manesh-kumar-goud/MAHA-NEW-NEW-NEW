-- Remove remarks and timestamp columns from Supabase tables
-- Run this in Supabase SQL Editor

-- Remove remarks from prefix_metadata
ALTER TABLE prefix_metadata 
DROP COLUMN IF EXISTS remarks;

-- Remove timestamps from prefix_metadata
ALTER TABLE prefix_metadata 
DROP COLUMN IF EXISTS created_at;

ALTER TABLE prefix_metadata 
DROP COLUMN IF EXISTS updated_at;

-- Remove timestamps from serial_log (if exists)
ALTER TABLE serial_log 
DROP COLUMN IF EXISTS created_at;

-- Verify columns are removed
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name IN ('prefix_metadata', 'serial_log')
AND column_name IN ('remarks', 'created_at', 'updated_at');

-- Should return 0 rows if successful

