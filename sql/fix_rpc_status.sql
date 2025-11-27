-- Fix RPC function to use 'pending' instead of 'running'
-- Drop and recreate the function with correct status

DROP FUNCTION IF EXISTS public.next_prefix_number(text, integer, boolean);

CREATE OR REPLACE FUNCTION public.next_prefix_number(
    p_prefix text,
    p_digits integer DEFAULT 5,
    p_has_space boolean DEFAULT true
)
RETURNS TABLE (
    prefix text,
    digits integer,
    last_number integer,
    has_space boolean,
    status text,
    remarks text,
    created_at timestamptz,
    updated_at timestamptz
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_new_number integer;
    v_current_record record;
BEGIN
    -- Get current record
    SELECT * INTO v_current_record
    FROM public.prefix_metadata pm
    WHERE pm.prefix = p_prefix
    FOR UPDATE;
    
    -- If not exists, create it
    IF NOT FOUND THEN
        INSERT INTO public.prefix_metadata (
            prefix, digits, last_number, has_space, status, created_at, updated_at
        ) VALUES (
            p_prefix, p_digits, 0, p_has_space, 'pending', NOW(), NOW()
        )
        RETURNING * INTO v_current_record;
    END IF;
    
    -- Increment number
    v_new_number := v_current_record.last_number + 1;
    
    -- Update with new number and keep status as 'pending' (not 'running')
    UPDATE public.prefix_metadata
    SET 
        last_number = v_new_number,
        digits = COALESCE(p_digits, v_current_record.digits),
        has_space = COALESCE(p_has_space, v_current_record.has_space),
        status = 'pending',  -- Always use 'pending', never 'running'
        updated_at = NOW()
    WHERE public.prefix_metadata.prefix = p_prefix;
    
    -- Return updated record
    RETURN QUERY
    SELECT 
        pm.prefix,
        COALESCE(p_digits, v_current_record.digits),
        v_new_number,
        COALESCE(p_has_space, v_current_record.has_space),
        'pending'::text,  -- Always return 'pending'
        pm.remarks,
        pm.created_at,
        NOW()
    FROM public.prefix_metadata pm
    WHERE pm.prefix = p_prefix;
END;
$$;

