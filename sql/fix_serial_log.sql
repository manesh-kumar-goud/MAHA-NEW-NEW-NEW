-- Fix serial_log table status constraint
-- The constraint is too restrictive, need to update it

-- Drop the existing constraint
ALTER TABLE public.serial_log DROP CONSTRAINT IF EXISTS serial_log_status_check;

-- Add new constraint with correct status values
ALTER TABLE public.serial_log ADD CONSTRAINT serial_log_status_check 
CHECK (status IN ('pending', 'running', 'completed', 'error'));

-- Update any existing invalid status values
UPDATE public.serial_log 
SET status = 'completed' 
WHERE status = 'partial';

-- Verify the fix
SELECT DISTINCT status FROM public.serial_log;
