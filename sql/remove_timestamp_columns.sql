-- Remove timestamp columns from Supabase tables
-- Run this in Supabase SQL Editor

-- Remove from prefix_metadata table
ALTER TABLE prefix_metadata 
DROP COLUMN IF EXISTS created_at;

ALTER TABLE prefix_metadata 
DROP COLUMN IF EXISTS updated_at;

-- Remove from serial_log table (if exists)
ALTER TABLE serial_log 
DROP COLUMN IF EXISTS created_at;

-- Verify columns are removed
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name IN ('prefix_metadata', 'serial_log')
AND column_name IN ('created_at', 'updated_at');

-- Should return 0 rows if successful

