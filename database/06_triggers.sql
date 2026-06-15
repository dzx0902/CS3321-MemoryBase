DROP TRIGGER IF EXISTS trg_user_touch ON user_account;
DROP TRIGGER IF EXISTS trg_workspace_touch ON workspace;
DROP TRIGGER IF EXISTS trg_memory_touch ON memory_item;
DROP TRIGGER IF EXISTS trg_entity_touch ON entity;
DROP TRIGGER IF EXISTS trg_memory_scene_touch ON memory_scene;
DROP TRIGGER IF EXISTS trg_wiki_touch ON wiki_page;
DROP TRIGGER IF EXISTS trg_memory_before_update ON memory_item;
DROP TRIGGER IF EXISTS trg_memory_after_insert ON memory_item;
DROP TRIGGER IF EXISTS trg_memory_after_update ON memory_item;
DROP TRIGGER IF EXISTS trg_memory_soft_delete ON memory_item;
DROP TRIGGER IF EXISTS trg_wiki_revision_after_insert ON wiki_page_revision;
DROP TRIGGER IF EXISTS trg_conflict_touch ON conflict_record;
DROP TRIGGER IF EXISTS trg_conflict_after_insert ON conflict_record;
DROP TRIGGER IF EXISTS trg_conflict_after_update ON conflict_record;

DROP FUNCTION IF EXISTS fn_memory_revision_fields_changed();

-- Actor context helpers read transaction-local settings set by services or SQL fixtures.
-- They let triggers attribute revisions and audit rows without extra trigger arguments.
CREATE OR REPLACE FUNCTION fn_current_actor_type()
RETURNS VARCHAR(20) AS $$
BEGIN
  RETURN coalesce(nullif(current_setting('app.actor_type', true), ''), 'system');
END;
$$ LANGUAGE plpgsql;

-- Returns NULL when no actor id is supplied, which is valid for system actions.
CREATE OR REPLACE FUNCTION fn_current_actor_id()
RETURNS UUID AS $$
BEGIN
  RETURN nullif(current_setting('app.actor_id', true), '')::uuid;
END;
$$ LANGUAGE plpgsql;

-- Allows service code to override the revision reason for a transaction.
CREATE OR REPLACE FUNCTION fn_revision_reason(default_reason TEXT)
RETURNS TEXT AS $$
BEGIN
  RETURN coalesce(nullif(current_setting('app.revision_reason', true), ''), default_reason);
END;
$$ LANGUAGE plpgsql;

-- Shared updated_at maintainer for tables with mutable rows.
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

CREATE TRIGGER trg_entity_touch
BEFORE UPDATE ON entity
FOR EACH ROW EXECUTE FUNCTION fn_touch_updated_at();

CREATE TRIGGER trg_memory_scene_touch
BEFORE UPDATE ON memory_scene
FOR EACH ROW EXECUTE FUNCTION fn_touch_updated_at();

CREATE TRIGGER trg_wiki_touch
BEFORE UPDATE ON wiki_page
FOR EACH ROW EXECUTE FUNCTION fn_touch_updated_at();

CREATE TRIGGER trg_conflict_touch
BEFORE UPDATE ON conflict_record
FOR EACH ROW EXECUTE FUNCTION fn_touch_updated_at();

-- Revision-worthy memory changes. Pure updated_at changes should not create
-- a new revision number.
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

-- Marks direct wiki projections as stale when their source memory changes.
CREATE OR REPLACE FUNCTION fn_mark_wiki_rebuild_for_memory(target_memory_id UUID)
RETURNS VOID AS $$
BEGIN
  UPDATE wiki_page
  SET needs_rebuild = TRUE
  WHERE generated_from_memory_id = target_memory_id
    AND needs_rebuild IS DISTINCT FROM TRUE;
END;
$$ LANGUAGE plpgsql;

-- Before update: decide the next current_revision_no atomically before the row
-- is written, so the after trigger can insert the matching revision row.
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

-- After insert: create the initial immutable revision and audit snapshot.
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

-- After update: append revision/audit rows and convert lifecycle status changes
-- into specific action_type values for governance reports.
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

-- Soft delete for direct memory deletes. Workspace cascade deletes are allowed
-- to hard-delete by checking whether the parent workspace still exists.
CREATE OR REPLACE FUNCTION fn_memory_soft_delete()
RETURNS TRIGGER AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM workspace
    WHERE workspace_id = OLD.workspace_id
  ) THEN
    RETURN OLD;
  END IF;

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

-- Helper used by conflict triggers to decide whether a memory can return to active.
CREATE OR REPLACE FUNCTION fn_memory_has_open_conflict(target_memory_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1
    FROM conflict_record
    WHERE status = 'open'
      AND (
        left_memory_id = target_memory_id
        OR right_memory_id = target_memory_id
      )
  );
END;
$$ LANGUAGE plpgsql;

-- When an open conflict is created, active endpoint memories become conflicted.
CREATE OR REPLACE FUNCTION fn_conflict_mark_memory_conflicted(target_memory_id UUID)
RETURNS VOID AS $$
BEGIN
  UPDATE memory_item
  SET status = 'conflicted'
  WHERE memory_id = target_memory_id
    AND status = 'active';
END;
$$ LANGUAGE plpgsql;

-- Restore a conflicted memory only after all open conflicts involving it are closed.
CREATE OR REPLACE FUNCTION fn_conflict_restore_memory_if_clear(target_memory_id UUID)
RETURNS VOID AS $$
BEGIN
  IF NOT fn_memory_has_open_conflict(target_memory_id) THEN
    UPDATE memory_item
    SET status = 'active'
    WHERE memory_id = target_memory_id
      AND status = 'conflicted';
  END IF;
END;
$$ LANGUAGE plpgsql;

-- New open conflicts immediately mark both endpoint memories as conflicted.
CREATE OR REPLACE FUNCTION fn_conflict_after_insert()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.status = 'open' THEN
    PERFORM fn_conflict_mark_memory_conflicted(NEW.left_memory_id);
    PERFORM fn_conflict_mark_memory_conflicted(NEW.right_memory_id);
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_conflict_after_insert
AFTER INSERT ON conflict_record
FOR EACH ROW EXECUTE FUNCTION fn_conflict_after_insert();

-- Conflict status transitions keep memory endpoint statuses synchronized.
CREATE OR REPLACE FUNCTION fn_conflict_after_update()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.status = 'open' THEN
    PERFORM fn_conflict_mark_memory_conflicted(NEW.left_memory_id);
    PERFORM fn_conflict_mark_memory_conflicted(NEW.right_memory_id);
  ELSIF OLD.status = 'open' AND NEW.status IN ('resolved', 'ignored') THEN
    PERFORM fn_conflict_restore_memory_if_clear(NEW.left_memory_id);
    PERFORM fn_conflict_restore_memory_if_clear(NEW.right_memory_id);
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_conflict_after_update
AFTER UPDATE OF status ON conflict_record
FOR EACH ROW EXECUTE FUNCTION fn_conflict_after_update();

-- A wiki revision insert advances the page pointer, clears needs_rebuild, and
-- writes an audit row for the generated version.
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
