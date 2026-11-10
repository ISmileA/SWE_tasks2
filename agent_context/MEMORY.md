# Memory lifecycle
Current query and graph state: request scope, no indefinite transcript growth.
Episodes: only successful recommendation IDs, method and trace reference; 7-day TTL.
Preferences: explicit user input only, source and update time required; 90-day TTL.
Current explicit genre outranks stored genre. Corrections overwrite a key transactionally.
Expired data is purged on read. DELETE /memory/{user_id} clears both persistent layers.
No automatic inference of sensitive attributes. No write tool is exposed to the LLM.
