# KTMA FM Mapping and Reconciliation Learnings

- **FM Coefficient & Entity Separation**: Maintaining strict separation between Eplaza and Impulsa columns prevents amount mixing in multi-entity consolidation.
- **Semantic Key Uniqueness**: Preserving period, account code, and entity context avoids collision in consolidated mapping rules.
- **Query Sheet Hygiene**: Distinguishing actual zero-balance accounts from single-entity presence ensures accurate query results without artificial row clutter.
