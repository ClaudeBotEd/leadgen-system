DROP INDEX IF EXISTS decisions_signal_text_fts;
CREATE INDEX decisions_signal_text_fts
  ON decisions USING gin (to_tsvector('simple',
    coalesce(inputs_payload->'signal'->>'postText', '') || ' ' ||
    coalesce(inputs_payload->'lead'->>'postText', '') || ' ' ||
    coalesce(inputs_payload->'lead'->>'niche', '')
  ));
