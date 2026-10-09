# S51 native EAT connector

Adds a single-use physical equip_item→consume_held→correlated probe transaction. It requires a pre-existing current ISSUED Action in ActionSupervisor; exact applied receipts and the S46 post-food/inventory delta are necessary for OUTCOME. Errors, incomplete transport and unknown effects close as UNKNOWN, never retry automatically. This milestone **does not yet qualify actual survival-mode eating**; required World-test evidence remains in #394. No food acquisition or crafting.
