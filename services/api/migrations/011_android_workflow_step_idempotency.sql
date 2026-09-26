-- Prevent concurrent resume/result handlers from creating duplicate active workflow steps.
CREATE UNIQUE INDEX IF NOT EXISTS ux_device_commands_active_workflow_step
ON device_commands (
    owner_id,
    (arguments_json->'_workflow'->>'id'),
    (arguments_json->'_workflow'->>'next_index')
)
WHERE status='ACCEPTED'
  AND arguments_json ? '_workflow'
  AND arguments_json->'_workflow'->>'id' IS NOT NULL
  AND arguments_json->'_workflow'->>'next_index' IS NOT NULL;
