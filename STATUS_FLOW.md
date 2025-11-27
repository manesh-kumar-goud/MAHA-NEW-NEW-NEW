# Status Flow Logic

## 📋 Status Flow Rules

### 1. **New Row Entry** → `NOT_STARTED`
- When a new prefix is added to Supabase
- Status is automatically set to `NOT_STARTED`
- Code: `app/services/id_generator.py` - creates with `NOT_STARTED` status

### 2. **Processing Priority** → `PENDING` first, then `NOT_STARTED`
- **PRIORITY 1**: Process all `PENDING` prefixes first
- **PRIORITY 2**: Only when ALL `PENDING` are completed, start `NOT_STARTED`
- When starting a `NOT_STARTED` → automatically changes to `PENDING`
- Code: `app/services/automation_new.py` - `_get_next_prefix_to_process()`

### 3. **Completion** → `COMPLETED`
- When a prefix reaches its maximum (e.g., 5 digits = 0-99999)
- Status automatically changes to `COMPLETED`
- Code: `app/services/automation_new.py` - `_process_prefix_until_completion()`

## 🔄 Complete Flow

```
New Row Added
    ↓
NOT_STARTED
    ↓
[Wait until all PENDING are completed]
    ↓
Status changed to PENDING (when processing starts)
    ↓
Processing... (generating IDs, scraping)
    ↓
COMPLETED (when max reached)
```

## 📊 Example Scenario

1. **Add prefix "2626"** → Status: `NOT_STARTED`
2. **Add prefix "2442"** → Status: `NOT_STARTED`
3. **Automation starts** → Checks for PENDING (none found)
4. **Starts "2626"** → Status: `NOT_STARTED` → `PENDING`
5. **Processing "2626"** → Generating IDs...
6. **"2626" completes** → Status: `PENDING` → `COMPLETED`
7. **All PENDING done** → Starts "2442"
8. **"2442" starts** → Status: `NOT_STARTED` → `PENDING`
9. **"2442" completes** → Status: `PENDING` → `COMPLETED`

## ✅ Code Implementation

### New Prefix Creation
```python
# app/services/id_generator.py
new_config = {
    "prefix": prefix,
    "status": PrefixStatus.NOT_STARTED.value  # ✅ New rows = NOT_STARTED
}
```

### Starting NOT_STARTED (only when all PENDING done)
```python
# app/services/automation_new.py
# Check if NO PENDING exist
if len(all_pending.data) == 0:
    # Start NOT_STARTED and change to PENDING
    status: NOT_STARTED → PENDING
```

### Completion
```python
# app/services/automation_new.py
if final_config.last_number >= max_number:
    await self._mark_prefix_status(prefix, PrefixStatus.COMPLETED)
```

## 🎯 Key Points

- ✅ New rows always start as `NOT_STARTED`
- ✅ `NOT_STARTED` only starts when ALL `PENDING` are completed
- ✅ When `NOT_STARTED` starts → automatically becomes `PENDING`
- ✅ When processing completes → automatically becomes `COMPLETED`
- ✅ Status changes are automatic - no manual intervention needed

