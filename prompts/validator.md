Audit the supplied structured verification record. Return accepted=true and issues=[]
when ALL conditions hold: expected_count equals selected_count, unique_count equals
selected_count, every selected_id occurs in allowed_ids, deterministic_checks_passed=true,
and failed_checks is empty. Otherwise return accepted=false with short issues.
Do not add genre, plot, cast, title or user-query requirements: those are outside this record.
An acceptance MUST have an empty issues array. Output only JSON.
