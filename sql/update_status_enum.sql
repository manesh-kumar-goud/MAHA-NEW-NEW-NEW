-- Update prefix_metadata table to use new 3-status system
-- NOT_STARTED, PENDING, COMPLETED

-- First, convert existing statuses to new system
UPDATE public.prefix_metadata
SET status = 'pending'
WHERE status IN ('running', 'error', 'paused');

-- Update the check constraint to only allow the 3 new statuses
ALTER TABLE public.prefix_metadata
DROP CONSTRAINT IF EXISTS prefix_metadata_status_check;

ALTER TABLE public.prefix_metadata
ADD CONSTRAINT prefix_metadata_status_check
CHECK (status IN ('not_started', 'pending', 'completed'));

-- Verify the update
SELECT status, COUNT(*) as count
FROM public.prefix_metadata
GROUP BY status
ORDER BY status;
