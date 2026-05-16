DROP TRIGGER IF EXISTS trg_user_touch ON user_account;
DROP TRIGGER IF EXISTS trg_workspace_touch ON workspace;
DROP TRIGGER IF EXISTS trg_memory_touch ON memory_item;
DROP TRIGGER IF EXISTS trg_wiki_touch ON wiki_page;
DROP TRIGGER IF EXISTS trg_memory_before_update ON memory_item;
DROP TRIGGER IF EXISTS trg_memory_after_insert ON memory_item;
DROP TRIGGER IF EXISTS trg_memory_after_update ON memory_item;
DROP TRIGGER IF EXISTS trg_memory_soft_delete ON memory_item;
DROP TRIGGER IF EXISTS trg_wiki_revision_after_insert ON wiki_page_revision;

DROP FUNCTION IF EXISTS fn_memory_revision_fields_changed();

CREATE OR REPLACE FUNCTION fn_current_actor_type()
RETURNS VARCHAR(20) AS $$
BEGIN
  RETURN coalesce(nullif(current_setting('app.actor_type', true), ''), 'system');
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_current_actor_id()
RETURNS UUID AS $$
BEGIN
  RETURN nullif(current_setting('app.actor_id', true), '')::uuid;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_revision_reason(default_reason TEXT)
RETURNS TEXT AS $$
BEGIN
  RETURN coalesce(nullif(current_setting('app.revision_reason', true), ''), default_reason);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = clock_timestamp();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_user_touch
BEFORE UPDATE ON user_account
FOR EACH ROW EXECUTE FUNCTION fn_touch_updated_at();

CREATE TRIGGER trg_workspace_touch
BEFORE UPDATE ON workspace
FOR EACH ROW EXECUTE FUNCTION fn_touch_updated_at();

CREATE TRIGGER trg_memory_touch
BEFORE UPDATE ON memory_item
FOR EACH ROW EXECUTE FUNCTION fn_touch_updated_at();

CREATE TRIGGER trg_wiki_touch
BEFORE UPDATE ON wiki_page
FOR EACH ROW EXECUTE FUNCTION fn_touch_updated_at();

CREATE OR REPLACE FUNCTION fn_memory_revision_fields_changed(
  old_memory memory_item,
  new_memory memory_item
)
RETURNS BOOLEAN AS $$
BEGIN
  RETURN new_memory.canonical_text IS DISTINCT FROM old_memory.canonical_text
    OR new_memory.summary IS DISTINCT FROM old_memory.summary
    OR new_memory.status IS DISTINCT FROM old_memory.status
    OR new_memory.confidence IS DISTINCT FROM old_memory.confidence
    OR new_memory.importance IS DISTINCT FROM old_memory.importance
    OR new_memory.access_level IS DISTINCT FROM old_memory.access_level
    OR new_memory.valid_from IS DISTINCT FROM old_memory.valid_from
    OR new_memory.valid_to IS DISTINCT FROM old_memory.valid_to
    OR new_memory.superseded_by_memory_id IS DISTINCT FROM old_memory.superseded_by_memory_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_mark_wiki_rebuild_for_memory(target_memory_id UUID)
RETURNS VOID AS $$
BEGIN
  UPDATE wiki_page
  SET needs_rebuild = TRUE
  WHERE generated_from_memory_id = target_memory_id
    AND needs_rebuild IS DISTINCT FROM TRUE;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION fn_memory_before_update()
RETURNS TRIGGER AS $$
BEGIN
  IF fn_memory_revision_fields_changed(OLD, NEW) THEN
    NEW.current_revision_no = OLD.current_revision_no + 1;
  ELSE
    NEW.current_revision_no = OLD.current_revision_no;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_memory_before_update
BEFORE UPDATE ON memory_item
FOR EACH ROW EXECUTE FUNCTION fn_memory_before_update();

CREATE OR REPLACE FUNCTION fn_memory_after_insert()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO memory_revision(
    memory_id, revision_no, revision_text, revision_summary,
    revision_reason, editor_type, editor_id
  )
  VALUES (
    NEW.memory_id,
    1,
    NEW.canonical_text,
    NEW.summary,
    fn_revision_reason('initial create'),
    fn_current_actor_type(),
    fn_current_actor_id()
  );

  INSERT INTO audit_log(
    workspace_id, actor_type, actor_id,
    action_type, target_type, target_id, after_json
  )
  VALUES (
    NEW.workspace_id,
    fn_current_actor_type(),
    fn_current_actor_id(),
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

CREATE OR REPLACE FUNCTION fn_memory_after_update()
RETURNS TRIGGER AS $$
DECLARE
  action_type TEXT := 'memory.update';
BEGIN
  IF NEW.current_revision_no <> OLD.current_revision_no THEN
    INSERT INTO memory_revision(
      memory_id, revision_no, revision_text, revision_summary,
      revision_reason, editor_type, editor_id
    )
    VALUES (
      NEW.memory_id,
      NEW.current_revision_no,
      NEW.canonical_text,
      NEW.summary,
      fn_revision_reason('memory updated'),
      fn_current_actor_type(),
      fn_current_actor_id()
    );

    PERFORM fn_mark_wiki_rebuild_for_memory(NEW.memory_id);
  END IF;

  IF NEW.status = 'archived' AND OLD.status IS DISTINCT FROM 'archived' THEN
    action_type := 'memory.soft_delete';
  ELSIF NEW.status = 'forgotten' AND OLD.status IS DISTINCT FROM 'forgotten' THEN
    action_type := 'memory.forget';
  END IF;

  INSERT INTO audit_log(
    workspace_id, actor_type, actor_id,
    action_type, target_type, target_id, before_json, after_json
  )
  VALUES (
    NEW.workspace_id,
    fn_current_actor_type(),
    fn_current_actor_id(),
    action_type,
    'memory_item',
    NEW.memory_id,
    to_jsonb(OLD),
    to_jsonb(NEW)
  );

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_memory_after_update
AFTER UPDATE ON memory_item
FOR EACH ROW EXECUTE FUNCTION fn_memory_after_update();

CREATE OR REPLACE FUNCTION fn_memory_soft_delete()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE memory_item
  SET status = 'archived',
      valid_to = coalesce(valid_to, now())
  WHERE memory_id = OLD.memory_id
    AND status <> 'archived';

  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_memory_soft_delete
BEFORE DELETE ON memory_item
FOR EACH ROW EXECUTE FUNCTION fn_memory_soft_delete();

CREATE OR REPLACE FUNCTION fn_wiki_revision_after_insert()
RETURNS TRIGGER AS $$
BEGIN
  UPDATE wiki_page
  SET current_revision_no = NEW.revision_no,
      needs_rebuild = FALSE
  WHERE page_id = NEW.page_id;

  INSERT INTO audit_log(
    workspace_id, actor_type, actor_id,
    action_type, target_type, target_id, after_json
  )
  SELECT
    wp.workspace_id,
    fn_current_actor_type(),
    fn_current_actor_id(),
    'wiki.revision.insert',
    'wiki_page',
    NEW.page_id,
    to_jsonb(NEW)
  FROM wiki_page wp
  WHERE wp.page_id = NEW.page_id;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_wiki_revision_after_insert
AFTER INSERT ON wiki_page_revision
FOR EACH ROW EXECUTE FUNCTION fn_wiki_revision_after_insert();
