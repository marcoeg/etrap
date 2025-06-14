-- Test transaction with known values
-- Record the exact time and values for verification

BEGIN;

-- Insert with explicit values
INSERT INTO financial_transactions (account_id, amount, type, reference) 
VALUES ('ACC999', 999.99, 'C', 'TEST-VERIFY');

-- Get the inserted record with exact database values
SELECT 
    id,
    account_id,
    amount,
    type,
    created_at,
    reference
FROM financial_transactions 
WHERE account_id = 'ACC999' 
ORDER BY id DESC 
LIMIT 1;

COMMIT;