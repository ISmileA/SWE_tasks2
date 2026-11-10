---
name: verify-recommendations
description: Independently audit count, identity and genre against tool evidence.
---
Read selected_ids and allowed_ids. Count equality and uniqueness are explicit numbers.
Reject only if a selected ID is absent, the counts differ, failed_checks is nonempty,
or deterministic_checks_passed is false. Do not invent missing query/genre fields.
When the record passes, output accepted=true, issues=[]. The application independently
enforces deterministic checks; you cannot override a failed check.
