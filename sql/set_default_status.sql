-- Set default status to 'not_started' for new rows in prefix_metadata
-- Run this in Supabase SQL Editor

-- Set default value for status column
ALTER TABLE prefix_metadata 
ALTER COLUMN status SET DEFAULT 'not_started';

-- Verify the default is set
SELECT column_name, column_default, data_type 
FROM information_schema.columns 
WHERE table_name = 'prefix_metadata' 
AND column_name = 'status';

-- Should show: column_default = 'not_started'::character varying

