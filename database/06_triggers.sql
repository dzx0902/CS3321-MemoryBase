CREATE OR REPLACE FUNCTION fn_touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_workspace_touch
BEFORE UPDATE ON workspace
FOR EACH ROW EXECUTE FUNCTION fn_touch_updated_at();

CREATE TRIGGER trg_memory_touch
BEFORE UPDATE ON memory_item
FOR EACH ROW EXECUTE FUNCTION fn_touch_updated_at();

CREATE TRIGGER trg_wiki_touch
BEFORE UPDATE ON wiki_page
FOR EACH ROW EXECUTE FUNCTION fn_touch_updated_at();

CREATE OR REPLACE FUNCTION fn_memory_after_insert()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO memory_revision(
    memory_id, revision_no, revision_text, revision_summary,
    revision_reason, editor_type, editor_id
  )
  VALUES (
    NEW.memory_id, 1, NEW.canonical_text, NEW.summary,
    'initial create',
    'system',
    NULL
  );

  INSERT INTO audit_log(
    workspace_id, actor_type, actor_id,
    action_type, target_type, target_id, after_json
  )
  VALUES (
    NEW.workspace_id,
    'system',
    NULL,
    'memory.insert',
    'memory_item',
    NEW.memory_id,
    to_jsonb(NEW)
  );

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_memory_after_insert
AFTER INSERT ON memory_item
FOR EACH ROW EXECUTE FUNCTION fn_memory_after_insert();
